# agents/company_research_agent.py

import os
import json
import textwrap
from typing import Any, Dict, Optional

import requests

from agents.groq_client import GroqClient


class CompanyResearchAgent:
    """
    Researches a target company using web APIs (when available) + LLM.

    - If TAVILY_API_KEY is set, it will call Tavily's web search API.
    - Otherwise, it falls back to LLM-only reasoning based on the company name.

    Returned structure is a JSON-like dict, safe for the UI and NL orchestrator:
    {
      "summary": str,
      "culture": [str, ...],
      "keywords": [str, ...],
      "role_alignment": str,
      "raw_sources": str  # optional, concatenated snippets
    }
    """

    def __init__(self, llm: GroqClient):
        self.llm = llm
        self.tavily_key = os.getenv("TAVILY_API_KEY")

    # ------------- Internal helpers -------------

    def _search_tavily(self, query: str) -> str:
        """
        Call Tavily web search API if API key is configured.
        Returns a long text blob of concatenated snippets, or empty string on failure.
        """
        if not self.tavily_key:
            return ""

        try:
            resp = requests.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": self.tavily_key,
                    "query": query,
                    "max_results": 5,
                    "include_answer": False,
                },
                timeout=12,
            )
            resp.raise_for_status()
            data = resp.json()

            snippets = []
            for item in data.get("results", []):
                title = item.get("title", "")
                content = item.get("content", "")
                url = item.get("url", "")
                if not content:
                    continue
                snippet = f"{title}\n{content}\nSource: {url}"
                snippets.append(snippet)

            # Keep it within a safe character budget for the LLM
            return "\n\n".join(snippets)[:6000]

        except Exception as e:
            print(f"[CompanyResearchAgent] Tavily search failed: {e}")
            return ""

    def _build_llm_prompt(
        self,
        company: str,
        extra_context: str,
        web_snippets: str,
    ) -> str:
        """
        Build a structured prompt that asks the LLM to turn web + context
        into a clean JSON summary usable by the rest of the system.
        """
        if web_snippets:
            web_block = web_snippets
        else:
            web_block = (
                "[No live web snippets available. Use your general knowledge and "
                "reasonable assumptions based on the company name and context.]"
            )

        prompt = f"""
        You are an AI assistant that researches target companies to help a user
        tailor their resume and job applications.

        Company name: "{company}"

        User's goal / extra context (may be empty):
        {extra_context or "N/A"}

        Web research snippets (may be partial or noisy):
        {web_block}

        From this, produce a compact JSON object with the following keys:

        - "summary": One short paragraph (2–4 sentences) describing the company:
          what it does, domain/industry, typical products/services.
        - "culture": An array of 3–7 bullet strings describing culture, values,
          and working style. Infer from context when needed.
        - "keywords": An array of 10–20 strings with high-impact keywords
          (tech stack, tools, values, focus areas) useful for tailoring a resume.
        - "role_alignment": A short paragraph explaining how a software / data /
          AI / engineering profile might align with this company in general.

        If you are unsure about some details, keep them generic but realistic.
        DO NOT invent obviously false facts.

        IMPORTANT:
        - Return ONLY valid JSON (no markdown, no comments, no backticks).
        - Make sure it's a single top-level JSON object with exactly those 4 keys.
        """
        return textwrap.dedent(prompt).strip()

    # ------------- Public API -------------

    def run(self, company: str, extra_context: str = "") -> Dict[str, Any]:
        """
        Main entry point.

        1) Optionally calls a web search API for real data.
        2) Feeds snippets + context into the LLM.
        3) Tries to parse the result as JSON; if parsing fails, wraps raw text.
        """
        company = (company or "").strip()
        if not company:
            return {
                "summary": "",
                "culture": [],
                "keywords": [],
                "role_alignment": "",
                "raw_sources": "",
                "error": "No company name provided.",
            }

        # Step 1: Web research (if Tavily key is present)
        query = f"{company} company overview culture products hiring tech stack values"
        web_snippets = self._search_tavily(query)

        # Step 2: Ask LLM to structure the research
        prompt = self._build_llm_prompt(
            company=company,
            extra_context=extra_context,
            web_snippets=web_snippets,
        )
        raw_answer = self.llm.generate(prompt, max_tokens=900)

        # Step 3: Parse JSON safely
        result: Dict[str, Any]
        try:
            result = json.loads(raw_answer)
            if not isinstance(result, dict):
                raise ValueError("Top-level JSON is not an object.")
        except Exception as e:
            print(f"[CompanyResearchAgent] JSON parse failed: {e}")
            # Fallback: wrap raw text so frontend doesn't crash
            result = {
                "summary": "",
                "culture": [],
                "keywords": [],
                "role_alignment": "",
                "raw_text": raw_answer,
            }

        # Attach raw sources if we had any
        if web_snippets:
            result.setdefault("raw_sources", web_snippets)

        return result
