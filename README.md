# IIT Jodhpur — Multi-Agent Academic Helpdesk System

> An autonomous, retrieval-augmented multi-agent helpdesk system designed for academic administration at the **Indian Institute of Technology Jodhpur (IIT Jodhpur)**. Capable of answering inquiries regarding academic ordinances, curricula, degree credit requirements, class timetable slots, and drafting formal faculty correspondence—with strict out-of-scope guardrails and 100% verifiable citations.

---

## 📋 Table of Contents
1. [Overview & Key Features](#overview--key-features)
2. [Multi-Agent System Architecture](#multi-agent-system-architecture)
3. [Repository Structure](#repository-structure)
4. [Hardware Profile & 16GB RAM Optimization](#hardware-profile--16gb-ram-optimization)
5. [Installation & Setup](#installation--setup)
6. [Interactive Terminal Chatbot](#interactive-terminal-chatbot)
7. [Benchmark Evaluation & Results (`result.txt`)](#benchmark-evaluation--results-resulttxt)
8. [Docker & Local LLM Deployment](#docker--local-llm-deployment)
9. [Academic Report (`report.pdf`)](#academic-report-reportpdf)
10. [Audit Logging for Human Review](#audit-logging-for-human-review)
11. [Submission Package (`submission/`)](#submission-package-submission)

---

## 🚀 Overview & Key Features

Navigating higher education administration is often challenging for students due to scattered academic ordinances, syllabi, course timetables, and faculty directories. This system provides an autonomous academic helpdesk that combines:
- **Modular Multi-Agent Architecture**: A central **Helpdesk Orchestrator** dispatches queries to domain-specialist agents (**PolicyAgent**, **ScheduleAgent**, **EmailAgent**).
- **Persistent ChromaDB Vector Store**: Dense semantic indexing of 27 official institute documents across **4,297 chunks** (`hnsw:space: cosine`, 80MB embedding footprint, zero network at query time).
- **Relational Timetable & Faculty Tools**: Deterministic Python tool suite for CSV timetable slot matching, class meeting time matrix, department elective offerings counts, and instructor directory lookups.
- **Strict Out-of-Scope (OOS) Guard**: Enforces institute policy by refusing non-academic inquiries (campus dining, city transit, hostels, gym, weather, general trivia, math) without hallucination or guessing, logging each refusal to `unanswered_questions.jsonl` for administrative review.
- **16GB RAM Laptop Readiness**: Optimized for local execution with 4-bit quantized 8B chat models (e.g., Llama 3.1 8B, Qwen 2.5 7B) through LiteLLM or an instant deterministic grounded offline synthesizer with circuit breaker.
- **100% Verifiable Grounded Citations**: Every generated academic response explicitly cites the specific regulation, circular number, or timetable source file.

---

## 🏛️ Multi-Agent System Architecture

```
                       ┌─────────────────────────┐
                       │   Student Inquiry Input │
                       │  (Terminal / CLI / API) │
                       └────────────┬────────────┘
                                    │
                                    ▼
                 ┌──────────────────────────────────────┐
                 │        Helpdesk Orchestrator         │
                 │   - Intent Classification & Routing  │
                 │   - Strict Out-of-Scope Refusal Guard│
                 └──────┬───────────┬───────────┬───────┘
                        │           │           │
       ┌────────────────┘           │           └────────────────┐
       ▼                            ▼                            ▼
┌──────────────┐             ┌──────────────┐             ┌──────────────┐
│ Policy Agent │             │Schedule Agent│             │ Email Agent  │
├──────────────┤             ├──────────────┤             ├──────────────┤
│- Regulations │             │- Timetables  │             │- Faculty Map │
│- Attendance  │             │- Slot Matrix │             │- Leave Draft │
│- 10-12 OE Cr │             │- 400L Counts │             │- Makeup Exam │
└──────┬───────┘             └──────┬───────┘             └──────┬───────┘
       │                            │                            │
       ▼                            ▼                            ▼
┌──────────────┐             ┌──────────────┐             ┌──────────────┐
│   ChromaDB   │             │Timetable CSVs│             │Faculty Direct│
│ Vector Store │             │ (Sem 1 & 2)  │             │  & Leave Tmpl│
│(4,297 Chunks)│             │ (Slots A-N)  │             │ (Course Map) │
└──────┬───────┘             └──────┬───────┘             └──────┬───────┘
       │                            │                            │
       └────────────────────────────┼────────────────────────────┘
                                    │
                                    ▼
                 ┌──────────────────────────────────────┐
                 │     Grounded Response Formulation    │
                 │    + Official Institute Citations    │
                 └──────────────────────────────────────┘
```

### Specialized Agents

1. **Academic Helpdesk Orchestrator (`src/agents/orchestrator.py`)**:
   - Analyzes incoming queries via regex and semantic classification.
   - Detects out-of-scope queries (campus dining, transit, hostels, sports, weather, math, general trivia).
   - Writes out-of-scope inquiries to `unanswered_questions.jsonl` and emits a polite, standard refusal.
   - Dispatches academic queries to the designated worker agent.

2. **Policy Agent (`src/agents/policy_agent.py`)**:
   - Resolves questions on academic ordinances, exam eligibility, degree requirements, and branch changes.
   - Cites official rules:
     - **Attendance**: Minimum 75% attendance in lectures, tutorials, and practicals.
     - **Condonation**: 65% to 75% attendance condonable on medical grounds validated by the Institute Medical Officer (IMO).
     - **DX Grade**: Strictly below 65% attendance results in an automatic **DX (Debarred)** grade.
     - **Graduation Requirements**: Regular B.Tech. students must earn **10 to 12 Open Elective (OE) credits**.
     - **Makeup Examinations**: Formal application required within 3 working days with IMO endorsement; prorating of marks is strictly prohibited.
     - **Branch Change**: Minimum CGPA of 8.00 (8.50 for Computer Science & Engineering).

3. **Schedule Agent (`src/agents/schedule_agent.py`)**:
   - Handles course slot queries (e.g., *Autonomous Systems* $\rightarrow$ Slot H, Tue/Thu/Sat 11:00--11:55 AM, Dr. Ashok Joshi).
   - Queries slot matrix timings (Slots A through N).
   - Computes department course offerings (e.g., 11 400-level Humanities electives in Semester 1, 10 in Semester 2).

4. **Email Agent (`src/agents/email_agent.py`)**:
   - Queries the faculty email directory and course-instructor mapping.
   - Automatically drafts formal, institute-compliant student emails for sick leave or makeup exam permissions, referencing Section 15/23 and Circular 51682.

---

## 📁 Repository Structure

```
autonomous_assignment/
├── README.md                           # Main project documentation (this file)
├── benchmark_questions.json            # 25 curated benchmark questions with ground truth
├── benchmark_questions.md              # Markdown formatted benchmark question suite
├── result.txt                          # Comprehensive evaluation report with all 25 responses
├── chatbot.py                          # Interactive terminal chatbot (stateless single-turn Q&A)
├── main.py                             # Evaluation runner & CLI entry point
├── pyproject.toml                      # Project metadata and dependencies
├── unanswered_questions.jsonl          # Audit log of out-of-scope inquiries for human review
│
├── data/                               # 27 Organized real institute documents
│   ├── policies/                       # Academic regulations, attendance amendment circulars
│   ├── curriculum/                     # B.Tech. CSE curriculum guide, credit requirements
│   ├── timetable/                      # Sem 1 & Sem 2 all-course timetable CSVs, slot matrix
│   ├── faculty/                        # Faculty email directory, course-instructor mapping
│   ├── course_details/                 # Course descriptions and syllabus summaries
│   └── office_orders/                  # Institute notices and official academic circulars
│
├── src/                                # Core multi-agent package
│   ├── agents/
│   │   ├── base_agent.py               # Abstract agent base class with tool-loop execution
│   │   ├── orchestrator.py             # Orchestrator & Out-of-Scope Guard
│   │   ├── policy_agent.py             # Specialized Policy Agent
│   │   ├── schedule_agent.py           # Specialized Schedule Agent
│   │   └── email_agent.py              # Specialized Email & Correspondence Agent
│   ├── llm/
│   │   ├── client.py                   # LiteLLM wrapper with circuit-breaker & auto-detect
│   │   └── prompts.py                  # Agent system prompts and role definitions
│   ├── rag/
│   │   ├── chunker.py                  # Category-aware document chunker
│   │   ├── document_loader.py          # PDF, Markdown, CSV, XML/XLSX loader
│   │   ├── embedder.py                 # Offline-cached all-MiniLM-L6-v2 embedder
│   │   ├── retriever.py                # Semantic retriever with query intent routing
│   │   └── vector_store.py             # ChromaDB persistent collection manager
│   ├── tools/
│   │   └── definitions.py              # Tool schemas (LiteLLM compatible) & dispatcher
│   └── evaluation/
│       ├── benchmark_prompts.py        # Benchmark prompt loader
│       └── evaluator.py                # Automated 25-question evaluation suite
│
├── tools/
│   └── academic_tools.py               # Standalone deterministic tools
│
├── docker/                             # Containerization files
│   ├── docker-compose.yml              # Multi-service compose for Ollama and llama.cpp
│   ├── run_ollama.sh                   # Ollama 8B model startup script
│   ├── run_llama_cpp.sh                # Docker llama.cpp server startup script
│   └── README.md                       # Docker guide & RAM breakdown
│
├── report/                             # Academic LaTeX report
│   ├── report.tex                      # Complete 6-page academic paper source
│   └── report.pdf                      # Compiled publication-ready PDF
│
└── submission/                         # Clean submission package (no venv, no raw vector db)
    ├── README.md                       # Standalone submission documentation
    ├── report.pdf                      # Complete academic report
    ├── benchmark_questions.json        # Curated test questions
    ├── benchmark_questions.md          # Benchmark question documentation
    ├── result.txt                      # 25-question evaluation log with all responses
    ├── chatbot.py                      # Interactive terminal chatbot
    ├── main.py                         # Unified test runner
    ├── pyproject.toml                  # Dependencies & package metadata
    ├── data/                           # 27 Curated academic documents
    ├── src/                            # Complete multi-agent codebase
    ├── tools/                          # Standalone tool suite
    ├── docker/                         # Docker container configurations
    └── unanswered_questions.jsonl      # Audit trail for human review
```

---

## 💻 Hardware Profile & 16GB RAM Optimization

The system is configured specifically to operate within 16GB of system RAM:

| Component | Implementation | RAM Allocation | % of 16GB |
| :--- | :--- | :--- | :--- |
| **OS & Daemons** | Linux kernel, background services | $\approx$2.0 GB | 12.5% |
| **Vector Embedder** | `all-MiniLM-L6-v2` (PyTorch CPU) | $\approx$0.3 GB | 1.9% |
| **Vector Store** | ChromaDB SQLite + HNSW cache | $\approx$0.2 GB | 1.3% |
| **Language Model** | Quantized 8B (Q4_K_M GGUF via Ollama) | $\approx$5.2 GB | 32.5% |
| **Python Runtime** | Multi-agent orchestrator, tools, UI | $\approx$0.3 GB | 1.9% |
| **Available Buffer** | System cache, dynamic swap headroom | $\approx$8.0 GB | 50.0% |
| **Total Peak Footprint**| | **$\approx$8.0 GB** | **50.0%** |

---

## ⚙️ Installation & Setup

### 1. Prerequisites
- Linux / macOS with Python 3.10+
- `uv` (recommended) or standard Python `venv`
- `pdflatex` (TeX Live) for compiling the report

### 2. Environment Setup with `uv`
```bash
# Clone or navigate to the workspace
cd /home/laksh/autonomous_assignment

# Activate the virtual environment
source .venv/bin/activate
```

If initializing a fresh virtual environment:
```bash
uv venv .venv --python 3.12
source .venv/bin/activate
uv pip install -e .
```

---

## 💬 Interactive Terminal Chatbot

The terminal chatbot (`chatbot.py`) provides a single-turn, stateless Q&A interface (no conversational memory overhead). Each query is routed through the multi-agent orchestrator and rendered with Rich UI formatting:

```bash
.venv/bin/python chatbot.py
```

### Sample Sessions

**1. Course Schedule Query:**
```text
Student Query > What is the slot for the course Autonomous Systems?
Agent Assigned: ScheduleAgent (ROUTED_TO_SCHEDULE_AGENT)
╭──────────────────── 🎓 Helpdesk Response (ScheduleAgent) ────────────────────╮
│ Course Schedule Details for CSL7650 (Autonomous Systems):                    │
│                                                                              │
│ • Slot: Slot H                                                               │
│ • Class Timings: Tuesday, Thursday, Saturday 11:00 - 11:55 AM                │
│ • Instructor: Ashok Joshi                                                    │
│ • L-T-P / Credits: 3-0-0 (3 credits)                                         │
│ • Semester: Sem1                                                             │
╰──────────────────────────────────────────────────────────────────────────────╯
📚 Grounded Sources & Citations:
  • Timetable Sem1 (CSE Department)
```

**2. Out-of-Scope Refusal (Logged to Audit Queue):**
```text
Student Query > What are the available dining options on the campus?
╭───────── 🛑 Refusal — Out of Academic Scope (Logged to Audit File) ──────────╮
│ I am sorry, but I do not have information regarding campus dining options    │
│ and eateries. As an Academic Helpdesk Agent, my scope is strictly limited to │
│ academic regulations, course timetables, degree credit requirements, and     │
│ academic faculty communications.                                             │
│                                                                              │
│ Note: Your inquiry has been recorded in the administrator review queue for   │
│ follow-up.                                                                   │
╰──────────────────────────────────────────────────────────────────────────────╯
```

---

## 📊 Benchmark Evaluation & Results (`result.txt`)

The system includes an automated evaluation suite (`src/evaluation/evaluator.py`) testing **25 benchmark questions** spanning all four domains:

```bash
# Run benchmark evaluation:
.venv/bin/python main.py
# or
.venv/bin/python -m src.evaluation.evaluator
```

The entire execution, detailed responses, and grounded citations for all 25 questions are saved directly to [`result.txt`](result.txt).

### Summary Evaluation Metrics

```
================================================================================
  ACADEMIC HELPDESK MULTI-AGENT SYSTEM — BENCHMARK EVALUATION
================================================================================
  • Total Evaluated Prompts:    25
  • Intent Routing Accuracy:    25/25 (100.0%)
  • Answer Accuracy:            25/25 (100.0%)
  • Groundedness / Citations:   25/25 (100.0%)
  • Out-of-Scope Refusal Rate:  7/7 (100.0%)
================================================================================
[+] Detailed evaluation report and responses saved to: result.txt
```

### Benchmark Question Breakdown

| ID | Domain | Prompt Summary | Target Agent | Result |
| :--- | :--- | :--- | :--- | :---: |
| `POL_01` | Policy | Major exam 75% attendance requirement | PolicyAgent | **PASS** |
| `POL_02` | Policy | Attendance falling below 65% (DX grade) | PolicyAgent | **PASS** |
| `POL_03` | Policy | Open elective credits for B.Tech. (10--12 credits) | PolicyAgent | **PASS** |
| `POL_04` | Policy | Makeup exam rules for missed Minor 1 | PolicyAgent | **PASS** |
| `POL_05` | Policy | Minimum CGPA for branch change (8.00 / 8.50 CSE) | PolicyAgent | **PASS** |
| `POL_06` | Policy | Course withdrawal after add-drop deadline | PolicyAgent | **PASS** |
| `SCH_01` | Schedule | Slot for Autonomous Systems (Slot H) | ScheduleAgent | **PASS** |
| `SCH_02` | Schedule | Class timings and days for Slot H | ScheduleAgent | **PASS** |
| `SCH_03` | Schedule | 400-level Humanities electives in Sem 1 (11 courses) | ScheduleAgent | **PASS** |
| `SCH_04` | Schedule | 400-level Humanities electives in Sem 2 (10 courses) | ScheduleAgent | **PASS** |
| `SCH_05` | Schedule | Slot & instructor for CSL2020 DSA (Slot B, Suchetana) | ScheduleAgent | **PASS** |
| `SCH_06` | Schedule | Timing of Slot A lectures (Mon/Wed/Fri 08:00 AM) | ScheduleAgent | **PASS** |
| `EML_01` | Email | Sick leave email to CSL7570 instructor | EmailAgent | **PASS** |
| `EML_02` | Email | Makeup exam email for Autonomous Systems | EmailAgent | **PASS** |
| `EML_03` | Email | 3-day sick leave email for CSL3080 | EmailAgent | **PASS** |
| `EML_04` | Email | 1-day leave draft for CSL4020 Deep Learning | EmailAgent | **PASS** |
| `EML_05` | Email | Official email address for Dr. Ashok Joshi | EmailAgent | **PASS** |
| `EML_06` | Email | Leave email for CSL2060 Software Engineering | EmailAgent | **PASS** |
| `OOS_01` | Out-of-Scope | Campus dining options | Refusal Guard | **PASS** |
| `OOS_02` | Out-of-Scope | Best way to reach campus from city center | Refusal Guard | **PASS** |
| `OOS_03` | Out-of-Scope | Late-night snacks or canteens on campus | Refusal Guard | **PASS** |
| `OOS_04` | Out-of-Scope | Booking a cab from railway station to IIT | Refusal Guard | **PASS** |
| `OOS_05` | Out-of-Scope | Sports tournaments in campus gym | Refusal Guard | **PASS** |
| `OOS_06` | Out-of-Scope | Weather forecast for Jodhpur this week | Refusal Guard | **PASS** |
| `OOS_07` | Out-of-Scope | Which hostel has best laundry facilities | Refusal Guard | **PASS** |

---

## 🐳 Docker & Local LLM Deployment

To execute with a live 8B local LLM via Ollama or llama.cpp:

### Option A: Using Ollama
```bash
# Start Ollama container and pull 8B chat model
./docker/run_ollama.sh

# Run chatbot (automatically connects via LiteLLM)
.venv/bin/python chatbot.py
```

### Option B: Using Docker Compose
```bash
docker compose -f docker/docker-compose.yml up -d
```

### Option C: Using llama.cpp
```bash
./docker/run_llama_cpp.sh
```

---

## 📄 Academic Report (`report.pdf`)

A complete academic report has been authored and compiled to PDF:
* **PDF File**: [`report/report.pdf`](report/report.pdf) (6 pages, 269 KB).
* **LaTeX Source**: [`report/report.tex`](report/report.tex).
* **Compilation Command**:
  ```bash
  cd report
  TEXMFVAR=/tmp/texmf-var pdflatex -interaction=nonstopmode report.tex
  TEXMFVAR=/tmp/texmf-var pdflatex -interaction=nonstopmode report.tex
  ```

---

## 📝 Audit Logging for Human Review

All queries identified as out-of-scope or unresolvable are automatically appended to `unanswered_questions.jsonl` in JSON Lines format:

```json
{"timestamp": "2026-10-29T01:17:37.590976", "question": "What are the available dining options on the campus?", "reason": "out_of_scope: campus dining options", "metadata": {}}
```

This log serves as a human-in-the-loop audit trail enabling academic administrators to track student demand patterns and update FAQ databases accordingly.

---

## 📦 Submission Package (`submission/`)

The standalone submission package is located in `submission/`:
* Contains all required project code, dataset files, tools, docker configurations, evaluation suite, and documentation.
* **Excluded**: Virtual environments (`.venv/`), raw vector database binaries (`vectorstore/`), and LaTeX source (`report.tex`).
* **Included Report**: Clean, compiled [`report.pdf`](submission/report.pdf).
* **Included Results**: Detailed [`result.txt`](submission/result.txt) with all 25 benchmark runs and generated responses.

---

## 👥 Authors
- **Autonomous Systems Assignment Team**
- Department of Computer Science and Engineering, IIT Jodhpur
- Academic Year: 2026–2027
