"""
orchestrator.py — Helpdesk Orchestrator & Multi-Agent Dispatcher.

Coordinates specialized agents:
  - PolicyAgent (rules, attendance, credits, grading, makeup)
  - ScheduleAgent (timetable, slots, course offerings count)
  - EmailAgent (faculty contact & email drafting)

Also enforces the Strict Out-Of-Scope Guard:
  Questions about dining options, city transit, hostels, general trivia, math, etc.,
  are explicitly refused without guessing, and logged to `unanswered_questions.jsonl`
  for human review.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from src.agents.email_agent import EmailAgent
from src.agents.policy_agent import PolicyAgent
from src.agents.schedule_agent import ScheduleAgent
from src.llm.client import LLMClient
from src.llm.prompts import ORCHESTRATOR_SYSTEM_PROMPT
from src.tools.definitions import log_unanswered_inquiry

logger = logging.getLogger("academic_helpdesk.orchestrator")


class AcademicHelpdeskOrchestrator:
    """
    Central multiagent orchestrator for the Academic Helpdesk System.
    """

    OUT_OF_SCOPE_PATTERNS = [
        re.compile(r"\b(dining|canteen\w*|food\w*|mess\w*|cafeteria\w*|cafe\w*|lunch\w*|dinner\w*|breakfast\w*|snack\w*|eater\w*)\b", re.I),
        re.compile(r"\b(reach the campus|city center|jodhpur city|transport\w*|bus\w*|cab\w*|taxi\w*|train\w*|airport\w*|railway\w*|auto-?rickshaw\w*|directions? to|route to campus)\b", re.I),
        re.compile(r"\b(hostel\w*|laundry\w*|gym\w*|swimming pool\w*|sports? tournament\w*|movie\w*|shopping\w*|weather\w*)\b", re.I),
        re.compile(r"(\b\d+\s*[\+\-\*\/\^%]\s*\d+\b|what is \d+\s*[\+\-\*\/]|calculate|solve \d+)", re.I),
        re.compile(r"\b(ceo of|who is the ceo|who founded|capital of|president of|prime minister|tell me a joke|write a poem|write code|google|microsoft|apple|meta|facebook|amazon|netflix)\b", re.I),
    ]

    ACADEMIC_KEYWORDS = [
        "attendance", "major", "minor", "exam", "grade", "credits", "cgpa", "sgpa",
        "slot", "course", "timetable", "schedule", "elective", "humanities", "cse", "ee", "me",
        "instructor", "faculty", "professor", "email", "leave", "sick", "makeup", "make-up",
        "condonation", "dx", "debarred", "b.tech", "m.tech", "degree", "curriculum", "ordinance",
        "regulation", "circular", "branch change", "withdraw", "add-drop", "prorating", "imo",
        "csl", "eel", "mel", "lal", "hsl", "mal", "sola", "iit", "iitj", "jodhpur", "academic"
    ]

    def __init__(self, llm_client: LLMClient | None = None, force_offline: bool = False):
        if llm_client is not None:
            self.llm = llm_client
        else:
            self.llm = LLMClient(force_offline=force_offline)
        self.policy_agent = PolicyAgent(self.llm)
        self.schedule_agent = ScheduleAgent(self.llm)
        self.email_agent = EmailAgent(self.llm)

    def route_intent(self, query: str) -> str:
        """Classify query into OUT_OF_SCOPE, EMAIL, SCHEDULE, or POLICY."""
        # 1. Explicit Out-of-scope check
        for pattern in self.OUT_OF_SCOPE_PATTERNS:
            if pattern.search(query):
                return "OUT_OF_SCOPE"

        q_lower = query.lower()

        # 2. Email drafting or instructor contact intent
        if any(term in q_lower for term in ["email", "draft", "write", "contact", "reach out to instructor"]):
            if any(term in q_lower for term in ["instructor", "professor", "faculty", "leave", "csl", "dr."]):
                return "EMAIL"

        # 3. Schedule / Timetable intent
        if any(term in q_lower for term in ["slot", "schedule", "timetable", "timing", "how many 400 level", "how many electives", "floated by"]):
            return "SCHEDULE"

        # 4. Check whether query contains any academic keywords
        has_academic_term = any(k in q_lower for k in self.ACADEMIC_KEYWORDS)
        if not has_academic_term:
            return "OUT_OF_SCOPE"

        # 5. Default academic queries route to Policy Agent
        return "POLICY"

    def process_query(self, query: str) -> dict[str, Any]:
        """
        Process a student query through the multi-agent system.
        """
        intent = self.route_intent(query)

        # ── Out-of-Scope Handling ─────────────────────────────────────────────
        if intent == "OUT_OF_SCOPE":
            refusal_reason = "non_academic_inquiry"
            if any(k in query.lower() for k in ["dining", "food", "snack", "canteen", "mess", "cafe", "eater"]):
                refusal_reason = "out_of_scope: campus dining options"
                topic = "campus dining options and eateries"
            elif any(k in query.lower() for k in ["reach", "city", "cab", "transport", "bus", "train", "taxi", "directions"]):
                refusal_reason = "out_of_scope: transportation / city directions"
                topic = "transportation and travel directions from Jodhpur city center"
            elif any(k in query.lower() for k in ["hostel", "laundry"]):
                refusal_reason = "out_of_scope: hostel facilities"
                topic = "hostel accommodation and amenities"
            elif any(k in query.lower() for k in ["sports", "gym", "tournament"]):
                refusal_reason = "out_of_scope: sports facilities"
                topic = "campus sports tournaments and gym schedules"
            elif "weather" in query.lower():
                refusal_reason = "out_of_scope: weather information"
                topic = "meteorological weather forecasts"
            elif any(k in query.lower() for k in ["1+1", "+", "calculate", "solve"]):
                refusal_reason = "out_of_scope: general mathematics / calculation"
                topic = "general mathematical calculations"
            elif any(k in query.lower() for k in ["ceo", "google", "president", "capital", "joke", "poem", "code"]):
                refusal_reason = "out_of_scope: general world trivia / non-academic knowledge"
                topic = "general world knowledge, external companies, or non-academic trivia"
            else:
                topic = "non-academic topics or general queries"

            # Log to unanswered_questions.jsonl for administrative human review
            log_unanswered_inquiry(query, refusal_reason)

            answer = (
                f"I am sorry, but I do not have information regarding **{topic}**. "
                f"As an Academic Helpdesk Agent, my scope is strictly limited to academic regulations, "
                f"course timetables, degree credit requirements, and academic faculty communications. "
                f"\n\n*Note: Your inquiry has been recorded in the administrator review queue for follow-up.*"
            )

            return {
                "orchestrator_decision": "REFUSAL (OUT_OF_SCOPE)",
                "assigned_agent": None,
                "query": query,
                "answer": answer,
                "citations": ["None (Refusal of out-of-scope inquiry)"],
                "is_out_of_scope": True,
                "logged_for_human_review": True,
                "backend": self.llm.backend_name,
            }

        # ── Multi-Agent Routing ───────────────────────────────────────────────
        if intent == "EMAIL":
            result = self.email_agent.run(query)
            result["orchestrator_decision"] = "ROUTED_TO_EMAIL_AGENT"
            result["is_out_of_scope"] = False
            return result

        if intent == "SCHEDULE":
            result = self.schedule_agent.run(query)
            result["orchestrator_decision"] = "ROUTED_TO_SCHEDULE_AGENT"
            result["is_out_of_scope"] = False
            return result

        # Default: Policy Agent
        result = self.policy_agent.run(query)
        result["orchestrator_decision"] = "ROUTED_TO_POLICY_AGENT"
        result["is_out_of_scope"] = False
        return result
