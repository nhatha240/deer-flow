"use client";

import Link from "next/link";
import { useEffect } from "react";

import { IdeaPageHeader } from "@/components/idea/idea-page-header";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  WorkspaceBody,
  WorkspaceContainer,
} from "@/components/workspace/workspace-container";
import { useI18n } from "@/core/i18n/hooks";
import { useIdeas, useMountedProjects } from "@/core/ideas";
import { formatTimeAgo } from "@/core/utils/datetime";

export default function IdeasPage() {
  const { t } = useI18n();
  const { ideas } = useIdeas();
  const { projects } = useMountedProjects();

  useEffect(() => {
    document.title = `${t.sidebar.ideas} - ${t.pages.appName}`;
  }, [t.pages.appName, t.sidebar.ideas]);

  return (
    <WorkspaceContainer>
      <IdeaPageHeader />
      <WorkspaceBody className="overflow-auto">
        <div className="mx-auto flex w-full max-w-6xl flex-col gap-6 p-6">
          <div className="flex flex-col justify-between gap-4 md:flex-row md:items-center">
            <div className="space-y-1">
              <h1 className="text-2xl font-semibold">{t.ideas.title}</h1>
              <p className="text-muted-foreground text-sm">
                {t.ideas.description}
              </p>
            </div>
            <Button asChild>
              <Link href="/idea/new">{t.ideas.newIdea}</Link>
            </Button>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>{t.ideas.mountedProjects}</CardTitle>
              <CardDescription>{t.ideas.mountedProjectsDescription}</CardDescription>
            </CardHeader>
            <CardContent className="flex flex-wrap gap-2">
              {projects.map((project) => (
                <Badge key={project.id} variant="secondary">
                  {project.name}
                </Badge>
              ))}
              {projects.length === 0 && (
                <div className="text-muted-foreground text-sm">
                  {t.ideas.noMountedProjects}
                </div>
              )}
            </CardContent>
          </Card>

          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {ideas.map((idea) => (
              <Link key={idea.id} href={`/idea/${idea.id}`}>
                <Card className="h-full transition hover:border-primary/40 hover:shadow-md">
                  <CardHeader>
                    <CardTitle>{idea.name}</CardTitle>
                    <CardDescription>
                      {idea.description || t.ideas.noDescription}
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <div className="flex flex-wrap gap-2">
                      {idea.projects.map((project) => (
                        <Badge key={project.id} variant="outline">
                          {project.name}
                        </Badge>
                      ))}
                    </div>
                    <div className="text-muted-foreground text-sm">
                      {idea.thread_ids.length} {t.ideas.threads}
                    </div>
                    <div className="text-muted-foreground text-xs">
                      {formatTimeAgo(idea.updated_at)}
                    </div>
                  </CardContent>
                </Card>
              </Link>
            ))}
          </div>

          {ideas.length === 0 && (
            <Card>
              <CardHeader>
                <CardTitle>{t.ideas.emptyTitle}</CardTitle>
                <CardDescription>{t.ideas.emptyDescription}</CardDescription>
              </CardHeader>
            </Card>
          )}
        </div>
      </WorkspaceBody>
    </WorkspaceContainer>
  );
}
