"""
Academic Helpdesk Multi-Agent System Package.
"""

from src.agents.base_agent import BaseAgent
from src.agents.email_agent import EmailAgent
from src.agents.orchestrator import AcademicHelpdeskOrchestrator
from src.agents.policy_agent import PolicyAgent
from src.agents.schedule_agent import ScheduleAgent

__all__ = [
    "BaseAgent",
    "AcademicHelpdeskOrchestrator",
    "PolicyAgent",
    "ScheduleAgent",
    "EmailAgent",
]

