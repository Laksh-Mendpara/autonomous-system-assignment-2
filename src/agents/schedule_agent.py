"""
schedule_agent.py — Specialized Agent for Timetables, Slots, and Course Offerings.

Handles:
  - Course slot and timing queries (e.g. Autonomous Systems -> Slot H)
  - Timetable slot days and class meeting hours (e.g. Slot A, Slot H)
  - Department elective counts (e.g. 400 level Humanities electives count)
"""

from __future__ import annotations

import re
from typing import Any

from src.agents.base_agent import BaseAgent
from src.llm.client import LLMClient
from src.llm.prompts import SCHEDULE_SYSTEM_PROMPT
from tools.academic_tools import SLOT_TIMINGS


class ScheduleAgent(BaseAgent):
    """Specialized agent for academic timetables and course scheduling."""

    def __init__(self, llm_client: LLMClient | None = None):
        super().__init__(
            name="ScheduleAgent",
            system_prompt=SCHEDULE_SYSTEM_PROMPT,
            llm_client=llm_client,
            allowed_tools=["lookup_course_slot", "count_floated_courses"],
        )

    def run(self, query: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        """Determine appropriate tool and execute."""
        q_lower = query.lower()

        # 1. Department elective count query
        if "how many" in q_lower or "count" in q_lower or "floated" in q_lower:
            dept = "HS" if ("humanities" in q_lower or "hs" in q_lower or "sola" in q_lower) else "CSE"
            level = "400" if "400" in q_lower else ("700" if "700" in q_lower else "all")
            sem = "Sem2" if ("semester 2" in q_lower or "sem 2" in q_lower or "sem2" in q_lower) else "Sem1"
            initial_tool = ("count_floated_courses", {"dept": dept, "level": level, "semester": sem})
            return self._execute_tool_loop(query, initial_tool_call=initial_tool)

        # 2. Slot timing direct query (e.g., "timing of Slot A", "class timings and days for Slot H")
        slot_match = re.search(r"\bslot\s+([A-N])\b", query, re.I)
        if slot_match and not any(k in q_lower for k in ["course", "csl", "autonomous", "data structures"]):
            slot_letter = slot_match.group(1).upper()
            timing = SLOT_TIMINGS.get(slot_letter, "Special slot schedule")
            citation = "Timetable Slot Matrix (data/timetable/timetable_sem1_all_courses.csv)"
            return {
                "agent": self.name,
                "query": query,
                "answer": (
                    f"**Slot {slot_letter} Schedule Details**:\n\n"
                    f"• **Class Meeting Days & Timings**: {timing}\n"
                    f"• **Official Source**: {citation}"
                ),
                "citations": [citation],
                "trace": [{"step": "direct_slot_lookup", "slot": slot_letter, "timing": timing}],
                "backend": "schedule_agent_direct",
            }

        # 3. Course slot lookup query (e.g., "Autonomous Systems", "CSL2020", "CSL7570")
        course_id = "Autonomous Systems"
        if "csl" in q_lower:
            c_match = re.search(r"(csl\s*\d{4})", query, re.I)
            if c_match:
                course_id = c_match.group(1).replace(" ", "").upper()
        elif "autonomous systems" in q_lower:
            course_id = "Autonomous Systems"
        elif "data structures" in q_lower:
            course_id = "Data Structures"
        elif "operating systems" in q_lower:
            course_id = "Operating Systems"
        else:
            # Extract possible course code
            c_match = re.search(r"([A-Z]{3}\s*\d{4})", query, re.I)
            if c_match:
                course_id = c_match.group(1)

        sem = "Sem2" if ("semester 2" in q_lower or "sem 2" in q_lower) else "Sem1"
        initial_tool = ("lookup_course_slot", {"course_identifier": course_id, "semester": sem})
        return self._execute_tool_loop(query, initial_tool_call=initial_tool)

    def synthesize_from_tool_results(self, query: str, tool_results: list[tuple[str, Any]]) -> str:
        """Format schedule results into clear markdown answers."""
        for tool_name, result in tool_results:
            if tool_name == "count_floated_courses":
                dept = result.get("department", "Humanities")
                level = result.get("level", "400-level")
                sem = result.get("semester", "Semester 1")
                count = result.get("count", 0)
                courses = result.get("courses", [])

                lines = [
                    f"According to the official {sem} Timetable, the **Humanities and Social Sciences (HS / SoLA) Department** has floated **{count} electives (elective courses)** at the **{level}** in **{sem}**:\n"
                ]
                for c in courses[:6]:
                    lines.append(f"• **{c['code']}**: {c['name']} (Slot: {c['slot']}, Credits: {c['credits']}, Instructor: {c['instructor']})")
                if len(courses) > 6:
                    lines.append(f"• ... and {len(courses) - 6} additional elective course(s).")
                return "\n".join(lines)

            if tool_name == "lookup_course_slot":
                matches = result.get("matches", [])
                if matches:
                    primary = matches[0]
                    slot_val = primary['slot']
                    slot_str = f"Slot {slot_val}" if not slot_val.lower().startswith("slot") else slot_val
                    lines = [
                        f"**Course Schedule Details for {primary['course_code']} ({primary['course_name']})**:\n",
                        f"• **Slot**: **{slot_str}**",
                        f"• **Class Timings**: {primary.get('timing', 'Refer to slot matrix')}",
                        f"• **Instructor**: {primary.get('instructor', 'TBD')}",
                        f"• **L-T-P / Credits**: {primary.get('ltp', '3-0-0')} ({primary.get('credits', '3')} credits)",
                        f"• **Semester**: {primary.get('semester', 'Sem1')}",
                    ]
                    return "\n".join(lines)
                else:
                    return f"No timetable slot entry was found matching '{result.get('course_identifier')}'. Please verify the course code."

        return "Could not retrieve schedule information for the requested course."
