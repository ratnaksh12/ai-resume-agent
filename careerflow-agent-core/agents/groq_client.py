# agents/groq_client.py
import os
import json
import requests
from dotenv import load_dotenv
from typing import Optional, Any

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

# sensible defaults
DEFAULT_MODEL = "llama-3.1-8b-instant"
DEFAULT_TEMPERATURE = 0.0  # deterministic for JSON outputs

class GroqClient:
    def __init__(self, api_key: Optional[str] = None, model: str = DEFAULT_MODEL):
        self.api_key = api_key or GROQ_API_KEY
        self.model = model
        self.demo_mode = False
        if not self.api_key:
            print("\n⚠️  No GROQ_API_KEY found — running in DEMO mode.\n")
            self.demo_mode = True

    def _call_groq(self, messages: list, max_tokens: int = 512) -> dict:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": DEFAULT_TEMPERATURE,
            "max_tokens": max_tokens,
        }
        resp = requests.post(GROQ_API_URL, json=payload, headers=headers, timeout=60)
        resp.raise_for_status()
        return resp.json()

    def generate(self, prompt: str, max_tokens: int = 400, expect_json: bool = False, model: Optional[str] = None) -> Any:
        """
        Send a chat request. If expect_json=True, we instruct the model to return STRICT JSON and parse it.
        Returns a string (if expect_json=False) or a Python object parsed from JSON (if expect_json=True).
        """
        if self.demo_mode:
            return self._demo_response(prompt, expect_json=expect_json)

        model_to_use = model or self.model
        system_msg = (
            "You are a JSON responder. ALWAYS respond with valid JSON and nothing else.\n"
            "If asked to return an array or object, return strictly valid JSON with double quotes.\n"
            "If you cannot determine correct values, use empty arrays or empty strings, but still return valid JSON.\n"
            "Do not add any commentary, explanation, or markdown.\n"
        )
        user_msg = prompt

        messages = [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
        ]

        try:
            data = self._call_groq(messages, max_tokens=max_tokens)
            # typical response structure: data["choices"][0]["message"]["content"]
            content = data["choices"][0]["message"]["content"]
        except Exception as e:
            print("❌ Groq API error:", e)
            raise RuntimeError(f"Groq request failed: {e}")

        if not expect_json:
            return content

        # try to parse JSON (and attempt simple fixes if needed)
        try:
            parsed = json.loads(content)
            return parsed
        except json.JSONDecodeError:
            # Attempt to extract JSON substring (best-effort)
            start = content.find("{")
            end = content.rfind("}") + 1
            if start != -1 and end != -1 and end > start:
                candidate = content[start:end]
                try:
                    parsed = json.loads(candidate)
                    return parsed
                except Exception:
                    pass
            # As a last resort return the raw content but signal parse failure
            raise ValueError(f"Failed to parse JSON from model output: {content!r}")

    # ----------------
    # Demo fallback, same outputs as before but return parsed JSON when expect_json=True
    # ----------------
    def _demo_response(self, prompt: str, expect_json: bool = False):
        pl = prompt.lower()
        if "classify" in pl:
            resp = "job_match,section_enhance,company_research"
            return resp if not expect_json else [s.strip() for s in resp.split(",")]

        if "job_match" in pl:
            j = {"score": 0.72, "gaps": ["cloud architecture", "system design"], "suggestions": ["Add metrics", "Highlight AWS/GCP"]}
            return j if expect_json else json.dumps(j)

        if "section_enhance" in pl:
            j = {"edits": [{"index": 0, "before": "Worked on backend systems", "after": "Designed backend services handling 1M+ daily requests with 30% lower latency", "explanation": "Added metric + strong action verb"}]}
            return j if expect_json else json.dumps(j)

        if "company_research" in pl:
            j = {"company": "ExampleCorp", "about": "A cloud infra company.", "tone": "technical, metrics-driven", "keywords": ["scalability", "SRE", "distributed systems"]}
            return j if expect_json else json.dumps(j)

        return {} if expect_json else "[]"
