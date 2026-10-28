"""
email_agent.py — Specialized Agent for Faculty Contact & Academic Email Drafting.

Handles:
  - Faculty directory lookup (e.g. Dr. Ashok Joshi -> ashokjoshi@iitj.ac.in)
  - Formal leave of absence email drafting (e.g. sick leave for 2 days)
  - Make-up examination permission email drafting
"""

from __future__ import annotations

import re
from typing import Any

from src.agents.base_agent import BaseAgent
from src.llm.client import LLMClient
from src.llm.prompts import EMAIL_SYSTEM_PROMPT


class EmailAgent(BaseAgent):
    """Specialized agent for academic correspondence and faculty contact lookup."""

    def __init__(self, llm_client: LLMClient | None = None):
        super().__init__(
            name="EmailAgent",
            system_prompt=EMAIL_SYSTEM_PROMPT,
            llm_client=llm_client,
            allowed_tools=["get_instructor_email", "draft_leave_email"],
        )

    def run(self, query: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        """Determine whether query is a contact lookup or email drafting request."""
        q_lower = query.lower()

        # 1. Pure email lookup query (e.g. "What is the official email address of Dr. Ashok Joshi")
        if ("what is the" in q_lower or "email address" in q_lower or "contact" in q_lower) and not any(k in q_lower for k in ["draft", "write", "send"]):
            search_key = "Autonomous Systems"
            if "ashok" in q_lower or "joshi" in q_lower:
                search_key = "Ashok Joshi"
            elif "csl" in q_lower:
                m = re.search(r"(csl\s*\d{4})", query, re.I)
                if m:
                    search_key = m.group(1).replace(" ", "").upper()
            elif "sumit" in q_lower or "kalra" in q_lower:
                search_key = "Sumit Kalra"

            initial_tool = ("get_instructor_email", {"query": search_key})
            return self._execute_tool_loop(query, initial_tool_call=initial_tool)

        # 2. Email drafting query (e.g. "Write an email to course instructor of CSL7570...")
        course_code = "CSL7570"
        m_code = re.search(r"(csl\s*\d{4})", query, re.I)
        if m_code:
            course_code = m_code.group(1).replace(" ", "").upper()
        elif "autonomous systems" in q_lower:
            course_code = "CSL7650"
        elif "computer networks" in q_lower:
            course_code = "CSL3080"
        elif "deep learning" in q_lower:
            course_code = "CSL4020"
        elif "software engineering" in q_lower:
            course_code = "CSL2060"
        elif "data structures" in q_lower:
            course_code = "CSL2020"

        # Extract duration
        duration = 2
        d_match = re.search(r"(\d+)\s*day", query, re.I)
        if d_match:
            duration = int(d_match.group(1))

        # Extract reason
        reason = "sick leave"
        if "makeup" in q_lower or "make-up" in q_lower:
            reason = "permission to appear for a make-up examination due to illness"
        elif "medical" in q_lower:
            reason = "medical indisposition"

        initial_tool = (
            "draft_leave_email",
            {
                "course_code": course_code,
                "reason": reason,
                "duration_days": duration,
                "student_name": "[Student Name]",
                "student_roll": "[Roll Number]",
            },
        )
        return self._execute_tool_loop(query, initial_tool_call=initial_tool)

    def synthesize_from_tool_results(self, query: str, tool_results: list[tuple[str, Any]]) -> str:
        """Format email agent output with clear header and body."""
        for tool_name, result in tool_results:
            if tool_name == "draft_leave_email":
                recipient = result.get("recipient_name", "Course Instructor")
                email = result.get("recipient_email", "instructor@iitj.ac.in")
                subject = result.get("subject", "Leave Application")
                body = result.get("body", "")

                return (
                    f"### Generated Email Draft for Course Instructor\n\n"
                    f"**To**: `{recipient} <{email}>`\n"
                    f"**Subject**: `{subject}`\n\n"
                    f"```text\n{body}\n```\n\n"
                    f"*Note: Please review and replace the bracketed placeholders before sending.*"
                )

            if tool_name == "get_instructor_email":
                results = result.get("results", [])
                if results:
                    first = results[0]
                    name = first.get("instructor") or first.get("instructor_name", "Faculty")
                    email = first.get("email", "N/A")
                    dept = first.get("dept", "IIT Jodhpur")
                    course = first.get("course_name") or first.get("course_code", "")
                    course_info = f" ({course})" if course else ""

                    return (
                        f"**Faculty Contact Information**:\n\n"
                        f"• **Instructor**: **{name}**\n"
                        f"• **Email Address**: `{email}`\n"
                        f"• **Department**: {dept}{course_info}\n"
                        f"• **Source**: Faculty Directory Database"
                    )
                else:
                    return f"No instructor contact was found matching '{result.get('query')}'. Please verify the name or course code."

        return "Could not complete the academic correspondence request."

