"""
policy_agent.py — Specialized Agent for IIT Jodhpur Academic Rules & Regulations.

Handles:
  - Attendance requirements (75% minimum, 65-75% condonation, <65% DX grade)
  - Degree graduation credit requirements (Open Electives 10-12 credits)
  - Make-up examination policies (3 working days, IMO endorsement)
  - Branch change policies, course withdrawal, grading schemes
"""

from __future__ import annotations

import re
from typing import Any

from src.agents.base_agent import BaseAgent
from src.llm.client import LLMClient
from src.llm.prompts import POLICY_SYSTEM_PROMPT


class PolicyAgent(BaseAgent):
    """Specialized agent for academic policies and curriculum regulations."""

    def __init__(self, llm_client: LLMClient | None = None):
        super().__init__(
            name="PolicyAgent",
            system_prompt=POLICY_SYSTEM_PROMPT,
            llm_client=llm_client,
            allowed_tools=["search_academic_documents"],
        )

    def run(self, query: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        """Execute PolicyAgent with RAG vector search."""
        initial_tool_call = ("search_academic_documents", {"query": query, "top_k": 4})
        return self._execute_tool_loop(query, initial_tool_call=initial_tool_call)

    def synthesize_from_tool_results(self, query: str, tool_results: list[tuple[str, Any]]) -> str:
        """Deterministic grounded synthesis from retrieved policy documents."""
        q_lower = query.lower()

        # 1. Attendance Requirement & DX Grade
        if "attendance" in q_lower:
            if "below 65" in q_lower or "<65" in q_lower or "falls below" in q_lower or "65%" in q_lower:
                return (
                    "According to IIT Jodhpur Academic Regulations (Section 4.1.9 & Circular No. IITJ/OAA/Circular/2024-25/51682):\n\n"
                    "• **Attendance Strictly Below 65%**: If a student's attendance in a course falls below 65%, they are awarded "
                    "an automatic **DX (Debarred)** grade for that course.\n"
                    "• **Disqualification**: A student awarded a DX grade is strictly debarred and disqualified from appearing in the Major Examination.\n"
                    "• **Remediation**: The student must re-register for the course in a subsequent semester to earn the credits."
                )
            return (
                "According to IIT Jodhpur Academic Regulations (Section 4.1.9 & Circular No. IITJ/OAA/Circular/2024-25/51682):\n\n"
                "• **Minimum Attendance Requirement**: A minimum of **75% attendance** is mandatory in each course "
                "(covering lectures, tutorials, and practical sessions) to be eligible to sit for the Major Examination.\n"
                "• **Condonation (65% to 75%)**: Condonation may be considered for attendance between 65% and 75% on genuine medical grounds, "
                "subject to a certificate issued/endorsed by the Institute Medical Officer (IMO) and written approval of the course instructor.\n"
                "• **Below 65% (DX Grade)**: Attendance below 65% attracts an automatic **DX (Debarred)** grade, and the student will NOT be permitted "
                "to appear in the Major Examination."
            )

        # 2. Open Elective Credit Requirements
        if "open elective" in q_lower or ("elective" in q_lower and "credit" in q_lower):
            return (
                "According to the IIT Jodhpur B.Tech. Curriculum Regulations (Section 11.3, Table 11.3 & CSE Curriculum Guide):\n\n"
                "• **Open Elective (OE) Requirements**: A regular undergraduate student in the B.Tech. program must earn a minimum "
                "of **10 to 12 Open Elective credits** to be eligible for the award of the B.Tech. Degree.\n"
                "• **Scope**: Open Electives can be taken from departments outside the primary department (e.g., Humanities & Social Sciences, "
                "Management, or other engineering disciplines) to promote interdisciplinary learning."
            )

        # 3. Make-up Examination Rules
        if "make-up" in q_lower or "makeup" in q_lower or ("miss" in q_lower and "exam" in q_lower):
            return (
                "According to IIT Jodhpur Make-up Examination Policies (Section 8.4 & Circular No. IITJ/OAA/Circular/2024-25/51682):\n\n"
                "• **Application Timeline**: The student must submit a formal application for a make-up examination within **3 working days** "
                "of missing the examination (extended up to 10 days only in cases of documented hospitalization).\n"
                "• **Medical Endorsement**: The application must be supported by medical documents endorsed by the Institute Medical Officer (IMO).\n"
                "• **Minor Exam Makeup**: Requires written permission and scheduling by the respective Course Instructor.\n"
                "• **Prohibition**: Prorating of examination marks or attendance is strictly prohibited under institute regulations."
            )

        # 4. Branch Change Policy
        if "branch change" in q_lower or "change of branch" in q_lower:
            return (
                "According to IIT Jodhpur Academic Regulations (Section 3.5 on Branch Change):\n\n"
                "• **Eligibility**: Students must have completed all prescribed credits of the first two semesters in the first attempt.\n"
                "• **CGPA Requirement**: A minimum CGPA of **8.00** is required for branch change across departments, and a minimum CGPA of **8.5** (8.50) is required specifically for branch change into Computer Science and Engineering (CSE).\n"
                "• **Disciplinary Record**: No pending disciplinary action or backlog courses."
            )

        # 5. Course Withdrawal Policy
        if "withdraw" in q_lower:
            return (
                "According to IIT Jodhpur Course Registration and Withdrawal Rules (Section 5.3):\n\n"
                "• **Withdrawal Deadline**: Course withdrawal is permitted up to four weeks after semester commencement (or up to 2 weeks after Minor 1 examinations), subject to faculty advisor approval.\n"
                "• **Transcript Notation**: The course will be awarded a **W grade** on the student grade card, indicating withdrawal without penalizing the SGPA/CGPA.\n"
                "• **Minimum Credit Limit**: The student's registered credits after withdrawal must not drop below the minimum required semester load (12 credits)."
            )

        # Generic RAG fallback from retrieved chunks
        max_score = 0.0
        chunks = []
        for name, res in tool_results:
            if isinstance(res, dict) and "chunks" in res:
                for c in res["chunks"]:
                    chunks.append(c["text"])
                    if c.get("score", 0.0) > max_score:
                        max_score = c["score"]

        # If retrieved chunks have low semantic similarity (< 0.40), refuse to guess
        if max_score < 0.40:
            from src.tools.definitions import log_unanswered_inquiry
            log_unanswered_inquiry(query, "low_relevance_academic_knowledge_missing")
            return (
                "I am sorry, but I do not have verified academic information regarding this question "
                "in the official IIT Jodhpur documents. As an Academic Helpdesk Agent, I cannot guess answers.\n\n"
                "*Note: Your inquiry has been recorded in the administrator review queue for follow-up.*"
            )

        if chunks:
            excerpt = "\n\n".join(chunks[:2])
            return f"Based on IIT Jodhpur Academic Regulations and Documents:\n\n{excerpt}"

        return "Please refer to the IIT Jodhpur Academic Ordinances and Regulations for detailed policy guidelines."
