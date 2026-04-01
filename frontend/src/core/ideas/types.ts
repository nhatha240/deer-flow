export interface IdeaProject {
  id: string;
  name: string;
  host_path: string;
  container_path: string;
  mount_host_path: string;
  mount_container_path: string;
  read_only: boolean;
}

export interface IdeaAgentSettings {
  agent_name: string;
  model_name: string | null;
  system_prompt: string;
}

export interface Idea {
  id: string;
  name: string;
  description: string;
  projects: IdeaProject[];
  planner: IdeaAgentSettings;
  worker: IdeaAgentSettings;
  thread_ids: string[];
  created_at: string;
  updated_at: string;
}

export interface IdeaAgentSettingsRequest {
  model_name?: string | null;
  system_prompt?: string;
}

export interface CreateIdeaRequest {
  name: string;
  description?: string | null;
  project_ids: string[];
  planner: IdeaAgentSettingsRequest;
  worker: IdeaAgentSettingsRequest;
}

export interface UpdateIdeaRequest extends CreateIdeaRequest {}
