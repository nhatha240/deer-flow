"use client";

import { FolderKanban, Lightbulb, Plus } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarRail,
  SidebarTrigger,
  useSidebar,
} from "@/components/ui/sidebar";
import { useI18n } from "@/core/i18n/hooks";
import { useIdeas } from "@/core/ideas";
import { cn } from "@/lib/utils";

export function IdeaSidebar({
  ...props
}: React.ComponentProps<typeof Sidebar>) {
  const { t } = useI18n();
  const pathname = usePathname();
  const { state } = useSidebar();
  const { ideas } = useIdeas();

  return (
    <>
      <Sidebar variant="sidebar" collapsible="icon" {...props}>
        <SidebarHeader className="py-0">
          <div
            className={cn(
              "group/workspace-header flex h-12 flex-col justify-center",
            )}
          >
            {state === "collapsed" ? (
              <div className="group-has-data-[collapsible=icon]/sidebar-wrapper:-translate-y flex w-full cursor-pointer items-center justify-center">
                <div className="text-primary block pt-1 font-serif group-hover/workspace-header:hidden">
                  DF
                </div>
                <SidebarTrigger className="hidden pl-2 group-hover/workspace-header:block" />
              </div>
            ) : (
              <div className="flex items-center justify-between gap-2">
                <Link href="/idea" className="text-primary ml-2 font-serif">
                  DeerFlow
                </Link>
                <SidebarTrigger />
              </div>
            )}
          </div>
          <SidebarMenu>
            <SidebarMenuItem>
              <SidebarMenuButton isActive={pathname === "/idea/new"} asChild>
                <Link className="text-muted-foreground" href="/idea/new">
                  <Plus size={16} />
                  <span>{t.ideas.newIdea}</span>
                </Link>
              </SidebarMenuButton>
            </SidebarMenuItem>
          </SidebarMenu>
        </SidebarHeader>

        <SidebarContent>
          <SidebarGroup className="pt-1">
            <SidebarMenu>
              <SidebarMenuItem>
                <SidebarMenuButton isActive={pathname === "/idea"} asChild>
                  <Link className="text-muted-foreground" href="/idea">
                    <Lightbulb />
                    <span>{t.sidebar.ideas}</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
            </SidebarMenu>
          </SidebarGroup>

          <SidebarGroup>
            <SidebarGroupLabel>{t.ideas.title}</SidebarGroupLabel>
            <SidebarGroupContent className="group-data-[collapsible=icon]:pointer-events-none group-data-[collapsible=icon]:-mt-8 group-data-[collapsible=icon]:opacity-0">
              <SidebarMenu>
                {ideas.map((idea) => {
                  const isActive =
                    pathname === `/idea/${idea.id}` ||
                    pathname.startsWith(`/idea/${idea.id}/threads/`);
                  return (
                    <SidebarMenuItem key={idea.id}>
                      <SidebarMenuButton isActive={isActive} asChild>
                        <Link
                          className="text-muted-foreground flex items-center gap-2"
                          href={`/idea/${idea.id}`}
                        >
                          <FolderKanban size={16} />
                          <span className="truncate">{idea.name}</span>
                        </Link>
                      </SidebarMenuButton>
                    </SidebarMenuItem>
                  );
                })}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        </SidebarContent>

        <SidebarFooter />
        <SidebarRail />
      </Sidebar>
    </>
  );
}
