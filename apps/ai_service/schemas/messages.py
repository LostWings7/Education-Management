"""
Message and tool schemas for AI service conversations.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum


class RoleEnum(str, Enum):
    USER = 'user'
    ASSISTANT = 'assistant'
    SYSTEM = 'system'
    TOOL = 'tool'


@dataclass
class ChatMessage:
    role: str
    content: str
    tool_call_id: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    structured_payload: Optional[Dict[str, Any]] = None


@dataclass
class ToolDefinition:
    name: str
    description: str
    parameters: Dict[str, Any]
    required_role: Optional[str] = None


@dataclass
class ToolCallRequest:
    tool_call_id: str
    name: str
    arguments: Dict[str, Any]
