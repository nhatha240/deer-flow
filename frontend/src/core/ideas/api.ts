import { getBackendBaseURL } from "@/core/config";

import type {
  CreateIdeaRequest,
  Idea,
  IdeaProject,
  UpdateIdeaRequest,
} from "./types";

export async function listIdeas(): Promise<Idea[]> {
  const res = await fetch(`${getBackendBaseURL()}/api/ideas`);
  if (!res.ok) {
    throw new Error(`Failed to load ideas: ${res.statusText}`);
  }
  const data = (await res.json()) as { ideas: Idea[] };
  return data.ideas;
}

export async function getIdea(id: string): Promise<Idea> {
  const res = await fetch(`${getBackendBaseURL()}/api/ideas/${id}`);
  if (!res.ok) {
    throw new Error(`Idea '${id}' not found`);
  }
  return res.json() as Promise<Idea>;
}

export async function listMountedProjects(): Promise<IdeaProject[]> {
  const res = await fetch(`${getBackendBaseURL()}/api/ideas/mounted-projects`);
  if (!res.ok) {
    throw new Error(`Failed to load mounted projects: ${res.statusText}`);
  }
  const data = (await res.json()) as { projects: IdeaProject[] };
  return data.projects;
}

export async function createIdea(request: CreateIdeaRequest): Promise<Idea> {
  const res = await fetch(`${getBackendBaseURL()}/api/ideas`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  if (!res.ok) {
    const err = (await res.json().catch(() => ({}))) as { detail?: string };
    throw new Error(err.detail ?? `Failed to create idea: ${res.statusText}`);
  }
  return res.json() as Promise<Idea>;
}

export async function updateIdea(
  id: string,
  request: UpdateIdeaRequest,
): Promise<Idea> {
  const res = await fetch(`${getBackendBaseURL()}/api/ideas/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  if (!res.ok) {
    const err = (await res.json().catch(() => ({}))) as { detail?: string };
    throw new Error(err.detail ?? `Failed to update idea: ${res.statusText}`);
  }
  return res.json() as Promise<Idea>;
}

export async function deleteIdea(id: string): Promise<void> {
  const res = await fetch(`${getBackendBaseURL()}/api/ideas/${id}`, {
    method: "DELETE",
  });
  if (!res.ok) {
    const err = (await res.json().catch(() => ({}))) as { detail?: string };
    throw new Error(err.detail ?? `Failed to delete idea: ${res.statusText}`);
  }
}

export async function attachIdeaThread(
  ideaId: string,
  threadId: string,
): Promise<void> {
  const res = await fetch(
    `${getBackendBaseURL()}/api/ideas/${ideaId}/threads/${threadId}`,
    {
      method: "POST",
    },
  );
  if (!res.ok) {
    const err = (await res.json().catch(() => ({}))) as { detail?: string };
    throw new Error(
      err.detail ?? `Failed to attach thread to idea: ${res.statusText}`,
    );
  }
}
