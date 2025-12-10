# agents/job_match_agent.py
import json
from typing import Dict, Any
from .groq_client import GroqClient

class JobMatchAgent:
    def __init__(self, llm_client: GroqClient):
        self.llm = llm_client

    def run(self, resume_text: str, job_description: str) -> Dict[str, Any]:
        prompt = f"""
JOB_MATCH:
You are an expert hiring screener. Compare the resume text and the job description.
Return a JSON object with fields:
- score: float (0-1) representing match
- gaps: array of short strings listing missing skills/experience
- suggestions: array of short actionable suggestions to improve match

Resume:
\"\"\"{resume_text}\"\"\"

Job Description:
\"\"\"{job_description}\"\"\"

Return only valid JSON.
"""
        resp = self.llm.generate(prompt, max_tokens=400)
        # try to parse
        try:
            parsed = json.loads(resp)
            return parsed
        except Exception:
            # best-effort fallback if the model returns non-json
            return {"score": 0.0, "gaps": [], "suggestions": [resp]}
