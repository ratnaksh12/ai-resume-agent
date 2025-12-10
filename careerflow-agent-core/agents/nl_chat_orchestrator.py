# agents/nl_chat_orchestrator.py

from typing import Optional, Dict, Any, List

from agents.nl_router_agent import NLRouterAgent, NLRoute
from agents.job_match_agent import JobMatchAgent
from agents.section_enhance_agent import SectionEnhanceAgent
from agents.company_research_agent import CompanyResearchAgent
from agents.groq_client import GroqClient
from store.sqlite_store import Store


class NLChatOrchestrator:
    """
    High-level natural-language chat orchestrator.

    - Uses NLRouterAgent (LangChain) to decide which tools to call.
    - Calls existing job_match, section_enhance, company_research agents.
    - Produces a friendly, single-text reply for the frontend chat.
    """

    def __init__(self, llm: GroqClient, store: Store):
        self.llm = llm
        self.store = store

        # LangChain-based router
        self.router = NLRouterAgent()

        # Existing agents
        self.job_agent = JobMatchAgent(llm)
        self.section_agent = SectionEnhanceAgent(llm)
        self.company_agent = CompanyResearchAgent(llm)

    def _detect_manual_translation_route(self, message: str) -> Optional[NLRoute]:
        """
        Simple keyword-based override so that languages like Japanese/Korean
        always trigger translation, even if the LLM router gets confused.
        """
        msg = message.lower()
        if "translate" not in msg:
            return None

        lang_map = {
            "mexican spanish": "Mexican Spanish",
            "spanish": "Spanish",
            "french": "French",
            "german": "German",
            "hindi": "Hindi",
            "urdu": "Urdu",
            "japanese": "Japanese",
            "japan": "Japanese",
            "korean": "Korean",
            "korea": "Korean",
        }

        target = None
        for key, val in lang_map.items():
            if key in msg:
                target = val
                break

        if not target:
            return None

        return NLRoute(
            intent="translate",
            run_job_match=False,
            run_company_research=False,
            run_section_enhance=False,
            translate=True,
            target_language=target,
        )

    def handle_message(
        self,
        message: str,
        resume_version_id: Optional[int] = None,
        role: Optional[str] = None,
        company: Optional[str] = None,
        job_description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Main entry point used by /chat_nl endpoint.
        Returns:
            {
              "reply": str,
              "agents_called": [...],
              "structured": {...},
              "routing_decision": {...}
            }
        """
        # ---- Load resume text (if we got a version id) ----
        resume_text = ""
        if resume_version_id:
            v = self.store.get_version(resume_version_id)
            if v:
                resume_text = v.raw_text or ""

        # ---- Manual override for translation-heavy prompts ----
        manual_route = self._detect_manual_translation_route(message)
        if manual_route:
            route = manual_route
        else:
            route = self.router.route(message)

        agents_called: List[str] = []
        structured: Dict[str, Any] = {}

        # Decide if this is a "pure translation" ask:
        pure_translation = (
            route.translate
            and not route.run_job_match
            and not route.run_company_research
            and not route.run_section_enhance
        )

        # ---- Company research ----
        if route.run_company_research and company:
            comp = self.company_agent.run(company, extra_context=message)
            structured["company_research"] = comp
            agents_called.append("company_research")

        # ---- Job match ----
        if route.run_job_match and resume_text:
            jd_text = job_description or message
            jm = self.job_agent.run(resume_text, jd_text)
            structured["job_match"] = jm
            agents_called.append("job_match")

        # ---- Section enhancement ----
        if route.run_section_enhance and resume_text:
            bullets = resume_text.splitlines()[:5]
            se = self.section_agent.run(
                bullets,
                role=role or "Software Engineer",
            )
            structured["section_enhance"] = se
            agents_called.append("section_enhance")

        # ---- Build a natural-language summary reply (English) ----
        summary_prompt = self._build_summary_prompt(
            user_message=message,
            route_dict=route.dict(),
            structured=structured,
            role=role,
            company=company,
        )

        reply_text = self.llm.generate(summary_prompt, max_tokens=800)

        # ---- Translation step (post-processing) ----
        if route.translate and route.target_language:
            if pure_translation and resume_text:
                content_to_translate = resume_text
            else:
                content_to_translate = reply_text

            translation_prompt = (
                "You are a professional resume translator.\n"
                f"Target language: {route.target_language}.\n"
                "Translate the following text for that market, keeping the resume format.\n"
                "Preserve line breaks and bullet points.\n"
                "DO NOT return JSON, YAML, or any structured data.\n"
                "DO NOT add explanations, headings, or commentary.\n"
                "Return ONLY the translated resume text.\n\n"
                f"{content_to_translate}"
            )
            reply_text = self.llm.generate(translation_prompt, max_tokens=1800)
            agents_called.append(f"translation:{route.target_language}")

        return {
            "reply": reply_text,
            "agents_called": agents_called,
            "structured": structured,
            "routing_decision": route.dict(),
        }

    def _build_summary_prompt(
        self,
        user_message: str,
        route_dict: Dict[str, Any],
        structured: Dict[str, Any],
        role: Optional[str],
        company: Optional[str],
    ) -> str:
        """
        Compose a single prompt to let Groq generate a readable answer,
        using the structured outputs from the agents we ran.
        """

        lines = [
            "You are an AI resume assistant.",
            "User request:",
            user_message,
            "",
            f"Target role (if any): {role or 'N/A'}",
            f"Target company (if any): {company or 'N/A'}",
            "",
            "Routing decision (tools called):",
            str(route_dict),
            "",
            "Structured tool outputs (JSON-like):",
            str(structured),
            "",
            "Write a concise, helpful answer to the user.",
            "",
            # Job match guidance
            "If job_match data is present, clearly include:",
            "- A numeric match_score between 0 and 1.",
            "- A short explanation of what that score means.",
            "- A bullet list of skill or experience gaps.",
            "- A bullet list of concrete suggestions to improve the match.",
            "",
            # Section enhancement guidance
            "If section_enhance data is present, propose improved bullet points.",
            "Make them quantified and impact-focused where possible.",
            "",
            # Company research guidance
            "If company_research is present, weave in company tone and keywords.",
            "",
            "Respond as if this were a chat assistant talking to a human, NOT raw JSON.",
        ]
        return "\n".join(lines)
