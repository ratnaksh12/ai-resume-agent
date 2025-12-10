# **AI Resume Agent – Multi-Agent Career Optimization System**

🚀 **AI Resume Agent** is an intelligent multi-agent system that helps users:

* Analyze resume–job match
* Enhance resume bullet points
* Perform company research
* Interact using natural language
* Export optimized resumes as clean, structured PDFs

The system is designed using a **modular agent architecture**, powered by **Groq LLM**, **FastAPI**, and a **React + Tailwind frontend**.

This project demonstrates real-world usage of **LLMs in production-style applications** with orchestration, vector search, and resume version control.

---

## ✅ **Key Features**

* 📄 Resume Upload & Parsing
* 🧠 AI Job Match Scoring with Skill Gap Detection
* ✍️ Bullet Point Enhancement using LLMs
* 🏢 Company Research Agent
* 💬 Natural Language Chat with Agent Routing
* 📊 Resume Version Control
* 📥 Clean PDF Resume Export
* 🌍 Multi-language Resume Translation
* 🔐 Secure API Key Handling via `.env`

---

## 🧠 **Overall Agent Architecture**

This project follows a **multi-agent orchestration pattern**:

```
User → Frontend (React)
        ↓
   FastAPI Backend
        ↓
  NL Chat Orchestrator
        ↓
   Router Agent
        ↓
 ┌─────────────┬─────────────┬──────────────────┐
 | Job Match   | Bullet      | Company Research |
 | Agent       | Enhance     | Agent            |
 └─────────────┴─────────────┴──────────────────┘
        ↓
  Structured JSON Output
        ↓
  Resume Storage + Vector DB (Chroma)
```

---

## 🔁 **Agent Responsibilities**

### 1. **NL Chat Orchestrator**

* Interprets user intent
* Dispatches requests to appropriate agents
* Merges structured + natural output

### 2. **Router Agent**

* Decides whether to call:

  * Job Match Agent
  * Bullet Enhancement Agent
  * Company Research Agent

### 3. **Job Match Agent**

* Compares resume vs job description
* Outputs:

  * Match score
  * Missing skills
  * Optimization suggestions

### 4. **Section Enhance Agent**

* Improves resume bullet points
* Converts weak bullets into quantified, impact-driven statements

### 5. **Company Research Agent**

* Generates:

  * Company overview
  * Hiring tone
  * Resume keyword suggestions

---

## 🧩 **Context Engineering Strategy**

To ensure high-quality outputs:

* ✅ Resume text is injected as **primary context**
* ✅ Job descriptions are passed with **role-specific framing**
* ✅ Company research uses:

  * Company name
  * Recruiting intent cues
* ✅ Bullet enhancement is executed with:

  * Role-specific prompts
  * Skill weighting
  * Impact-oriented phrasing

This avoids hallucination and ensures **resume-safe outputs**.

---

## 🛠️ **Tech Stack**

### Backend

* **FastAPI** – API server
* **Groq LLM API** – Ultra-fast LLM inference
* **ChromaDB** – Resume vector storage
* **SQLite** – Resume version tracking
* **ReportLab** – PDF resume export

### Frontend

* **React.js**
* **TailwindCSS**
* **Vite**

---

## ⚙️ **Setup Instructions**

### 1️⃣ Clone the Repo

```bash
git clone https://github.com/ratnaksh12/ai-resume-agent.git
cd ai-resume-agent
```

---

### 2️⃣ Backend Setup

```bash
cd careerflow-agent-core
python -m venv venv
venv\Scripts\activate     # Windows
pip install -r requirements.txt
```

Create `.env` file:

```
GROQ_API_KEY=your_api_key_here
```

Run backend:

```bash
uvicorn app:app --reload
```

---

### 3️⃣ Frontend Setup

```bash
cd careerflow-frontend
npm install
npm run dev
```

---

## 🔌 **Key API Endpoints**

| Endpoint                          | Purpose                     |
| --------------------------------- | --------------------------- |
| `/upload_resume`                  | Upload and parse resume     |
| `/chat`                           | Run structured agents       |
| `/chat_nl`                        | Natural language agent chat |
| `/apply_changes`                  | Apply bullet updates        |
| `/resume/{id}/versions`           | List resume versions        |
| `/resume/{version_id}/export_pdf` | Download resume as PDF      |

---

## 📥 **PDF Resume Export**

* Generates **clean, structured resumes**
* Uses:

  * Section headers
  * Consistent spacing
  * Readable typography
* Downloadable directly from the frontend

---



