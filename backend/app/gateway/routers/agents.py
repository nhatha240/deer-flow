"""CRUD API for custom agents."""

import logging
import re
import shutil

import yaml
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from deerflow.config.agents_config import AgentConfig, list_custom_agents, load_agent_config, load_agent_soul
from deerflow.config.agent_templates import get_agent_template, list_agent_templates
from deerflow.config.paths import get_paths

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["agents"])

AGENT_NAME_PATTERN = re.compile(r"^[A-Za-z0-9-]+$")


class AgentResponse(BaseModel):
    """Response model for a custom agent."""

    name: str = Field(..., description="Agent name (hyphen-case)")
    description: str = Field(default="", description="Agent description")
    model: str | None = Field(default=None, description="Optional model override")
    tool_groups: list[str] | None = Field(default=None, description="Optional tool group whitelist")
    allow_mcp_tools: bool = Field(default=True, description="Whether MCP tools are available to the agent")
    allow_acp_tools: bool = Field(default=True, description="Whether ACP tools are available to the agent")
    allow_subagents: bool = Field(default=True, description="Whether subagent delegation can be enabled for the agent")
    denied_tool_names: list[str] | None = Field(default=None, description="Optional denylist of tool names filtered from the agent")
    template_id: str | None = Field(default=None, description="Optional built-in template id used when the agent was created")
    soul: str | None = Field(default=None, description="SOUL.md content (included on GET /{name})")


class AgentsListResponse(BaseModel):
    """Response model for listing all custom agents."""

    agents: list[AgentResponse]


class AgentTemplateResponse(BaseModel):
    """Response model for a built-in agent template."""

    id: str = Field(..., description="Stable template identifier")
    name: str = Field(..., description="Human-readable template name")
    description: str = Field(..., description="Template summary")


class AgentTemplatesListResponse(BaseModel):
    """Response model for listing built-in agent templates."""

    templates: list[AgentTemplateResponse]


class AgentCreateRequest(BaseModel):
    """Request body for creating a custom agent."""

    name: str = Field(..., description="Agent name (must match ^[A-Za-z0-9-]+$, stored as lowercase)")
    template_id: str | None = Field(default=None, description="Optional built-in template id")
    description: str | None = Field(default=None, description="Agent description")
    model: str | None = Field(default=None, description="Optional model override")
    tool_groups: list[str] | None = Field(default=None, description="Optional tool group whitelist")
    allow_mcp_tools: bool | None = Field(default=None, description="Optional override for MCP tool access")
    allow_acp_tools: bool | None = Field(default=None, description="Optional override for ACP tool access")
    allow_subagents: bool | None = Field(default=None, description="Optional override for subagent delegation")
    denied_tool_names: list[str] | None = Field(default=None, description="Optional denylist of tool names")
    soul: str | None = Field(default=None, description="SOUL.md content — agent personality and behavioral guardrails")


class AgentUpdateRequest(BaseModel):
    """Request body for updating a custom agent."""

    description: str | None = Field(default=None, description="Updated description")
    model: str | None = Field(default=None, description="Updated model override")
    tool_groups: list[str] | None = Field(default=None, description="Updated tool group whitelist")
    allow_mcp_tools: bool | None = Field(default=None, description="Updated MCP tool access policy")
    allow_acp_tools: bool | None = Field(default=None, description="Updated ACP tool access policy")
    allow_subagents: bool | None = Field(default=None, description="Updated subagent access policy")
    denied_tool_names: list[str] | None = Field(default=None, description="Updated denylist of tool names")
    soul: str | None = Field(default=None, description="Updated SOUL.md content")


def _validate_agent_name(name: str) -> None:
    """Validate agent name against allowed pattern.

    Args:
        name: The agent name to validate.

    Raises:
        HTTPException: 422 if the name is invalid.
    """
    if not AGENT_NAME_PATTERN.match(name):
        raise HTTPException(
            status_code=422,
            detail=f"Invalid agent name '{name}'. Must match ^[A-Za-z0-9-]+$ (letters, digits, and hyphens only).",
        )


def _normalize_agent_name(name: str) -> str:
    """Normalize agent name to lowercase for filesystem storage."""
    return name.lower()


def _agent_config_to_response(agent_cfg: AgentConfig, include_soul: bool = False) -> AgentResponse:
    """Convert AgentConfig to AgentResponse."""
    soul: str | None = None
    if include_soul:
        soul = load_agent_soul(agent_cfg.name) or ""

    return AgentResponse(
        name=agent_cfg.name,
        description=agent_cfg.description,
        model=agent_cfg.model,
        tool_groups=agent_cfg.tool_groups,
        allow_mcp_tools=agent_cfg.allow_mcp_tools,
        allow_acp_tools=agent_cfg.allow_acp_tools,
        allow_subagents=agent_cfg.allow_subagents,
        denied_tool_names=agent_cfg.denied_tool_names,
        template_id=agent_cfg.template_id,
        soul=soul,
    )


def _resolve_agent_template(template_id: str | None):
    if not template_id:
        return None

    template = get_agent_template(template_id)
    if template is None:
        raise HTTPException(status_code=422, detail=f"Unknown agent template '{template_id}'")
    return template


def _build_agent_payload(name: str, request: AgentCreateRequest | AgentUpdateRequest, existing: AgentConfig | None = None) -> tuple[dict, str]:
    template = _resolve_agent_template(getattr(request, "template_id", None)) if existing is None else None
    description = request.description if request.description is not None else (existing.description if existing else (template.description if template else ""))
    model = request.model if request.model is not None else (existing.model if existing else template.model if template else None)
    tool_groups = request.tool_groups if request.tool_groups is not None else (existing.tool_groups if existing else template.tool_groups if template else None)
    allow_mcp_tools = request.allow_mcp_tools if request.allow_mcp_tools is not None else (existing.allow_mcp_tools if existing else template.allow_mcp_tools if template else True)
    allow_acp_tools = request.allow_acp_tools if request.allow_acp_tools is not None else (existing.allow_acp_tools if existing else template.allow_acp_tools if template else True)
    allow_subagents = request.allow_subagents if request.allow_subagents is not None else (existing.allow_subagents if existing else template.allow_subagents if template else True)
    denied_tool_names = request.denied_tool_names if request.denied_tool_names is not None else (existing.denied_tool_names if existing else template.denied_tool_names if template else None)
    template_id = existing.template_id if existing else (template.id if template else None)
    soul = request.soul if request.soul is not None else (load_agent_soul(existing.name) if existing else template.soul if template else "")

    config_data: dict = {
        "name": name,
        "description": description,
        "allow_mcp_tools": allow_mcp_tools,
        "allow_acp_tools": allow_acp_tools,
        "allow_subagents": allow_subagents,
    }
    if model is not None:
        config_data["model"] = model
    if tool_groups is not None:
        config_data["tool_groups"] = tool_groups
    if denied_tool_names is not None:
        config_data["denied_tool_names"] = denied_tool_names
    if template_id is not None:
        config_data["template_id"] = template_id

    return config_data, soul


@router.get(
    "/agent-templates",
    response_model=AgentTemplatesListResponse,
    summary="List Built-in Agent Templates",
    description="List first-party templates that can be used to create custom agents quickly.",
)
async def list_templates() -> AgentTemplatesListResponse:
    templates = [
        AgentTemplateResponse(id=template.id, name=template.name, description=template.description)
        for template in list_agent_templates()
    ]
    return AgentTemplatesListResponse(templates=templates)


@router.get(
    "/agents",
    response_model=AgentsListResponse,
    summary="List Custom Agents",
    description="List all custom agents available in the agents directory.",
)
async def list_agents() -> AgentsListResponse:
    """List all custom agents.

    Returns:
        List of all custom agents with their metadata (without soul content).
    """
    try:
        agents = list_custom_agents()
        return AgentsListResponse(agents=[_agent_config_to_response(a) for a in agents])
    except Exception as e:
        logger.error(f"Failed to list agents: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list agents: {str(e)}")


@router.get(
    "/agents/check",
    summary="Check Agent Name",
    description="Validate an agent name and check if it is available (case-insensitive).",
)
async def check_agent_name(name: str) -> dict:
    """Check whether an agent name is valid and not yet taken.

    Args:
        name: The agent name to check.

    Returns:
        ``{"available": true/false, "name": "<normalized>"}``

    Raises:
        HTTPException: 422 if the name is invalid.
    """
    _validate_agent_name(name)
    normalized = _normalize_agent_name(name)
    available = not get_paths().agent_dir(normalized).exists()
    return {"available": available, "name": normalized}


@router.get(
    "/agents/{name}",
    response_model=AgentResponse,
    summary="Get Custom Agent",
    description="Retrieve details and SOUL.md content for a specific custom agent.",
)
async def get_agent(name: str) -> AgentResponse:
    """Get a specific custom agent by name.

    Args:
        name: The agent name.

    Returns:
        Agent details including SOUL.md content.

    Raises:
        HTTPException: 404 if agent not found.
    """
    _validate_agent_name(name)
    name = _normalize_agent_name(name)

    try:
        agent_cfg = load_agent_config(name)
        return _agent_config_to_response(agent_cfg, include_soul=True)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Agent '{name}' not found")
    except Exception as e:
        logger.error(f"Failed to get agent '{name}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get agent: {str(e)}")


@router.post(
    "/agents",
    response_model=AgentResponse,
    status_code=201,
    summary="Create Custom Agent",
    description="Create a new custom agent with its config and SOUL.md.",
)
async def create_agent_endpoint(request: AgentCreateRequest) -> AgentResponse:
    """Create a new custom agent.

    Args:
        request: The agent creation request.

    Returns:
        The created agent details.

    Raises:
        HTTPException: 409 if agent already exists, 422 if name is invalid.
    """
    _validate_agent_name(request.name)
    normalized_name = _normalize_agent_name(request.name)

    agent_dir = get_paths().agent_dir(normalized_name)

    if agent_dir.exists():
        raise HTTPException(status_code=409, detail=f"Agent '{normalized_name}' already exists")

    try:
        agent_dir.mkdir(parents=True, exist_ok=True)

        config_data, soul = _build_agent_payload(normalized_name, request)

        config_file = agent_dir / "config.yaml"
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True)

        # Write SOUL.md
        soul_file = agent_dir / "SOUL.md"
        soul_file.write_text(soul, encoding="utf-8")

        logger.info(f"Created agent '{normalized_name}' at {agent_dir}")

        agent_cfg = load_agent_config(normalized_name)
        return _agent_config_to_response(agent_cfg, include_soul=True)

    except HTTPException:
        raise
    except Exception as e:
        # Clean up on failure
        if agent_dir.exists():
            shutil.rmtree(agent_dir)
        logger.error(f"Failed to create agent '{request.name}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create agent: {str(e)}")


@router.put(
    "/agents/{name}",
    response_model=AgentResponse,
    summary="Update Custom Agent",
    description="Update an existing custom agent's config and/or SOUL.md.",
)
async def update_agent(name: str, request: AgentUpdateRequest) -> AgentResponse:
    """Update an existing custom agent.

    Args:
        name: The agent name.
        request: The update request (all fields optional).

    Returns:
        The updated agent details.

    Raises:
        HTTPException: 404 if agent not found.
    """
    _validate_agent_name(name)
    name = _normalize_agent_name(name)

    try:
        agent_cfg = load_agent_config(name)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Agent '{name}' not found")

    agent_dir = get_paths().agent_dir(name)

    try:
        # Update config if any config fields changed
        config_changed = any(
            v is not None
            for v in [
                request.description,
                request.model,
                request.tool_groups,
                request.allow_mcp_tools,
                request.allow_acp_tools,
                request.allow_subagents,
                request.denied_tool_names,
            ]
        )

        if config_changed:
            updated, _ = _build_agent_payload(name, request, existing=agent_cfg)
            config_file = agent_dir / "config.yaml"
            with open(config_file, "w", encoding="utf-8") as f:
                yaml.dump(updated, f, default_flow_style=False, allow_unicode=True)

        # Update SOUL.md if provided
        if request.soul is not None:
            soul_path = agent_dir / "SOUL.md"
            soul_path.write_text(request.soul, encoding="utf-8")

        logger.info(f"Updated agent '{name}'")

        refreshed_cfg = load_agent_config(name)
        return _agent_config_to_response(refreshed_cfg, include_soul=True)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update agent '{name}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update agent: {str(e)}")


class UserProfileResponse(BaseModel):
    """Response model for the global user profile (USER.md)."""

    content: str | None = Field(default=None, description="USER.md content, or null if not yet created")


class UserProfileUpdateRequest(BaseModel):
    """Request body for setting the global user profile."""

    content: str = Field(default="", description="USER.md content — describes the user's background and preferences")


@router.get(
    "/user-profile",
    response_model=UserProfileResponse,
    summary="Get User Profile",
    description="Read the global USER.md file that is injected into all custom agents.",
)
async def get_user_profile() -> UserProfileResponse:
    """Return the current USER.md content.

    Returns:
        UserProfileResponse with content=None if USER.md does not exist yet.
    """
    try:
        user_md_path = get_paths().user_md_file
        if not user_md_path.exists():
            return UserProfileResponse(content=None)
        raw = user_md_path.read_text(encoding="utf-8").strip()
        return UserProfileResponse(content=raw or None)
    except Exception as e:
        logger.error(f"Failed to read user profile: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to read user profile: {str(e)}")


@router.put(
    "/user-profile",
    response_model=UserProfileResponse,
    summary="Update User Profile",
    description="Write the global USER.md file that is injected into all custom agents.",
)
async def update_user_profile(request: UserProfileUpdateRequest) -> UserProfileResponse:
    """Create or overwrite the global USER.md.

    Args:
        request: The update request with the new USER.md content.

    Returns:
        UserProfileResponse with the saved content.
    """
    try:
        paths = get_paths()
        paths.base_dir.mkdir(parents=True, exist_ok=True)
        paths.user_md_file.write_text(request.content, encoding="utf-8")
        logger.info(f"Updated USER.md at {paths.user_md_file}")
        return UserProfileResponse(content=request.content or None)
    except Exception as e:
        logger.error(f"Failed to update user profile: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update user profile: {str(e)}")


@router.delete(
    "/agents/{name}",
    status_code=204,
    summary="Delete Custom Agent",
    description="Delete a custom agent and all its files (config, SOUL.md, memory).",
)
async def delete_agent(name: str) -> None:
    """Delete a custom agent.

    Args:
        name: The agent name.

    Raises:
        HTTPException: 404 if agent not found.
    """
    _validate_agent_name(name)
    name = _normalize_agent_name(name)

    agent_dir = get_paths().agent_dir(name)

    if not agent_dir.exists():
        raise HTTPException(status_code=404, detail=f"Agent '{name}' not found")

    try:
        shutil.rmtree(agent_dir)
        logger.info(f"Deleted agent '{name}' from {agent_dir}")
    except Exception as e:
        logger.error(f"Failed to delete agent '{name}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete agent: {str(e)}")
