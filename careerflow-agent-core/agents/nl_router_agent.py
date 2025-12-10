# agents/nl_router_agent.py

import os
from typing import Optional

from pydantic import BaseModel, Field
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser


class NLRoute(BaseModel):
    """How to handle a natural-language request."""

    intent: str = Field(
        ...,
        description="Short description of the user's main goal.",
    )

    run_job_match: bool = Field(
        False, description="Run job-match analysis against a job description."
    )
    run_company_research: bool = Field(
        False, description="Research the mentioned company to tailor tone/keywords."
    )
    run_section_enhance: bool = Field(
        False, description="Suggest concrete bullet edits or section improvements."
    )

    translate: bool = Field(
        False, description="True if user wants translation of resume/response."
    )
    target_language: Optional[str] = Field(
        None,
        description="Detected target language like 'French (France)', 'German (Germany)', 'Urdu (Pakistan)'.",
    )


class NLRouterAgent:
    """
    Uses LangChain + Groq to interpret a user's free-form message and decide
    which internal agents should be run, including translation.
    """

    def __init__(self, model_name: str = "llama-3.1-8b-instant"):
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY is required for NLRouterAgent")

        self.llm = ChatGroq(
            api_key=api_key,
            model=model_name,
            temperature=0.0,  # deterministic routing
        )

        self.parser = PydanticOutputParser(pydantic_object=NLRoute)

        self.prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    (
                        "You are a STRICT routing engine for a resume AI system.\n\n"
                        "Your job:\n"
                        "1. Detect TRANSLATION in ANY language and ANY market.\n"
                        "2. Detect if optimization, job matching, or bullet improvement is required.\n\n"
                        "Tools available:\n"
                        "- job_match: compare resume to a job description.\n"
                        "- company_research: analyze company to extract tone & keywords.\n"
                        "- section_enhance: improve bullets or sections of the resume.\n"
                        "- translate: translate resume or response to a target language.\n\n"
                        "Examples:\n"
                        "1) 'Optimize my resume for Google' -> run_job_match=true, "
                        "run_company_research=true, run_section_enhance=true.\n"
                        "2) 'Translate this to Spanish for the Mexican market' -> "
                        "translate=true, target_language='Spanish (Mexico)'.\n"
                        "3) 'Translate my resume to French for the France market' -> "
                        "translate=true, target_language='French (France)'.\n"
                        "4) 'Translate my resume to Urdu for the Pakistan market' -> "
                        "translate=true, target_language='Urdu (Pakistan)'.\n\n"
                        "Return ONLY JSON matching the schema below.\n"
                        "{format_instructions}"
                    ),
                ),
                ("user", "{message}"),
            ]
        ).partial(format_instructions=self.parser.get_format_instructions())

        self.chain = self.prompt | self.llm | self.parser

    def route(self, message: str) -> NLRoute:
        """Return an NLRoute object describing what to do."""
        return self.chain.invoke({"message": message})
