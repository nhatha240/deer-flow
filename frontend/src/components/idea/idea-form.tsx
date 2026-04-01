"use client";

import { Loader2 } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { useI18n } from "@/core/i18n/hooks";
import { useMountedProjects } from "@/core/ideas";
import type { CreateIdeaRequest, Idea } from "@/core/ideas";
import { useModels } from "@/core/models/hooks";
import type { Model } from "@/core/models/types";
import { cn } from "@/lib/utils";

type IdeaFormState = CreateIdeaRequest & {
  description: string;
  planner: {
    model_name: string;
    system_prompt: string;
  };
  worker: {
    model_name: string;
    system_prompt: string;
  };
};

const DEFAULT_PLANNER_PROMPT =
  "Read all selected repositories before planning. Break the work into dependency-aware waves. Output execution-ready prompts with exact repository paths and clear hand-off boundaries.";
const DEFAULT_WORKER_PROMPT =
  "Implement only the scoped task in the assigned repositories. Keep changes production-ready, call out cross-repo impact, and do not expand scope without an explicit requirement.";

function buildIdeaFormState(
  idea: Idea | null | undefined,
  models: Model[],
): IdeaFormState {
  const fallbackModel = models[0]?.name ?? "";
  return {
    name: idea?.name ?? "",
    description: idea?.description ?? "",
    project_ids: idea?.projects.map((project) => project.id) ?? [],
    planner: {
      model_name: idea?.planner.model_name ?? fallbackModel,
      system_prompt:
        idea?.planner.system_prompt.trim() || DEFAULT_PLANNER_PROMPT,
    },
    worker: {
      model_name: idea?.worker.model_name ?? fallbackModel,
      system_prompt: idea?.worker.system_prompt.trim() || DEFAULT_WORKER_PROMPT,
    },
  };
}

export function IdeaForm({
  idea,
  submitLabel,
  isSubmitting,
  onSubmit,
}: {
  idea?: Idea | null;
  submitLabel: string;
  isSubmitting?: boolean;
  onSubmit: (request: CreateIdeaRequest) => Promise<void> | void;
}) {
  const { t } = useI18n();
  const { projects, isLoading: projectsLoading } = useMountedProjects();
  const { models } = useModels();
  const [state, setState] = useState<IdeaFormState>(() =>
    buildIdeaFormState(idea, models),
  );

  useEffect(() => {
    setState(buildIdeaFormState(idea, models));
  }, [idea?.id, idea?.updated_at, models]);

  const selectedProjects = useMemo(() => {
    const selectedIds = new Set(state.project_ids);
    return projects.filter((project) => selectedIds.has(project.id));
  }, [projects, state.project_ids]);

  const handleToggleProject = (projectId: string) => {
    setState((current) => {
      const selected = new Set(current.project_ids);
      if (selected.has(projectId)) {
        selected.delete(projectId);
      } else {
        selected.add(projectId);
      }
      return {
        ...current,
        project_ids: Array.from(selected),
      };
    });
  };

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    await onSubmit({
      name: state.name.trim(),
      description: state.description.trim(),
      project_ids: state.project_ids,
      planner: {
        model_name: state.planner.model_name,
        system_prompt: state.planner.system_prompt.trim(),
      },
      worker: {
        model_name: state.worker.model_name,
        system_prompt: state.worker.system_prompt.trim(),
      },
    });
  };

  return (
    <form className="mx-auto flex w-full max-w-6xl flex-col gap-6 p-6" onSubmit={handleSubmit}>
      <div className="grid gap-6 lg:grid-cols-[1.15fr_0.85fr]">
        <Card>
          <CardHeader>
            <CardTitle>{t.ideas.formScopeTitle}</CardTitle>
            <CardDescription>{t.ideas.formScopeDescription}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-5">
            <div className="space-y-2">
              <label className="text-sm font-medium">{t.ideas.nameLabel}</label>
              <Input
                value={state.name}
                placeholder={t.ideas.namePlaceholder}
                onChange={(event) =>
                  setState((current) => ({
                    ...current,
                    name: event.target.value,
                  }))
                }
              />
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">
                {t.ideas.descriptionLabel}
              </label>
              <Textarea
                rows={4}
                value={state.description}
                placeholder={t.ideas.descriptionPlaceholder}
                onChange={(event) =>
                  setState((current) => ({
                    ...current,
                    description: event.target.value,
                  }))
                }
              />
            </div>

            <div className="space-y-3">
              <div className="flex items-center justify-between gap-2">
                <label className="text-sm font-medium">
                  {t.ideas.mountedProjects}
                </label>
                <Badge variant="secondary">
                  {selectedProjects.length} {t.ideas.selectedProjects}
                </Badge>
              </div>
              <div className="grid gap-3">
                {projectsLoading && (
                  <div className="text-muted-foreground text-sm">
                    {t.common.loading}
                  </div>
                )}
                {!projectsLoading && projects.length === 0 && (
                  <div className="text-muted-foreground rounded-lg border border-dashed p-4 text-sm">
                    {t.ideas.noMountedProjects}
                  </div>
                )}
                {projects.map((project) => {
                  const selected = state.project_ids.includes(project.id);
                  return (
                    <button
                      key={project.id}
                      type="button"
                      className={cn(
                        "flex w-full flex-col gap-2 rounded-xl border p-4 text-left transition",
                        selected
                          ? "border-primary bg-primary/5"
                          : "hover:bg-muted/40",
                      )}
                      onClick={() => handleToggleProject(project.id)}
                    >
                      <div className="flex items-center justify-between gap-3">
                        <div className="font-medium">{project.name}</div>
                        <Badge variant={selected ? "default" : "outline"}>
                          {selected
                            ? t.ideas.selectedBadge
                            : t.ideas.availableBadge}
                        </Badge>
                      </div>
                      <div className="text-muted-foreground text-xs">
                        {project.host_path}
                      </div>
                      <div className="text-muted-foreground text-xs">
                        {project.container_path}
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>
          </CardContent>
        </Card>

        <div className="flex flex-col gap-6">
          <IdeaAgentCard
            title={t.ideas.plannerTitle}
            description={t.ideas.plannerDescription}
            modelLabel={t.ideas.modelLabel}
            promptLabel={t.ideas.systemPromptLabel}
            promptPlaceholder={t.ideas.plannerPromptPlaceholder}
            models={models}
            value={state.planner}
            onChange={(next) =>
              setState((current) => ({
                ...current,
                planner: next,
              }))
            }
          />

          <IdeaAgentCard
            title={t.ideas.workerTitle}
            description={t.ideas.workerDescription}
            modelLabel={t.ideas.modelLabel}
            promptLabel={t.ideas.systemPromptLabel}
            promptPlaceholder={t.ideas.workerPromptPlaceholder}
            models={models}
            value={state.worker}
            onChange={(next) =>
              setState((current) => ({
                ...current,
                worker: next,
              }))
            }
          />
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>{t.ideas.formSummaryTitle}</CardTitle>
          <CardDescription>{t.ideas.formSummaryDescription}</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          {selectedProjects.map((project) => (
            <Badge key={project.id} variant="secondary">
              {project.name}
            </Badge>
          ))}
          {selectedProjects.length === 0 && (
            <div className="text-muted-foreground text-sm">
              {t.ideas.selectAtLeastOneProject}
            </div>
          )}
        </CardContent>
        <CardFooter className="justify-end border-t">
          <Button
            type="submit"
            disabled={
              isSubmitting ||
              !state.name.trim() ||
              state.project_ids.length === 0 ||
              !state.planner.model_name ||
              !state.worker.model_name
            }
          >
            {isSubmitting && <Loader2 className="animate-spin" />}
            {submitLabel}
          </Button>
        </CardFooter>
      </Card>
    </form>
  );
}

function IdeaAgentCard({
  title,
  description,
  modelLabel,
  promptLabel,
  promptPlaceholder,
  models,
  value,
  onChange,
}: {
  title: string;
  description: string;
  modelLabel: string;
  promptLabel: string;
  promptPlaceholder: string;
  models: Model[];
  value: {
    model_name: string;
    system_prompt: string;
  };
  onChange: (value: { model_name: string; system_prompt: string }) => void;
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <label className="text-sm font-medium">{modelLabel}</label>
          <Select
            value={value.model_name}
            onValueChange={(model_name) => onChange({ ...value, model_name })}
          >
            <SelectTrigger className="w-full">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {models.map((model) => (
                <SelectItem key={model.name} value={model.name}>
                  {model.display_name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-2">
          <label className="text-sm font-medium">{promptLabel}</label>
          <Textarea
            rows={8}
            value={value.system_prompt}
            placeholder={promptPlaceholder}
            onChange={(event) =>
              onChange({ ...value, system_prompt: event.target.value })
            }
          />
        </div>
      </CardContent>
    </Card>
  );
}
