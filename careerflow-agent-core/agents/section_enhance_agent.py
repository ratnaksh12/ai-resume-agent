# agents/section_enhance_agent.py
import json
from typing import Dict, Any, List
from .groq_client import GroqClient

class SectionEnhanceAgent:
    def __init__(self, llm_client: GroqClient):
        self.llm = llm_client

    def run(self, bullets: List[str], role: str = "Software Engineer") -> Dict[str, Any]:
        """
        bullets: list of strings (existing bullet points)
        role: desired role to tailor bullets for
        returns: {"edits": [ {index, before, after, explanation} ... ]}
        """
        joined = "\n".join(f"- {b}" for b in bullets)
        prompt = f"""
SECTION_ENHANCE:
You are a professional resume writer. Improve the following bullet points to be action-driven,
quantified when possible, specific to the role: {role}.
Return JSON: {{ "edits": [ {{ "index": int, "before": str, "after": str, "explanation": str }} ] }}

Bullets:
{joined}

Rules:
- Keep each improved bullet <= 35 words.
- Use strong verbs and include metrics where possible.
- If not enough info to infer metric, propose a plausible conservative metric and mark it in explanation.
"""
        resp = self.llm.generate(prompt, max_tokens=800)
        try:
            parsed = json.loads(resp)
            return parsed
        except Exception:
            # fallback: wrap plain text
            return {"edits_text": resp}
