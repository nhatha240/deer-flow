"""CRUD API for idea workspaces."""

from __future__ import annotations

import hashlib
import json
import logging
import shutil
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from uuid import uuid4

import yaml
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from deerflow.config.agent_templates import get_agent_template
from deerflow.config.app_config import get_app_config
from deerflow.config.paths import Paths, get_paths

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/ideas", tags=["ideas"])


class MountedProjectResponse(BaseModel):
    """A mounted project that can be attached to an idea."""

    id: str
    name: str
    host_path: str
    container_path: str
    mount_host_path: str
    mount_container_path: str
    read_only: bool = False


class MountedProjectsListResponse(BaseModel):
    """Response model for mounted project discovery."""

    projects: list[MountedProjectResponse]


class IdeaAgentSettingsRequest(BaseModel):
    """User-configurable planner/worker settings."""

    model_name: str | None = Field(default=None, description="Optional model override")
    system_prompt: str = Field(default="", description="Additional system prompt for this idea agent")


class IdeaAgentSettingsResponse(IdeaAgentSettingsRequest):
    """Resolved planner/worker settings for an idea."""

    agent_name: str = Field(..., description="Backing DeerFlow custom agent name")


class IdeaResponse(BaseModel):
    """Response model for an idea."""

    id: str
    name: str
    description: str = ""
    projects: list[MountedProjectResponse]
    planner: IdeaAgentSettingsResponse
    worker: IdeaAgentSettingsResponse
    thread_ids: list[str] = Field(default_factory=list)
    created_at: str
    updated_at: str


class IdeasListResponse(BaseModel):
    """Response model for listing ideas."""

    ideas: list[IdeaResponse]


class IdeaCreateRequest(BaseModel):
    """Request body for creating an idea."""

    name: str = Field(..., description="Idea name")
    description: str | None = Field(default=None, description="Optional description")
    project_ids: list[str] = Field(default_factory=list, min_length=1, description="Mounted project ids to attach to the idea")
    planner: IdeaAgentSettingsRequest = Field(default_factory=IdeaAgentSettingsRequest)
    worker: IdeaAgentSettingsRequest = Field(default_factory=IdeaAgentSettingsRequest)


class IdeaUpdateRequest(BaseModel):
    """Request body for updating an idea."""

    name: str = Field(..., description="Updated idea name")
    description: str | None = Field(default=None, description="Updated description")
    project_ids: list[str] = Field(default_factory=list, min_length=1, description="Updated mounted project ids")
    planner: IdeaAgentSettingsRequest = Field(default_factory=IdeaAgentSettingsRequest)
    worker: IdeaAgentSettingsRequest = Field(default_factory=IdeaAgentSettingsRequest)


class IdeaThreadAttachResponse(BaseModel):
    """Response model for attaching a thread to an idea."""

    success: bool
    thread_id: str
    idea_id: str


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _project_digest(host_path: str, container_path: str) -> str:
    payload = f"{host_path}::{container_path}"
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:16]


def _planner_agent_name(idea_id: str) -> str:
    return f"idea-{idea_id}-planner"


def _worker_agent_name(idea_id: str) -> str:
    return f"idea-{idea_id}-worker"


def _scan_mount_projects() -> list[MountedProjectResponse]:
    config = get_app_config()
    projects: list[MountedProjectResponse] = []

    for mount in config.sandbox.mounts:
        host_root = Path(mount.host_path).expanduser()
        if not host_root.exists() or not host_root.is_dir():
            continue

        mount_container = PurePosixPath(mount.container_path)
        try:
            children = sorted(
                [child for child in host_root.iterdir() if child.is_dir() and not child.name.startswith(".")],
                key=lambda item: item.name.lower(),
            )
        except OSError:
            logger.exception("Failed to scan mounted projects under %s", host_root)
            continue

        if not children:
            project_container = str(mount_container)
            projects.append(
                MountedProjectResponse(
                    id=_project_digest(str(host_root.resolve()), project_container),
                    name=host_root.name,
                    host_path=str(host_root.resolve()),
                    container_path=project_container,
                    mount_host_path=str(host_root.resolve()),
                    mount_container_path=str(mount_container),
                    read_only=mount.read_only,
                )
            )
            continue

        for child in children:
            resolved_child = child.resolve()
            project_container = str(mount_container / child.name)
            projects.append(
                MountedProjectResponse(
                    id=_project_digest(str(resolved_child), project_container),
                    name=child.name,
                    host_path=str(resolved_child),
                    container_path=project_container,
                    mount_host_path=str(host_root.resolve()),
                    mount_container_path=str(mount_container),
                    read_only=mount.read_only,
                )
            )

    return sorted(projects, key=lambda item: item.name.lower())


def _resolve_projects(project_ids: list[str]) -> list[MountedProjectResponse]:
    available = {project.id: project for project in _scan_mount_projects()}
    resolved: list[MountedProjectResponse] = []
    missing: list[str] = []

    for project_id in project_ids:
        project = available.get(project_id)
        if project is None:
            missing.append(project_id)
            continue
        resolved.append(project)

    if missing:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown mounted project ids: {', '.join(missing)}",
        )

    return resolved


def _idea_payload(
    *,
    idea_id: str,
    name: str,
    description: str,
    projects: list[MountedProjectResponse],
    planner: IdeaAgentSettingsRequest,
    worker: IdeaAgentSettingsRequest,
    existing_thread_ids: list[str] | None = None,
    created_at: str | None = None,
) -> dict:
    return {
        "id": idea_id,
        "name": name,
        "description": description,
        "projects": [project.model_dump() for project in projects],
        "planner": {
            "agent_name": _planner_agent_name(idea_id),
            "model_name": planner.model_name,
            "system_prompt": planner.system_prompt,
        },
        "worker": {
            "agent_name": _worker_agent_name(idea_id),
            "model_name": worker.model_name,
            "system_prompt": worker.system_prompt,
        },
        "thread_ids": existing_thread_ids or [],
        "created_at": created_at or _utc_now_iso(),
        "updated_at": _utc_now_iso(),
    }


def _load_idea(idea_id: str, paths: Paths | None = None) -> IdeaResponse:
    path_manager = paths or get_paths()
    idea_file = path_manager.idea_file(idea_id)
    if not idea_file.exists():
        raise FileNotFoundError(idea_id)

    with open(idea_file, encoding="utf-8") as f:
        raw = json.load(f)

    return IdeaResponse.model_validate(raw)


def _save_idea(payload: dict, paths: Paths | None = None) -> IdeaResponse:
    path_manager = paths or get_paths()
    idea_file = path_manager.idea_file(payload["id"])
    idea_file.parent.mkdir(parents=True, exist_ok=True)
    with open(idea_file, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return IdeaResponse.model_validate(payload)


def _list_ideas(paths: Paths | None = None) -> list[IdeaResponse]:
    path_manager = paths or get_paths()
    if not path_manager.ideas_dir.exists():
        return []

    ideas: list[IdeaResponse] = []
    for idea_file in sorted(path_manager.ideas_dir.glob("*.json")):
        try:
            with open(idea_file, encoding="utf-8") as f:
                raw = json.load(f)
            ideas.append(IdeaResponse.model_validate(raw))
        except Exception:
            logger.exception("Failed to load idea metadata from %s", idea_file)

    return sorted(ideas, key=lambda item: item.updated_at, reverse=True)


def _delete_custom_agent(name: str, paths: Paths | None = None) -> None:
    path_manager = paths or get_paths()
    agent_dir = path_manager.agent_dir(name)
    if agent_dir.exists():
        shutil.rmtree(agent_dir)


def _write_custom_agent(
    *,
    name: str,
    description: str,
    model: str | None,
    soul: str,
    tool_groups: list[str] | None = None,
    allow_mcp_tools: bool = True,
    allow_acp_tools: bool = True,
    allow_subagents: bool = True,
    denied_tool_names: list[str] | None = None,
    template_id: str | None = None,
    paths: Paths | None = None,
) -> None:
    path_manager = paths or get_paths()
    agent_dir = path_manager.agent_dir(name)
    agent_dir.mkdir(parents=True, exist_ok=True)

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

    with open(agent_dir / "config.yaml", "w", encoding="utf-8") as f:
        yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True)

    (agent_dir / "SOUL.md").write_text(soul.strip() + "\n", encoding="utf-8")


def _format_project_context(projects: list[MountedProjectResponse]) -> str:
    return "\n".join(
        f"- {project.name}: host `{project.host_path}`, sandbox `{project.container_path}`"
        for project in projects
    )


def _build_planner_soul(projects: list[MountedProjectResponse], system_prompt: str) -> str:
    template = get_agent_template("codex-orchestrator")
    base_prompt = template.soul if template is not None else ""
    project_context = _format_project_context(projects)
    extra_prompt = system_prompt.strip()

    parts = [
        base_prompt.strip(),
        "# Idea Context",
        "You are planning for a DeerFlow idea workspace with these mounted projects:",
        project_context,
        "Always ground prompts in these exact repositories and paths.",
    ]
    if extra_prompt:
        parts.extend(["# Additional Planner Instructions", extra_prompt])
    return "\n\n".join(part for part in parts if part)


def _build_worker_soul(projects: list[MountedProjectResponse], system_prompt: str) -> str:
    project_context = _format_project_context(projects)
    extra_prompt = system_prompt.strip()
    parts = [
        "You are the implementation worker for a DeerFlow idea workspace.",
        "Operate only within the mounted projects relevant to the task, keep changes scoped, and make cross-repo dependencies explicit.",
        "# Mounted Projects",
        project_context,
    ]
    if extra_prompt:
        parts.extend(["# Additional Worker Instructions", extra_prompt])
    return "\n\n".join(parts)


def _sync_idea_agents(idea: IdeaResponse, paths: Paths | None = None) -> None:
    planner_name = idea.planner.agent_name
    worker_name = idea.worker.agent_name

    _write_custom_agent(
        name=planner_name,
        description=f'Planner agent for idea "{idea.name}"',
        model=idea.planner.model_name,
        soul=_build_planner_soul(idea.projects, idea.planner.system_prompt),
        tool_groups=["file:read", "web"],
        allow_mcp_tools=False,
        allow_acp_tools=False,
        allow_subagents=False,
        denied_tool_names=["tool_search"],
        template_id="codex-orchestrator",
        paths=paths,
    )

    _write_custom_agent(
        name=worker_name,
        description=f'Worker agent for idea "{idea.name}"',
        model=idea.worker.model_name,
        soul=_build_worker_soul(idea.projects, idea.worker.system_prompt),
        tool_groups=["file:read", "file:write", "bash"],
        allow_mcp_tools=False,
        allow_acp_tools=False,
        allow_subagents=False,
        paths=paths,
    )


def remove_thread_from_ideas(thread_id: str, paths: Paths | None = None) -> None:
    """Detach a thread id from every idea metadata file."""
    path_manager = paths or get_paths()
    for idea in _list_ideas(path_manager):
        if thread_id not in idea.thread_ids:
            continue
        payload = idea.model_dump()
        payload["thread_ids"] = [candidate for candidate in idea.thread_ids if candidate != thread_id]
        payload["updated_at"] = _utc_now_iso()
        _save_idea(payload, path_manager)


@router.get(
    "/mounted-projects",
    response_model=MountedProjectsListResponse,
    summary="List Mounted Projects",
    description="Discover mounted repositories from sandbox configuration so they can be attached to ideas.",
)
async def list_mounted_projects() -> MountedProjectsListResponse:
    return MountedProjectsListResponse(projects=_scan_mount_projects())


@router.get(
    "",
    response_model=IdeasListResponse,
    summary="List Ideas",
    description="List all idea workspaces.",
)
async def list_ideas() -> IdeasListResponse:
    return IdeasListResponse(ideas=_list_ideas())


@router.post(
    "",
    response_model=IdeaResponse,
    status_code=201,
    summary="Create Idea",
    description="Create a new idea workspace and sync its planner/worker agents.",
)
async def create_idea(request: IdeaCreateRequest) -> IdeaResponse:
    idea_id = uuid4().hex
    projects = _resolve_projects(request.project_ids)
    payload = _idea_payload(
        idea_id=idea_id,
        name=request.name.strip(),
        description=(request.description or "").strip(),
        projects=projects,
        planner=request.planner,
        worker=request.worker,
    )

    try:
        idea = _save_idea(payload)
        _sync_idea_agents(idea)
        logger.info("Created idea '%s' (%s)", idea.name, idea.id)
        return idea
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to create idea '%s'", request.name)
        try:
            get_paths().idea_file(idea_id).unlink(missing_ok=True)
            _delete_custom_agent(_planner_agent_name(idea_id))
            _delete_custom_agent(_worker_agent_name(idea_id))
        except Exception:
            logger.exception("Failed to roll back idea creation for %s", idea_id)
        raise HTTPException(status_code=500, detail=f"Failed to create idea: {exc}") from exc


@router.get(
    "/{idea_id}",
    response_model=IdeaResponse,
    summary="Get Idea",
    description="Retrieve a single idea workspace.",
)
async def get_idea(idea_id: str) -> IdeaResponse:
    try:
        return _load_idea(idea_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Idea '{idea_id}' not found")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Failed to load idea '%s'", idea_id)
        raise HTTPException(status_code=500, detail=f"Failed to load idea: {exc}") from exc


@router.put(
    "/{idea_id}",
    response_model=IdeaResponse,
    summary="Update Idea",
    description="Update idea metadata and resync planner/worker agents.",
)
async def update_idea(idea_id: str, request: IdeaUpdateRequest) -> IdeaResponse:
    try:
        existing = _load_idea(idea_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Idea '{idea_id}' not found")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    projects = _resolve_projects(request.project_ids)
    payload = _idea_payload(
        idea_id=idea_id,
        name=request.name.strip(),
        description=(request.description or "").strip(),
        projects=projects,
        planner=request.planner,
        worker=request.worker,
        existing_thread_ids=existing.thread_ids,
        created_at=existing.created_at,
    )

    try:
        idea = _save_idea(payload)
        _sync_idea_agents(idea)
        logger.info("Updated idea '%s' (%s)", idea.name, idea.id)
        return idea
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to update idea '%s'", idea_id)
        raise HTTPException(status_code=500, detail=f"Failed to update idea: {exc}") from exc


@router.post(
    "/{idea_id}/threads/{thread_id}",
    response_model=IdeaThreadAttachResponse,
    summary="Attach Thread To Idea",
    description="Associate an existing thread id with an idea workspace.",
)
async def attach_thread_to_idea(idea_id: str, thread_id: str) -> IdeaThreadAttachResponse:
    try:
        idea = _load_idea(idea_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Idea '{idea_id}' not found")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if thread_id in idea.thread_ids:
        return IdeaThreadAttachResponse(success=True, thread_id=thread_id, idea_id=idea_id)

    payload = idea.model_dump()
    payload["thread_ids"] = [*idea.thread_ids, thread_id]
    payload["updated_at"] = _utc_now_iso()

    try:
        _save_idea(payload)
        logger.info("Attached thread '%s' to idea '%s'", thread_id, idea_id)
        return IdeaThreadAttachResponse(success=True, thread_id=thread_id, idea_id=idea_id)
    except Exception as exc:
        logger.exception("Failed to attach thread '%s' to idea '%s'", thread_id, idea_id)
        raise HTTPException(status_code=500, detail=f"Failed to attach thread to idea: {exc}") from exc


@router.delete(
    "/{idea_id}",
    status_code=204,
    summary="Delete Idea",
    description="Delete an idea workspace and its backing planner/worker agents.",
)
async def delete_idea(idea_id: str) -> None:
    path_manager = get_paths()
    try:
        idea = _load_idea(idea_id, path_manager)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Idea '{idea_id}' not found")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    try:
        path_manager.idea_file(idea_id).unlink(missing_ok=True)
        _delete_custom_agent(idea.planner.agent_name, path_manager)
        _delete_custom_agent(idea.worker.agent_name, path_manager)
        logger.info("Deleted idea '%s' (%s)", idea.name, idea.id)
    except Exception as exc:
        logger.exception("Failed to delete idea '%s'", idea_id)
        raise HTTPException(status_code=500, detail=f"Failed to delete idea: {exc}") from exc
