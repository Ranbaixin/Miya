"""PentAGI Agent 系统工具 — Python 原生移植

从 PentAGI (Go) 移植的 33 个 Agent 工具，分为 7 类：
- Environment (3): terminal, file, browser
- Search Network (8): google, duckduckgo, tavily, traversaal, perplexity, searxng, sploitus, search
- Search Vector DB (9): search_in_memory, search_guide, store_guide, search_answer, store_answer, search_code, store_code, graphiti_search, memorist
- Agent Delegation (4): pentester, coder, maintenance, advice
- Agent Result (7): hack_result, code_result, maintenance_result, search_result, memorist_result, enricher_result, report_result
- Task Management (3): subtask_list, subtask_patch, ask
- Barrier (1): done

所有工具为 OpenA兼容 Function Calling 格式，可直接用于 LLM tool-calling。
"""

import json
import logging
import os
import subprocess
import time
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

# ─── Tool Schema Types ──────────────────────────────


class ToolType(Enum):
    NONE = "none"
    ENVIRONMENT = "environment"
    SEARCH_NETWORK = "search_network"
    SEARCH_VECTOR_DB = "search_vector_db"
    AGENT = "agent"
    STORE_AGENT_RESULT = "store_agent_result"
    STORE_VECTOR_DB = "store_vector_db"
    BARRIER = "barrier"


@dataclass
class ToolSchema:
    """OpenAI 兼容的 Function Definition"""

    name: str
    description: str
    parameters: Dict[str, Any]  # JSON Schema
    tool_type: ToolType = ToolType.NONE

    def to_openai(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


# ─── 7. Barrier Tools ───────────────────────────────

TOOL_DONE = ToolSchema(
    name="done",
    description="Finish the current sub-task with success or failure status. Call this when you have completed your work.",
    parameters={
        "type": "object",
        "properties": {
            "success": {"type": "boolean", "description": "Whether the task was completed successfully"},
            "result": {"type": "string", "description": "Summary of what was accomplished or why it failed"},
            "message": {"type": "string", "description": "Additional reasoning or notes about the completion"},
        },
        "required": ["success", "result"],
    },
    tool_type=ToolType.BARRIER,
)

TOOL_ASK = ToolSchema(
    name="ask",
    description="Ask the user for input, clarification, or additional information needed to proceed",
    parameters={
        "type": "object",
        "properties": {
            "message": {"type": "string", "description": "The question or request for input from the user"},
        },
        "required": ["message"],
    },
    tool_type=ToolType.BARRIER,
)


# ─── 1. Environment Tools ───────────────────────────

TOOL_TERMINAL = ToolSchema(
    name="terminal",
    description="Execute a shell command in blocking mode. One command at a time. Timeout: 300 seconds. "
    "Use for: reconnaissance, exploitation, file operations, tool execution.",
    parameters={
        "type": "object",
        "properties": {
            "input": {"type": "string", "description": "The shell command to execute"},
            "cwd": {"type": "string", "description": "Working directory for the command (optional)"},
            "timeout": {"type": "integer", "description": "Custom timeout in seconds (default: 300, max: 1200)"},
            "detach": {"type": "boolean", "description": "Run in detached mode (default: false)"},
            "message": {"type": "string", "description": "Human-readable description of what this command does"},
        },
        "required": ["input"],
    },
    tool_type=ToolType.ENVIRONMENT,
)

TOOL_FILE = ToolSchema(
    name="file",
    description="Read or modify local files. Use to save exploits, scripts, or read scan results.",
    parameters={
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["read_file", "update_file"],
                "description": "read_file: read file content, update_file: write or append to file",
            },
            "path": {"type": "string", "description": "File path"},
            "content": {"type": "string", "description": "Content to write (required for update_file)"},
            "message": {"type": "string", "description": "Description of the file operation"},
        },
        "required": ["action", "path"],
    },
    tool_type=ToolType.ENVIRONMENT,
)

TOOL_BROWSER = ToolSchema(
    name="browser",
    description="Open a web page and retrieve content as markdown, HTML, or extract links",
    parameters={
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "The URL to visit"},
            "action": {
                "type": "string",
                "enum": ["markdown", "html", "links"],
                "description": "How to return content: markdown (cleaned), html (raw), links (extracted URLs only)",
            },
            "message": {"type": "string", "description": "Why are you visiting this page"},
        },
        "required": ["url", "action"],
    },
    tool_type=ToolType.SEARCH_NETWORK,
)


# ─── 2. Search Network Tools ────────────────────────

TOOL_GOOGLE = ToolSchema(
    name="google",
    description="Search Google Custom Search. Fast queries, shortest content. "
    "Use for quick fact-checking or collecting public links by short query. "
    "Requires GOOGLE_API_KEY + GOOGLE_CX env vars.",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query"},
            "max_results": {"type": "integer", "description": "Number of results (1-10, default: 5)"},
            "message": {"type": "string", "description": "Why are you searching for this"},
        },
        "required": ["query"],
    },
    tool_type=ToolType.SEARCH_NETWORK,
)

TOOL_DUCKDUCKGO = ToolSchema(
    name="duckduckgo",
    description="Anonymous search via DuckDuckGo. Small content, different sources. "
    "Use for general web searches without tracking.",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query"},
            "max_results": {"type": "integer", "description": "Number of results (1-10, default: 5)"},
            "message": {"type": "string", "description": "Why are you searching for this"},
        },
        "required": ["query"],
    },
    tool_type=ToolType.SEARCH_NETWORK,
)

TOOL_TAVILY = ToolSchema(
    name="tavily",
    description="AI-powered search via Tavily. Complex queries, detailed content with AI-generated answers. "
    "Requires TAVILY_API_KEY.",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query"},
            "max_results": {"type": "integer", "description": "Number of results (1-10, default: 5)"},
            "message": {"type": "string", "description": "Why are you searching for this"},
        },
        "required": ["query"],
    },
    tool_type=ToolType.SEARCH_NETWORK,
)

TOOL_TRAVERSAAL = ToolSchema(
    name="traversaal",
    description="Semantic search via Traversaal. Returns AI answers with web links. "
    "Useful for research queries needing synthesized answers.",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query"},
            "max_results": {"type": "integer", "description": "Number of results (1-10, default: 5)"},
            "message": {"type": "string", "description": "Why are you searching for this"},
        },
        "required": ["query"],
    },
    tool_type=ToolType.SEARCH_NETWORK,
)

TOOL_PERPLEXITY = ToolSchema(
    name="perplexity",
    description="LLM-augmented research search via Perplexity. Full research reports. Requires PERPLEXITY_API_KEY.",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query"},
            "max_results": {"type": "integer", "description": "Number of results (1-10, default: 5)"},
            "message": {"type": "string", "description": "Why are you searching for this"},
        },
        "required": ["query"],
    },
    tool_type=ToolType.SEARCH_NETWORK,
)

TOOL_SEARXNG = ToolSchema(
    name="searxng",
    description="Privacy-focused meta-search via SearXNG. Aggregates multiple engines. Requires SEARXNG_URL config.",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query"},
            "max_results": {"type": "integer", "description": "Number of results (1-10, default: 5)"},
            "message": {"type": "string", "description": "Why are you searching for this"},
        },
        "required": ["query"],
    },
    tool_type=ToolType.SEARCH_NETWORK,
)

TOOL_SPLOITUS = ToolSchema(
    name="sploitus",
    description="Search the Sploitus exploit aggregator for public exploits, PoCs, and offensive security tools. "
    "Indexes ExploitDB, Packet Storm, GitHub Security Advisories, etc. "
    "Use this to find exploit code for CVEs, software, services, or vulnerability classes.",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search term (e.g. 'ssh', 'apache log4j', 'CVE-2021-44228')"},
            "exploit_type": {
                "type": "string",
                "enum": ["exploit", "tool", "paper"],
                "description": "Type of result to filter by (optional)",
            },
            "sort": {
                "type": "string",
                "enum": ["default", "date"],
                "description": "Sort order: default (relevance) or date (newest first)",
            },
            "max_results": {"type": "integer", "description": "Number of results (1-20, default: 10)"},
            "message": {"type": "string", "description": "Why are you searching"},
        },
        "required": ["query"],
    },
    tool_type=ToolType.SEARCH_NETWORK,
)


# ─── 3. Vector DB Search Tools ──────────────────────

TOOL_SEARCH_IN_MEMORY = ToolSchema(
    name="search_in_memory",
    description="Semantic search in long-term memory (vector DB). Provide 1-5 natural language queries "
    "with context and detail. Use for retrieving past findings, techniques, vulnerabilities.",
    parameters={
        "type": "object",
        "properties": {
            "questions": {
                "type": "array",
                "items": {"type": "string"},
                "description": "1-5 semantically rich natural language queries",
                "minItems": 1,
                "maxItems": 5,
            },
            "task_id": {"type": "integer", "description": "Filter by task ID (optional)"},
            "subtask_id": {"type": "integer", "description": "Filter by subtask ID (optional)"},
            "message": {"type": "string", "description": "Why you need this information"},
        },
        "required": ["questions"],
    },
    tool_type=ToolType.SEARCH_VECTOR_DB,
)

TOOL_SEARCH_GUIDE = ToolSchema(
    name="search_guide",
    description="Search stored guides/methodologies by semantic query. Use for reusable techniques.",
    parameters={
        "type": "object",
        "properties": {
            "questions": {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 5},
            "type": {
                "type": "string",
                "enum": ["install", "configure", "use", "pentest", "development", "other"],
                "description": "Guide category",
            },
            "message": {"type": "string"},
        },
        "required": ["questions", "type"],
    },
    tool_type=ToolType.SEARCH_VECTOR_DB,
)

TOOL_STORE_GUIDE = ToolSchema(
    name="store_guide",
    description="Store an anonymized guide/methodology for future reuse. "
    "Anonymize: IPs→{target_ip}, domains→{target_domain}, credentials→{username}/{password}",
    parameters={
        "type": "object",
        "properties": {
            "guide": {"type": "string", "description": "The guide content (anonymized)"},
            "question": {"type": "string", "description": "What question does this guide answer"},
            "type": {
                "type": "string",
                "enum": ["install", "configure", "use", "pentest", "development", "other"],
            },
            "message": {"type": "string"},
        },
        "required": ["guide", "question", "type"],
    },
    tool_type=ToolType.STORE_VECTOR_DB,
)

TOOL_SEARCH_ANSWER = ToolSchema(
    name="search_answer",
    description="Search stored answers by semantic query. Use for previously solved problems.",
    parameters={
        "type": "object",
        "properties": {
            "questions": {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 5},
            "type": {
                "type": "string",
                "enum": ["guide", "vulnerability", "code", "tool", "other"],
                "description": "Answer category",
            },
            "message": {"type": "string"},
        },
        "required": ["questions", "type"],
    },
    tool_type=ToolType.SEARCH_VECTOR_DB,
)

TOOL_STORE_ANSWER = ToolSchema(
    name="store_answer",
    description="Store an anonymized answer for future reference",
    parameters={
        "type": "object",
        "properties": {
            "answer": {"type": "string", "description": "The answer content (anonymized)"},
            "question": {"type": "string", "description": "The original question"},
            "type": {"type": "string", "enum": ["guide", "vulnerability", "code", "tool", "other"]},
            "message": {"type": "string"},
        },
        "required": ["answer", "question", "type"],
    },
    tool_type=ToolType.STORE_VECTOR_DB,
)

TOOL_SEARCH_CODE = ToolSchema(
    name="search_code",
    description="Search stored code samples by semantic query and language",
    parameters={
        "type": "object",
        "properties": {
            "questions": {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 5},
            "lang": {"type": "string", "description": "Programming language (e.g. python, go, bash)"},
            "message": {"type": "string"},
        },
        "required": ["questions"],
    },
    tool_type=ToolType.SEARCH_VECTOR_DB,
)

TOOL_STORE_CODE = ToolSchema(
    name="store_code",
    description="Store a code sample for future reference. Include explanation and description.",
    parameters={
        "type": "object",
        "properties": {
            "code": {"type": "string", "description": "The code content"},
            "question": {"type": "string", "description": "What problem does this code solve"},
            "lang": {"type": "string", "description": "Programming language"},
            "explanation": {"type": "string", "description": "How the code works"},
            "description": {"type": "string", "description": "What the code does"},
            "message": {"type": "string"},
        },
        "required": ["code", "question", "lang"],
    },
    tool_type=ToolType.STORE_VECTOR_DB,
)

TOOL_GRAPHITI_SEARCH = ToolSchema(
    name="graphiti_search",
    description="Search the temporal knowledge graph for historical penetration testing context. "
    "7 search types: temporal_window, entity_relationships, diverse_results, episode_context, "
    "successful_tools, recent_context, entity_by_label.",
    parameters={
        "type": "object",
        "properties": {
            "search_type": {
                "type": "string",
                "enum": [
                    "temporal_window",
                    "entity_relationships",
                    "diverse_results",
                    "episode_context",
                    "successful_tools",
                    "recent_context",
                    "entity_by_label",
                ],
            },
            "query": {"type": "string", "description": "Search query or description"},
            "max_results": {"type": "integer", "description": "Max results (default: 5)"},
            "time_start": {"type": "string", "description": "ISO datetime for time-bounded search start"},
            "time_end": {"type": "string", "description": "ISO datetime for time-bounded search end"},
            "center_node_uuid": {"type": "string", "description": "Entity UUID for relationship exploration"},
            "max_depth": {"type": "integer", "description": "Max graph traversal depth (default: 2)"},
            "node_labels": {"type": "array", "items": {"type": "string"}, "description": "Filter by node types"},
            "edge_types": {"type": "array", "items": {"type": "string"}, "description": "Filter by relationship types"},
            "diversity_level": {"type": "string", "enum": ["low", "medium", "high"]},
            "recency_window": {"type": "string", "description": "Time window (e.g. 6h, 24h, 7d)"},
            "min_mentions": {"type": "integer", "description": "Minimum mentions for successful_tools search"},
            "message": {"type": "string"},
        },
        "required": ["search_type", "query"],
    },
    tool_type=ToolType.SEARCH_VECTOR_DB,
)


# ─── 4. Agent Delegation Tools ──────────────────────

TOOL_SEARCH = ToolSchema(
    name="search",
    description="Delegate to Researcher team for complex multi-engine search. "
    "Researcher uses all search engines and long-term memory to find comprehensive information.",
    parameters={
        "type": "object",
        "properties": {
            "question": {
                "type": "string",
                "description": "Detailed question in English with format/structure requirements",
            },
            "message": {"type": "string", "description": "Additional context for the researcher"},
        },
        "required": ["question"],
    },
    tool_type=ToolType.AGENT,
)

TOOL_PENTESTER = ToolSchema(
    name="pentester",
    description="Delegate to Pentester team for penetration testing, vulnerability discovery, and exploitation",
    parameters={
        "type": "object",
        "properties": {
            "question": {"type": "string", "description": "Detailed task in English"},
            "message": {"type": "string", "description": "Additional context"},
        },
        "required": ["question"],
    },
    tool_type=ToolType.AGENT,
)

TOOL_CODER = ToolSchema(
    name="coder",
    description="Delegate to Developer team for code writing, exploit customization, automation scripts",
    parameters={
        "type": "object",
        "properties": {
            "question": {"type": "string", "description": "Detailed coding task in English"},
            "message": {"type": "string", "description": "Additional context"},
        },
        "required": ["question"],
    },
    tool_type=ToolType.AGENT,
)

TOOL_MAINTENANCE = ToolSchema(
    name="maintenance",
    description="Delegate to DevOps team for environment setup, tool installation, system administration",
    parameters={
        "type": "object",
        "properties": {
            "question": {"type": "string", "description": "Detailed maintenance task in English"},
            "message": {"type": "string", "description": "Additional context"},
        },
        "required": ["question"],
    },
    tool_type=ToolType.AGENT,
)

TOOL_ADVICE = ToolSchema(
    name="advice",
    description="Get expert advice from the Mentor. Use when stuck or needing strategic guidance.",
    parameters={
        "type": "object",
        "properties": {
            "question": {"type": "string", "description": "Detailed question"},
            "code": {"type": "string", "description": "Optional code snippet for context"},
            "output": {"type": "string", "description": "Optional command output for context"},
            "message": {"type": "string", "description": "Additional context"},
        },
        "required": ["question"],
    },
    tool_type=ToolType.AGENT,
)

TOOL_MEMORIST = ToolSchema(
    name="memorist",
    description="Query the Archivist team for historical information about past tasks, solutions, and context",
    parameters={
        "type": "object",
        "properties": {
            "question": {"type": "string", "description": "Question about past tasks/methods"},
            "task_id": {"type": "integer", "description": "Optional task filter"},
            "subtask_id": {"type": "integer", "description": "Optional subtask filter"},
            "message": {"type": "string", "description": "Additional context"},
        },
        "required": ["question"],
    },
    tool_type=ToolType.AGENT,
)


# ─── 5. Agent Result Tools ──────────────────────────

TOOL_SEARCH_RESULT = ToolSchema(
    name="search_result",
    description="Submit complex search results as answer to the user's question",
    parameters={
        "type": "object",
        "properties": {
            "result": {"type": "string", "description": "The search result/finding"},
            "message": {"type": "string", "description": "Summary of what was found"},
        },
        "required": ["result"],
    },
    tool_type=ToolType.STORE_AGENT_RESULT,
)

TOOL_HACK_RESULT = ToolSchema(
    name="hack_result",
    description="Submit penetration testing results with detailed findings",
    parameters={
        "type": "object",
        "properties": {
            "result": {"type": "string", "description": "Detailed penetration test findings"},
            "message": {"type": "string", "description": "Summary of findings"},
        },
        "required": ["result"],
    },
    tool_type=ToolType.STORE_AGENT_RESULT,
)

TOOL_CODE_RESULT = ToolSchema(
    name="code_result",
    description="Submit code development results with execution status",
    parameters={
        "type": "object",
        "properties": {
            "result": {"type": "string", "description": "The code or development result"},
            "message": {"type": "string", "description": "What was accomplished"},
        },
        "required": ["result"],
    },
    tool_type=ToolType.STORE_AGENT_RESULT,
)

TOOL_MAINTENANCE_RESULT = ToolSchema(
    name="maintenance_result",
    description="Submit environment maintenance results",
    parameters={
        "type": "object",
        "properties": {
            "success": {"type": "boolean", "description": "Whether maintenance succeeded"},
            "result": {"type": "string", "description": "Detailed report of maintenance work"},
            "message": {"type": "string", "description": "Summary"},
        },
        "required": ["success", "result"],
    },
    tool_type=ToolType.STORE_AGENT_RESULT,
)

TOOL_MEMORIST_RESULT = ToolSchema(
    name="memorist_result",
    description="Submit long-term memory search results",
    parameters={
        "type": "object",
        "properties": {
            "result": {"type": "string", "description": "Memory search findings"},
            "message": {"type": "string", "description": "Summary of recalled information"},
        },
        "required": ["result"],
    },
    tool_type=ToolType.STORE_AGENT_RESULT,
)

TOOL_ENRICHER_RESULT = ToolSchema(
    name="enricher_result",
    description="Submit enriched question with additional context from various sources",
    parameters={
        "type": "object",
        "properties": {
            "result": {"type": "string", "description": "Enriched question with context"},
            "message": {"type": "string", "description": "What was added and why"},
        },
        "required": ["result"],
    },
    tool_type=ToolType.STORE_AGENT_RESULT,
)

TOOL_REPORT_RESULT = ToolSchema(
    name="report_result",
    description="Submit the final task report with execution status and detailed description",
    parameters={
        "type": "object",
        "properties": {
            "success": {"type": "boolean", "description": "Overall task success status"},
            "result": {"type": "string", "description": "Complete task report with findings and action items"},
            "message": {"type": "string", "description": "Executive summary"},
        },
        "required": ["success", "result"],
    },
    tool_type=ToolType.STORE_AGENT_RESULT,
)


# ─── 6. Task Management Tools ───────────────────────

TOOL_SUBTASK_LIST = ToolSchema(
    name="subtask_list",
    description="Submit a new generated subtask list. Each subtask has title and description.",
    parameters={
        "type": "object",
        "properties": {
            "subtasks": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "Short subtask title"},
                        "description": {"type": "string", "description": "Detailed description of what to do"},
                    },
                    "required": ["title", "description"],
                },
                "description": "Ordered list of subtasks to execute",
                "minItems": 1,
            },
            "message": {"type": "string", "description": "Reasoning about task breakdown"},
        },
        "required": ["subtasks"],
    },
    tool_type=ToolType.STORE_AGENT_RESULT,
)

TOOL_SUBTASK_PATCH = ToolSchema(
    name="subtask_patch",
    description="Submit delta operations to modify the current subtask list. "
    "Supports add (create new subtask), remove (delete by ID), "
    "modify (update title/description), and reorder (move to position).",
    parameters={
        "type": "object",
        "properties": {
            "operations": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "op": {
                            "type": "string",
                            "enum": ["add", "remove", "modify", "reorder"],
                            "description": "Operation type",
                        },
                        "id": {"type": "string", "description": "Subtask ID to remove/modify/reorder"},
                        "title": {"type": "string", "description": "New title (for add/modify)"},
                        "description": {"type": "string", "description": "New description (for add/modify)"},
                        "position": {"type": "integer", "description": "Target position (for add/reorder)"},
                    },
                    "required": ["op"],
                },
                "description": "List of operations to apply",
            },
            "message": {"type": "string", "description": "Reasoning about the changes"},
        },
        "required": ["operations"],
    },
    tool_type=ToolType.STORE_AGENT_RESULT,
)


# ─── 7. Tool Registry ───────────────────────────────

ALL_TOOLS: Dict[str, ToolSchema] = {}

# Register all tools
for _tool in [
    # Barrier
    TOOL_DONE,
    TOOL_ASK,
    # Environment
    TOOL_TERMINAL,
    TOOL_FILE,
    TOOL_BROWSER,
    # Search Network
    TOOL_GOOGLE,
    TOOL_DUCKDUCKGO,
    TOOL_TAVILY,
    TOOL_TRAVERSAAL,
    TOOL_PERPLEXITY,
    TOOL_SEARXNG,
    TOOL_SPLOITUS,
    # Search Vector DB
    TOOL_SEARCH_IN_MEMORY,
    TOOL_SEARCH_GUIDE,
    TOOL_STORE_GUIDE,
    TOOL_SEARCH_ANSWER,
    TOOL_STORE_ANSWER,
    TOOL_SEARCH_CODE,
    TOOL_STORE_CODE,
    TOOL_GRAPHITI_SEARCH,
    # Agent Delegation
    TOOL_SEARCH,
    TOOL_PENTESTER,
    TOOL_CODER,
    TOOL_MAINTENANCE,
    TOOL_ADVICE,
    TOOL_MEMORIST,
    # Agent Result
    TOOL_SEARCH_RESULT,
    TOOL_HACK_RESULT,
    TOOL_CODE_RESULT,
    TOOL_MAINTENANCE_RESULT,
    TOOL_MEMORIST_RESULT,
    TOOL_ENRICHER_RESULT,
    TOOL_REPORT_RESULT,
    # Task Management
    TOOL_SUBTASK_LIST,
    TOOL_SUBTASK_PATCH,
]:
    ALL_TOOLS[_tool.name] = _tool


def get_all_tools() -> Dict[str, ToolSchema]:
    """Get all registered agent tools"""
    return ALL_TOOLS


def get_tool_definitions() -> List[Dict[str, Any]]:
    """Get all tools as OpenAI function definitions"""
    return [t.to_openai() for t in ALL_TOOLS.values()]


def get_tools_by_type(tool_type: ToolType) -> List[ToolSchema]:
    """Get tools filtered by type"""
    return [t for t in ALL_TOOLS.values() if t.tool_type == tool_type]


# Tool type mapping (compatible with PentAGI)
TOOL_TYPE_MAP: Dict[str, ToolType] = {name: tool.tool_type for name, tool in ALL_TOOLS.items()}

# Tools that support result summarizing
SUMMARIZABLE_TOOLS = {"terminal", "browser"}

# Tools whose results can be stored in memory
STORABLE_TOOLS = {
    "terminal",
    "file",
    "search",
    "google",
    "duckduckgo",
    "tavily",
    "traversaal",
    "perplexity",
    "searxng",
    "sploitus",
    "maintenance",
    "coder",
    "pentester",
    "advice",
}
