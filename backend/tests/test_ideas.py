from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.gateway.routers import ideas, threads
from deerflow.config.paths import Paths
from deerflow.config.sandbox_config import VolumeMountConfig


def _make_app() -> FastAPI:
    app = FastAPI()
    app.include_router(ideas.router)
    app.include_router(threads.router)
    return app


def _mock_config(mount_root: Path):
    return SimpleNamespace(
        sandbox=SimpleNamespace(
            mounts=[
                VolumeMountConfig(
                    host_path=str(mount_root),
                    container_path="/workspace/user-data/nextjs",
                    read_only=False,
                )
            ]
        )
    )


def test_paths_include_ideas_dir_and_file(tmp_path):
    paths = Paths(tmp_path)

    assert paths.ideas_dir == tmp_path / "ideas"
    assert paths.idea_file("spotlight-platform") == tmp_path / "ideas" / "spotlight-platform.json"


def test_list_mounted_projects_scans_directories(tmp_path):
    mount_root = tmp_path / "mounted"
    (mount_root / "spotlight-web").mkdir(parents=True)
    (mount_root / "spotlight-web" / ".git").mkdir(parents=True)
    (mount_root / "spotlight-api").mkdir(parents=True)
    (mount_root / "spotlight-api" / "pyproject.toml").write_text("", encoding="utf-8")

    app = _make_app()
    paths = Paths(tmp_path)

    with (
        patch("app.gateway.routers.ideas.get_paths", return_value=paths),
        patch("app.gateway.routers.ideas.get_app_config", return_value=_mock_config(mount_root)),
    ):
        with TestClient(app) as client:
            response = client.get("/api/ideas/mounted-projects")

    assert response.status_code == 200
    projects = response.json()["projects"]
    assert [project["name"] for project in projects] == ["spotlight-api", "spotlight-web"]
    assert projects[0]["container_path"].endswith("/spotlight-api")


def test_list_mounted_projects_returns_mount_root_when_mount_is_repo(tmp_path):
    mount_root = tmp_path / "agent_spolight"
    mount_root.mkdir(parents=True)
    (mount_root / ".git").mkdir()
    (mount_root / "src").mkdir()
    (mount_root / "tests").mkdir()

    app = _make_app()
    paths = Paths(tmp_path)

    with (
        patch("app.gateway.routers.ideas.get_paths", return_value=paths),
        patch("app.gateway.routers.ideas.get_app_config", return_value=_mock_config(mount_root)),
    ):
        with TestClient(app) as client:
            response = client.get("/api/ideas/mounted-projects")

    assert response.status_code == 200
    projects = response.json()["projects"]
    assert len(projects) == 1
    assert projects[0]["name"] == "agent_spolight"
    assert projects[0]["container_path"] == "/workspace/user-data/nextjs"


def test_list_mounted_projects_falls_back_to_mount_root_when_host_path_unavailable(tmp_path):
    missing_mount = tmp_path / "missing-host-path"

    app = _make_app()
    paths = Paths(tmp_path)

    with (
        patch("app.gateway.routers.ideas.get_paths", return_value=paths),
        patch("app.gateway.routers.ideas.get_app_config", return_value=_mock_config(missing_mount)),
    ):
        with TestClient(app) as client:
            response = client.get("/api/ideas/mounted-projects")

    assert response.status_code == 200
    projects = response.json()["projects"]
    assert len(projects) == 1
    assert projects[0]["name"] == "missing-host-path"
    assert projects[0]["host_path"].endswith("missing-host-path")


def test_create_idea_persists_metadata_and_syncs_agents(tmp_path):
    mount_root = tmp_path / "mounted"
    (mount_root / "spotlight-web").mkdir(parents=True)
    (mount_root / "spotlight-api").mkdir(parents=True)

    app = _make_app()
    paths = Paths(tmp_path)

    with (
        patch("app.gateway.routers.ideas.get_paths", return_value=paths),
        patch("app.gateway.routers.threads.get_paths", return_value=paths),
        patch("app.gateway.routers.ideas.get_app_config", return_value=_mock_config(mount_root)),
    ):
        with TestClient(app) as client:
            projects_response = client.get("/api/ideas/mounted-projects")
            project_ids = [project["id"] for project in projects_response.json()["projects"]]

            response = client.post(
                "/api/ideas",
                json={
                    "name": "Spotlight Platform",
                    "description": "Cross-repo rollout",
                    "project_ids": project_ids,
                    "planner": {
                        "model_name": "claude-sonnet-4.6",
                        "system_prompt": "Plan cross-repo work in waves.",
                    },
                    "worker": {
                        "model_name": "gpt-5.4",
                        "system_prompt": "Implement only after plan approval.",
                    },
                },
            )

    assert response.status_code == 201
    idea = response.json()
    assert idea["name"] == "Spotlight Platform"
    assert len(idea["projects"]) == 2
    assert idea["planner"]["agent_name"].endswith("-planner")
    assert idea["worker"]["agent_name"].endswith("-worker")

    idea_file = paths.idea_file(idea["id"])
    assert idea_file.exists()
    raw = json.loads(idea_file.read_text(encoding="utf-8"))
    assert raw["thread_ids"] == []

    planner_config = paths.agent_dir(idea["planner"]["agent_name"]) / "config.yaml"
    worker_config = paths.agent_dir(idea["worker"]["agent_name"]) / "config.yaml"
    assert planner_config.exists()
    assert worker_config.exists()
    assert "template_id: codex-orchestrator" in planner_config.read_text(encoding="utf-8")
    assert "tool_groups:" in worker_config.read_text(encoding="utf-8")


def test_attach_thread_and_delete_thread_prunes_idea_mapping(tmp_path):
    mount_root = tmp_path / "mounted"
    (mount_root / "spotlight-web").mkdir(parents=True)

    app = _make_app()
    paths = Paths(tmp_path)

    with (
        patch("app.gateway.routers.ideas.get_paths", return_value=paths),
        patch("app.gateway.routers.threads.get_paths", return_value=paths),
        patch("app.gateway.routers.ideas.get_app_config", return_value=_mock_config(mount_root)),
    ):
        with TestClient(app) as client:
            projects_response = client.get("/api/ideas/mounted-projects")
            project_id = projects_response.json()["projects"][0]["id"]

            create_response = client.post(
                "/api/ideas",
                json={
                    "name": "Spotlight Platform",
                    "project_ids": [project_id],
                    "planner": {},
                    "worker": {},
                },
            )
            idea_id = create_response.json()["id"]

            attach_response = client.post(f"/api/ideas/{idea_id}/threads/thread-123")
            assert attach_response.status_code == 200

            paths.sandbox_work_dir("thread-123").mkdir(parents=True, exist_ok=True)
            delete_response = client.delete("/api/threads/thread-123")

            assert delete_response.status_code == 200

            refreshed = client.get(f"/api/ideas/{idea_id}")

    assert refreshed.status_code == 200
    assert refreshed.json()["thread_ids"] == []
