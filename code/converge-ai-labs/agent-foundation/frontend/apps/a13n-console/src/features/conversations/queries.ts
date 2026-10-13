import { useQuery } from "@tanstack/react-query";
import { useClient } from "../../auth/context";
import { useWorkspace } from "../../layout/workspace";
import { conversationQueries } from "./api";

export function useRun(runId?: string | null) {
  const client = useClient(),
    { workspace } = useWorkspace();
  return useQuery({
    ...conversationQueries(client, workspace.id).run(runId ?? ""),
    enabled: !!runId,
  });
}

export function useSession(sessionId?: string | null) {
  const client = useClient(),
    { workspace } = useWorkspace();
  return useQuery({
    ...conversationQueries(client, workspace.id).session(sessionId ?? ""),
    enabled: !!sessionId,
  });
}
