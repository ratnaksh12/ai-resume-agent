# agents/router.py
from typing import List
from .groq_client import GroqClient

DEFAULT_AGENTS = ["job_match", "section_enhance", "company_research"]

class Router:
    def __init__(self, llm_client: GroqClient):
        self.llm = llm_client

    def route(self, user_message: str) -> List[str]:
        """
        Route the incoming user_message to one or more agents.
        Returns list of agent labels.
        """
        prompt = f"""
CLASSIFY: Given the user's request, return a comma-separated list of agent labels (job_match, section_enhance, company_research, translation).
Only return labels and commas. No extra text.

Examples:
User: "Optimize my resume for this Data Scientist job at Google" -> job_match,company_research,section_enhance
User: "Rewrite my backend bullet points to show impact" -> section_enhance
User: "Research the company's culture and suggest keywords for my resume" -> company_research
User: "{user_message}"
"""
        resp = self.llm.generate(prompt)
        # clean response
        if not resp:
            return DEFAULT_AGENTS
        labels = [x.strip() for x in resp.strip().split(",") if x.strip()]
        if not labels:
            return DEFAULT_AGENTS
        return labels
