"use client";

import Link from "next/link";

import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb";
import { useI18n } from "@/core/i18n/hooks";

import { GithubIcon } from "@/components/workspace/github-icon";
import { Tooltip } from "@/components/workspace/tooltip";

export function IdeaPageHeader({
  title,
  children,
}: {
  title?: string;
  children?: React.ReactNode;
}) {
  const { t } = useI18n();

  return (
    <header className="top-0 right-0 left-0 z-20 flex h-16 shrink-0 items-center justify-between gap-2 border-b backdrop-blur-sm transition-[width,height] ease-out group-has-data-[collapsible=icon]/sidebar-wrapper:h-12">
      <div className="flex items-center gap-2 px-4">
        <Breadcrumb>
          <BreadcrumbList>
            <BreadcrumbItem>
              <BreadcrumbLink asChild>
                <Link href="/idea">{t.sidebar.ideas}</Link>
              </BreadcrumbLink>
            </BreadcrumbItem>
            {title && (
              <>
                <BreadcrumbSeparator />
                <BreadcrumbItem>
                  <BreadcrumbPage>{title}</BreadcrumbPage>
                </BreadcrumbItem>
              </>
            )}
            {children && (
              <>
                <BreadcrumbSeparator />
                {children}
              </>
            )}
          </BreadcrumbList>
        </Breadcrumb>
      </div>
      <div className="pr-4">
        <Tooltip content={t.workspace.githubTooltip}>
          <a
            href="https://github.com/bytedance/deer-flow"
            target="_blank"
            rel="noopener noreferrer"
            className="opacity-75 transition hover:opacity-100"
          >
            <GithubIcon className="size-6" />
          </a>
        </Tooltip>
      </div>
    </header>
  );
}
