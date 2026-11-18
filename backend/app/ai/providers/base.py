"""
Base LLM Provider Interface
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class BaseLLMProvider(ABC):

    @abstractmethod
    async def generate_investigation(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generates structured hypotheses, recommendations, and missing evidence.
        """
        pass

    @abstractmethod
    async def answer_copilot_query(self, query: str, mode: str, incident_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Answers technical SRE questions in LEARNING or ENGINEERING mode.
        """
        pass

    @abstractmethod
    async def draft_postmortem(self, incident_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generates structured draft postmortem.
        """
        pass
