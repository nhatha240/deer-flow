export interface Agent {
  name: string;
  description: string;
  model: string | null;
  tool_groups: string[] | null;
  allow_mcp_tools: boolean;
  allow_acp_tools: boolean;
  allow_subagents: boolean;
  denied_tool_names?: string[] | null;
  template_id?: string | null;
  soul?: string | null;
}

export interface AgentTemplate {
  id: string;
  name: string;
  description: string;
}

export interface CreateAgentRequest {
  name: string;
  template_id?: string | null;
  description?: string | null;
  model?: string | null;
  tool_groups?: string[] | null;
  allow_mcp_tools?: boolean | null;
  allow_acp_tools?: boolean | null;
  allow_subagents?: boolean | null;
  denied_tool_names?: string[] | null;
  soul?: string | null;
}

export interface UpdateAgentRequest {
  description?: string | null;
  model?: string | null;
  tool_groups?: string[] | null;
  allow_mcp_tools?: boolean | null;
  allow_acp_tools?: boolean | null;
  allow_subagents?: boolean | null;
  denied_tool_names?: string[] | null;
  soul?: string | null;
}
