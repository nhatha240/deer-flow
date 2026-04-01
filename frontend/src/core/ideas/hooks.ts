import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  attachIdeaThread,
  createIdea,
  deleteIdea,
  getIdea,
  listIdeas,
  listMountedProjects,
  updateIdea,
} from "./api";
import type { CreateIdeaRequest, UpdateIdeaRequest } from "./types";

export function useIdeas() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["ideas"],
    queryFn: () => listIdeas(),
  });
  return { ideas: data ?? [], isLoading, error };
}

export function useIdea(id: string | null | undefined) {
  const { data, isLoading, error } = useQuery({
    queryKey: ["ideas", id],
    queryFn: () => getIdea(id!),
    enabled: !!id,
  });
  return { idea: data ?? null, isLoading, error };
}

export function useMountedProjects() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["ideas", "mounted-projects"],
    queryFn: () => listMountedProjects(),
  });
  return { projects: data ?? [], isLoading, error };
}

export function useCreateIdea() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (request: CreateIdeaRequest) => createIdea(request),
    onSuccess: (idea) => {
      void queryClient.invalidateQueries({ queryKey: ["ideas"] });
      void queryClient.setQueryData(["ideas", idea.id], idea);
    },
  });
}

export function useUpdateIdea() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      request,
    }: {
      id: string;
      request: UpdateIdeaRequest;
    }) => updateIdea(id, request),
    onSuccess: (idea) => {
      void queryClient.invalidateQueries({ queryKey: ["ideas"] });
      void queryClient.setQueryData(["ideas", idea.id], idea);
    },
  });
}

export function useDeleteIdea() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteIdea(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["ideas"] });
    },
  });
}

export function useAttachIdeaThread() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      ideaId,
      threadId,
    }: {
      ideaId: string;
      threadId: string;
    }) => attachIdeaThread(ideaId, threadId),
    onSuccess: (_data, { ideaId }) => {
      void queryClient.invalidateQueries({ queryKey: ["ideas"] });
      void queryClient.invalidateQueries({ queryKey: ["ideas", ideaId] });
    },
  });
}
