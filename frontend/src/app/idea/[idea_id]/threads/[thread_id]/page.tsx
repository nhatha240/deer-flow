"use client";

import { Lightbulb, PlusSquare } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import type { PromptInputMessage } from "@/components/ai-elements/prompt-input";
import { Button } from "@/components/ui/button";
import { ArtifactTrigger } from "@/components/workspace/artifacts";
import { ChatBox, useThreadChat } from "@/components/workspace/chats";
import { ExportTrigger } from "@/components/workspace/export-trigger";
import { InputBox } from "@/components/workspace/input-box";
import { MessageList } from "@/components/workspace/messages";
import { ThreadContext } from "@/components/workspace/messages/context";
import { ThreadTitle } from "@/components/workspace/thread-title";
import { TodoList } from "@/components/workspace/todo-list";
import { TokenUsageIndicator } from "@/components/workspace/token-usage-indicator";
import { Tooltip } from "@/components/workspace/tooltip";
import { useI18n } from "@/core/i18n/hooks";
import { useAttachIdeaThread, useIdea } from "@/core/ideas";
import { useNotification } from "@/core/notification/hooks";
import { useLocalSettings } from "@/core/settings";
import { useThreadStream } from "@/core/threads/hooks";
import type { AgentThreadContext } from "@/core/threads/types";
import { textOfMessage } from "@/core/threads/utils";
import { env } from "@/env";
import { cn } from "@/lib/utils";

type ChatContext = Omit<
  AgentThreadContext,
  "thread_id" | "is_plan_mode" | "thinking_enabled" | "subagent_enabled"
> & {
  mode: "flash" | "thinking" | "pro" | "ultra" | undefined;
  reasoning_effort?: "minimal" | "low" | "medium" | "high";
};

export default function IdeaThreadPage() {
  const { t } = useI18n();
  const [settings, setSettings] = useLocalSettings();
  const { showNotification } = useNotification();
  const { mutateAsync: attachThread } = useAttachIdeaThread();
  const { idea_id } = useParams<{ idea_id: string; thread_id: string }>();
  const { idea, isLoading } = useIdea(idea_id);
  const { threadId, isNewThread, setIsNewThread, isMock } = useThreadChat();
  const [chatContext, setChatContext] = useState<ChatContext>({
    ...settings.context,
  });

  useEffect(() => {
    if (!idea) {
      return;
    }
    setChatContext((current) => ({
      ...current,
      agent_name: idea.planner.agent_name,
      model_name: idea.planner.model_name ?? current.model_name,
    }));
  }, [idea?.id, idea?.planner.agent_name, idea?.planner.model_name]);

  const [thread, sendMessage, isUploading] = useThreadStream({
    threadId: isNewThread ? undefined : threadId,
    context: chatContext,
    isMock,
    onStart: (startedThreadId) => {
      setIsNewThread(false);
      history.replaceState(null, "", `/idea/${idea_id}/threads/${threadId}`);
      void attachThread({ ideaId: idea_id, threadId: startedThreadId }).catch(
        (error) => {
          const message =
            error instanceof Error ? error.message : "Failed to attach thread";
          toast.error(message);
        },
      );
    },
    onFinish: (state) => {
      if (document.hidden || !document.hasFocus()) {
        let body = "Conversation finished";
        const lastMessage = state.messages.at(-1);
        if (lastMessage) {
          const textContent = textOfMessage(lastMessage);
          if (textContent) {
            body =
              textContent.length > 200
                ? textContent.substring(0, 200) + "..."
                : textContent;
          }
        }
        showNotification(state.title, { body });
      }
    },
  });

  const handleSubmit = useCallback(
    (message: PromptInputMessage) => {
      void sendMessage(threadId, message);
    },
    [sendMessage, threadId],
  );

  const handleStop = useCallback(async () => {
    await thread.stop();
  }, [thread]);

  if (isLoading || !idea) {
    return (
      <div className="text-muted-foreground flex size-full items-center justify-center text-sm">
        {t.common.loading}
      </div>
    );
  }

  return (
    <ThreadContext.Provider value={{ thread, isMock }}>
      <ChatBox threadId={threadId}>
        <div className="relative flex size-full min-h-0 justify-between">
          <header
            className={cn(
              "absolute top-0 right-0 left-0 z-30 flex h-12 shrink-0 items-center gap-2 px-4",
              isNewThread
                ? "bg-background/0 backdrop-blur-none"
                : "bg-background/80 shadow-xs backdrop-blur",
            )}
          >
            <div className="flex shrink-0 items-center gap-1.5 rounded-md border px-2 py-1">
              <Lightbulb className="text-primary h-3.5 w-3.5" />
              <span className="text-xs font-medium">{idea.name}</span>
            </div>

            <div className="min-w-0 flex-1 text-sm font-medium">
              <ThreadTitle threadId={threadId} thread={thread} />
            </div>

            <div className="mr-4 flex items-center">
              <Tooltip content={t.ideas.newPlannerChat}>
                <Button size="sm" variant="secondary" asChild>
                  <Link href={`/idea/${idea.id}/threads/new`}>
                    <PlusSquare /> {t.ideas.newPlannerChat}
                  </Link>
                </Button>
              </Tooltip>
              <TokenUsageIndicator messages={thread.messages} />
              <ExportTrigger threadId={threadId} />
              <ArtifactTrigger />
            </div>
          </header>

          <main className="flex min-h-0 max-w-full grow flex-col">
            <div className="flex size-full justify-center">
              <MessageList
                className={cn("size-full", !isNewThread && "pt-10")}
                threadId={threadId}
                thread={thread}
              />
            </div>

            <div className="absolute right-0 bottom-0 left-0 z-30 flex justify-center px-4">
              <div
                className={cn(
                  "relative w-full",
                  isNewThread && "-translate-y-[calc(50vh-96px)]",
                  isNewThread
                    ? "max-w-(--container-width-sm)"
                    : "max-w-(--container-width-md)",
                )}
              >
                <div className="absolute -top-4 right-0 left-0 z-0">
                  <div className="absolute right-0 bottom-0 left-0">
                    <TodoList
                      className="bg-background/5"
                      todos={thread.values.todos ?? []}
                      hidden={
                        !thread.values.todos || thread.values.todos.length === 0
                      }
                    />
                  </div>
                </div>

                <InputBox
                  className={cn("bg-background/5 w-full -translate-y-4")}
                  isNewThread={isNewThread}
                  threadId={threadId}
                  autoFocus={isNewThread}
                  status={
                    thread.error
                      ? "error"
                      : thread.isLoading
                        ? "streaming"
                        : "ready"
                  }
                  context={chatContext}
                  extraHeader={
                    isNewThread && (
                      <div className="mb-3 rounded-xl border bg-background/80 p-4">
                        <div className="text-sm font-medium">
                          {t.ideas.plannerTitle}
                        </div>
                        <div className="text-muted-foreground mt-1 text-sm">
                          {idea.projects.map((project) => project.name).join(", ")}
                        </div>
                      </div>
                    )
                  }
                  disabled={
                    env.NEXT_PUBLIC_STATIC_WEBSITE_ONLY === "true" ||
                    isUploading
                  }
                  onContextChange={(nextContext) => {
                    setChatContext((current) => ({
                      ...current,
                      ...nextContext,
                      agent_name: idea.planner.agent_name,
                    }));
                    setSettings("context", {
                      mode: nextContext.mode,
                      reasoning_effort: nextContext.reasoning_effort,
                    });
                  }}
                  onSubmit={handleSubmit}
                  onStop={handleStop}
                />

                {env.NEXT_PUBLIC_STATIC_WEBSITE_ONLY === "true" && (
                  <div className="text-muted-foreground/67 w-full translate-y-12 text-center text-xs">
                    {t.common.notAvailableInDemoMode}
                  </div>
                )}
              </div>
            </div>
          </main>
        </div>
      </ChatBox>
    </ThreadContext.Provider>
  );
}
