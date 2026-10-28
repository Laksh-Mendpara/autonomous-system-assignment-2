"""
definitions.py — Academic Helpdesk Tool Schemas & Executable Dispatcher.

Provides tools for:
  1. Semantic Vector Store Search (`search_academic_documents`)
  2. Timetable Course Slot & Timings Lookup (`lookup_course_slot`)
  3. Faculty Email & Instructor Directory Lookup (`get_instructor_email`)
  4. Course Level / Department Offerings Counter (`count_floated_courses`)
  5. Student Formal Leave / Makeup Email Drafter (`draft_leave_email`)
  6. Out-of-Scope Logging for Human Review (`log_unanswered_inquiry`)
"""

from __future__ import annotations

import logging
from typing import Any

from src.rag.retriever import Retriever
from src.rag.vector_store import VectorStore
from tools.academic_tools import (
    count_floated_courses as _count_floated_courses,
    draft_leave_email as _draft_leave_email,
    get_instructor_email as _get_instructor_email,
    log_unanswered_question as _log_unanswered_question,
    lookup_course_slot as _lookup_course_slot,
)

logger = logging.getLogger("academic_helpdesk.tools")

# Lazy singleton vector retriever
_RETRIEVER_INSTANCE: Retriever | None = None


def get_retriever() -> Retriever:
    global _RETRIEVER_INSTANCE
    if _RETRIEVER_INSTANCE is None:
        store = VectorStore()
        _RETRIEVER_INSTANCE = Retriever(store)
    return _RETRIEVER_INSTANCE


def search_academic_documents(query: str, top_k: int = 4) -> dict[str, Any]:
    """
    Search indexed academic ordinances, curriculum guides, and office orders
    using ChromaDB dense semantic retrieval.
    """
    retriever = get_retriever()
    results = retriever.retrieve(query, top_k=top_k)
    chunks = [
        {
            "text": r.text,
            "source": r.source,
            "category": r.category,
            "score": round(r.score, 4),
            "citation": r.citation,
            "filename": r.metadata.get("filename", r.source),
        }
        for r in results
    ]
    citations = list({c["filename"] for c in chunks})
    return {
        "query": query,
        "count": len(chunks),
        "chunks": chunks,
        "citations": citations,
    }


def lookup_course_slot(course_identifier: str, semester: str = "Sem1") -> dict[str, Any]:
    """Lookup timetable slot, timings, and instructor for a course."""
    results = _lookup_course_slot(course_identifier, semester)
    citations = list({r.get("citation", "Timetable CSV") for r in results})
    return {
        "course_identifier": course_identifier,
        "semester": semester,
        "matches": results,
        "citation": citations[0] if citations else "Timetable Database (data/timetable/)",
        "citations": citations,
    }


def get_instructor_email(query: str) -> dict[str, Any]:
    """Lookup faculty email by course code, course name, or professor name."""
    results = _get_instructor_email(query)
    citations = list({r.get("citation", "Faculty Directory") for r in results})
    return {
        "query": query,
        "results": results,
        "citation": citations[0] if citations else "Faculty Directory (data/faculty/)",
        "citations": citations,
    }


def count_floated_courses(dept: str = "HS", level: str = "400", semester: str = "Sem1") -> dict[str, Any]:
    """Count how many courses of a specific level have been floated by a department."""
    res = _count_floated_courses(dept=dept, level=level, semester=semester)
    res["citations"] = [res["citation"]]
    return res


def draft_leave_email(
    course_code: str,
    reason: str = "sick-leave",
    duration_days: int = 2,
    student_name: str = "[Student Name]",
    student_roll: str = "[Roll Number]",
    start_date: str = "[Start Date]",
    end_date: str = "[End Date]",
) -> dict[str, Any]:
    """Draft a formal email to a course instructor for leave or makeup exam permission."""
    res = _draft_leave_email(
        course_code=course_code,
        reason=reason,
        duration_days=duration_days,
        student_name=student_name,
        student_roll=student_roll,
        start_date=start_date,
        end_date=end_date,
    )
    res["citations"] = [res["citation"]]
    return res


def log_unanswered_inquiry(question: str, reason: str = "out_of_scope") -> bool:
    """Log an unanswered inquiry for administrative human review."""
    return _log_unanswered_question(question=question, reason=reason)


# ── LiteLLM Tool Schemas (OpenAI-compatible) ──────────────────────────────────
TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "search_academic_documents",
            "description": "Search official academic regulations, degree requirements, attendance rules, and ordinances from the ChromaDB vector store.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query to match against academic documents"},
                    "top_k": {"type": "integer", "description": "Number of chunks to retrieve (default: 4)"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "lookup_course_slot",
            "description": "Find the slot, meeting timings, lecture days, and instructor for a course from the timetable database.",
            "parameters": {
                "type": "object",
                "properties": {
                    "course_identifier": {"type": "string", "description": "Course code (e.g. CSL7650, CSL7570) or course name (e.g. Autonomous Systems)"},
                    "semester": {"type": "string", "description": "Semester ('Sem1' or 'Sem2')", "default": "Sem1"},
                },
                "required": ["course_identifier"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_instructor_email",
            "description": "Look up an instructor's official email address by course code, course title, or instructor name.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Course code or instructor name"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "count_floated_courses",
            "description": "Count how many elective courses of a given level (e.g. 400 level) are floated by a department (e.g. Humanities) in a semester.",
            "parameters": {
                "type": "object",
                "properties": {
                    "dept": {"type": "string", "description": "Department name or code (e.g. HS, Humanities, CSE)", "default": "HS"},
                    "level": {"type": "string", "description": "Course level prefix (e.g. 400, 700)", "default": "400"},
                    "semester": {"type": "string", "description": "Semester ('Sem1' or 'Sem2')", "default": "Sem1"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "draft_leave_email",
            "description": "Draft a formal email application to a course instructor for leave of absence or makeup exam permission.",
            "parameters": {
                "type": "object",
                "properties": {
                    "course_code": {"type": "string", "description": "Course code (e.g. CSL7570, CSL7650, CSL3080)"},
                    "reason": {"type": "string", "description": "Reason for leave (e.g. sick-leave, fever, medical emergency)"},
                    "duration_days": {"type": "integer", "description": "Number of days of leave requested"},
                    "student_name": {"type": "string", "description": "Name of the student"},
                    "student_roll": {"type": "string", "description": "Student roll number"},
                },
                "required": ["course_code"],
            },
        },
    },
]

TOOL_MAP = {
    "search_academic_documents": search_academic_documents,
    "lookup_course_slot": lookup_course_slot,
    "get_instructor_email": get_instructor_email,
    "count_floated_courses": count_floated_courses,
    "draft_leave_email": draft_leave_email,
}


def execute_tool(name: str, args: dict[str, Any]) -> Any:
    """Execute a tool by name with arguments."""
    func = TOOL_MAP.get(name)
    if not func:
        raise ValueError(f"Unknown tool '{name}'. Available: {list(TOOL_MAP.keys())}")
    return func(**args)

