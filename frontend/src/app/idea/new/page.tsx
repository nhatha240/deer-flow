"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { toast } from "sonner";

import { IdeaForm } from "@/components/idea/idea-form";
import { IdeaPageHeader } from "@/components/idea/idea-page-header";
import {
  WorkspaceBody,
  WorkspaceContainer,
} from "@/components/workspace/workspace-container";
import { useI18n } from "@/core/i18n/hooks";
import { useCreateIdea } from "@/core/ideas";

export default function NewIdeaPage() {
  const { t } = useI18n();
  const router = useRouter();
  const { mutateAsync: createIdea, isPending } = useCreateIdea();

  useEffect(() => {
    document.title = `${t.ideas.newIdea} - ${t.pages.appName}`;
  }, [t.ideas.newIdea, t.pages.appName]);

  return (
    <WorkspaceContainer>
      <IdeaPageHeader title={t.ideas.newIdea} />
      <WorkspaceBody className="overflow-auto">
        <IdeaForm
          submitLabel={t.ideas.createIdea}
          isSubmitting={isPending}
          onSubmit={async (request) => {
            const idea = await createIdea(request);
            toast.success(t.ideas.createSuccess);
            router.push(`/idea/${idea.id}`);
          }}
        />
      </WorkspaceBody>
    </WorkspaceContainer>
  );
}
