"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useMemo } from "react";
import { toast } from "sonner";

import { IdeaForm } from "@/components/idea/idea-form";
import { IdeaPageHeader } from "@/components/idea/idea-page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  WorkspaceBody,
  WorkspaceContainer,
} from "@/components/workspace/workspace-container";
import { useI18n } from "@/core/i18n/hooks";
import { useDeleteIdea, useIdea, useUpdateIdea } from "@/core/ideas";
import { useThreads } from "@/core/threads/hooks";
import { titleOfThread } from "@/core/threads/utils";
import { formatTimeAgo } from "@/core/utils/datetime";

export default function IdeaDetailPage() {
  const { t } = useI18n();
  const router = useRouter();
  const { idea_id } = useParams<{ idea_id: string }>();
  const { idea, isLoading } = useIdea(idea_id);
  const { data: threads = [] } = useThreads();
  const { mutateAsync: updateIdea, isPending: isUpdating } = useUpdateIdea();
  const { mutateAsync: deleteIdea, isPending: isDeleting } = useDeleteIdea();

  const ideaThreads = useMemo(() => {
    if (!idea) {
      return [];
    }
    const threadIds = new Set(idea.thread_ids);
    return threads.filter((thread) => threadIds.has(thread.thread_id));
  }, [idea, threads]);

  useEffect(() => {
    document.title = idea
      ? `${idea.name} - ${t.pages.appName}`
      : `${t.sidebar.ideas} - ${t.pages.appName}`;
  }, [idea, t.pages.appName, t.sidebar.ideas]);

  if (isLoading || !idea) {
    return (
      <WorkspaceContainer>
        <IdeaPageHeader title={t.common.loading} />
        <WorkspaceBody className="justify-center">
          <div className="text-muted-foreground text-sm">{t.common.loading}</div>
        </WorkspaceBody>
      </WorkspaceContainer>
    );
  }

  return (
    <WorkspaceContainer>
      <IdeaPageHeader title={idea.name} />
      <WorkspaceBody className="overflow-auto">
        <div className="mx-auto flex w-full max-w-6xl flex-col gap-6 p-6">
          <div className="flex flex-col justify-between gap-4 md:flex-row md:items-center">
            <div className="space-y-2">
              <div className="flex flex-wrap gap-2">
                {idea.projects.map((project) => (
                  <Badge key={project.id} variant="secondary">
                    {project.name}
                  </Badge>
                ))}
              </div>
              <div className="text-muted-foreground text-sm">
                {idea.thread_ids.length} {t.ideas.threads}
              </div>
            </div>
            <div className="flex flex-wrap gap-2">
              <Button asChild>
                <Link href={`/idea/${idea.id}/threads/new`}>
                  {t.ideas.openPlanner}
                </Link>
              </Button>
              <Button
                variant="destructive"
                disabled={isDeleting}
                onClick={async () => {
                  if (!window.confirm(t.ideas.deleteConfirm)) {
                    return;
                  }
                  await deleteIdea(idea.id);
                  toast.success(t.ideas.deleteSuccess);
                  router.push("/idea");
                }}
              >
                {t.ideas.deleteIdea}
              </Button>
            </div>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>{t.ideas.threadsTitle}</CardTitle>
              <CardDescription>{t.ideas.threadsDescription}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {ideaThreads.map((thread) => (
                <Link
                  key={thread.thread_id}
                  href={`/idea/${idea.id}/threads/${thread.thread_id}`}
                  className="block rounded-xl border p-4 transition hover:border-primary/40 hover:bg-muted/30"
                >
                  <div className="font-medium">{titleOfThread(thread)}</div>
                  {thread.updated_at && (
                    <div className="text-muted-foreground mt-1 text-sm">
                      {formatTimeAgo(thread.updated_at)}
                    </div>
                  )}
                </Link>
              ))}
              {ideaThreads.length === 0 && (
                <div className="text-muted-foreground text-sm">
                  {t.ideas.noThreads}
                </div>
              )}
            </CardContent>
          </Card>

          <IdeaForm
            idea={idea}
            submitLabel={t.common.save}
            isSubmitting={isUpdating}
            onSubmit={async (request) => {
              await updateIdea({ id: idea.id, request });
              toast.success(t.ideas.saveSuccess);
            }}
          />
        </div>
      </WorkspaceBody>
    </WorkspaceContainer>
  );
}
