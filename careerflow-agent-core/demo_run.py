# demo_run.py
from agents.groq_client import GroqClient
from agents.router import Router
from agents.job_match_agent import JobMatchAgent
from agents.section_enhance_agent import SectionEnhanceAgent
from agents.company_research_agent import CompanyResearchAgent

def demo():
    llm = GroqClient()  # no key -> demo mode
    router = Router(llm)
    job_agent = JobMatchAgent(llm)
    section_agent = SectionEnhanceAgent(llm)
    company_agent = CompanyResearchAgent(llm)

    sample_resume = """
    John Doe
    - Worked on backend systems
    - Built CI/CD pipelines
    - Wrote unit tests and improved coverage
    """

    jd = """
    Senior Backend Engineer
    Requirements:
    - 5+ years building scalable backend systems
    - Experience with AWS/GCP and system design
    - Strong test-driven development and CI/CD practices
    """

    user_msg = "Please optimize my resume for this Senior Backend Engineer role at ExampleCorp"

    agents = router.route(user_msg)
    print("Router chose:", agents)

    comp = company_agent.run("ExampleCorp", extra_context=user_msg)
    print("Company research:", comp)

    jm = job_agent.run(sample_resume, jd)
    print("Job match:", jm)

    bullets = ["Worked on backend systems", "Built CI/CD pipelines", "Wrote unit tests"]
    se = section_agent.run(bullets, role="Senior Backend Engineer")
    print("Section enhancements:", se)

if __name__ == "__main__":
    demo()
