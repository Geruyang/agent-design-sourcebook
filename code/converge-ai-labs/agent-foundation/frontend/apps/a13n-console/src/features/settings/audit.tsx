import { useQuery } from "@tanstack/react-query";
import { GearSixIcon, PulseIcon } from "@phosphor-icons/react";

import { useTranslation } from "react-i18next";
import { useClient } from "../../auth/context";
import { UserAvatar } from "../../layout/avatar";
import { data } from "../../shared/api";
import {
  CollectionFooter,
  Empty,
  Pagination,
  ResourceIdentity,
  ResourceTable,
  useCursor,
} from "../../shared/collection";
import { ErrorNotice, Loading, Timestamp } from "../../shared/feedback";
import { CopyableId } from "../../shared/identity";
import styles from "../../shared/shared.module.css";
import settings from "./settings.module.css";
import type { ProfileTarget } from "./profile";

/**
 * Security activity for a workspace, an organization, or the reader's own
 * account. The service pages this collection and offers no server-side
 * filters, so the list stays unfiltered rather than filtering one page.
 */
export function Audit({ scope }: { scope: ProfileTarget }) {
  const client = useClient(),
    { t } = useTranslation(),
    page = useCursor();
  const query = useQuery({
    queryKey: [
      "audit",
      scope.kind,
      scope.kind === "personal" ? "me" : scope.id,
      page.cursor,
    ],
    queryFn: ({ signal }) => {
      const params = { query: { cursor: page.cursor, limit: 30 } };
      if (scope.kind === "personal")
        return client.http
          .GET("/api/v1/users/me/audit-events", { params, signal })
          .then(data);
      if (scope.kind === "workspace")
        return client.http
          .GET("/api/v1/workspaces/{workspace_id}/audit-events", {
            params: { ...params, path: { workspace_id: scope.id } },
            signal,
          })
          .then(data);
      return client.http
        .GET("/api/v1/organizations/{organization_id}/audit-events", {
          params: { ...params, path: { organization_id: scope.id } },
          signal,
        })
        .then(data);
    },
  });
  if (query.isPending) return <Loading variant="table" columns={4} rows={5} />;
  if (!query.data)
    return (
      <ErrorNotice error={query.error} retry={() => void query.refetch()} />
    );
  const items = query.data.items;
  if (!items.length && !page.previous)
    return (
      <Empty
        icon={<PulseIcon aria-hidden="true" />}
        title={t("No activity yet")}
        description={t("Security events will appear here as changes are made.")}
      />
    );
  return (
    <div className={styles.stack}>
      <ResourceTable
        items={items}
        caption={t("Security activity")}
        columns={[
          {
            label: t("Actor"),
            tone: "primary",
            render: (item) => {
              const user = item.actor?.kind === "user" ? item.actor : undefined;
              if (user)
                return (
                  <ResourceIdentity
                    icon={
                      <UserAvatar
                        name={user.name}
                        id={user.id}
                        url={user.image_url}
                        className="size-8 rounded-[8px]"
                      />
                    }
                    name={user.name}
                    description={user.email ?? undefined}
                    resourceId={user.id}
                  />
                );
              return (
                <ResourceIdentity
                  icon={<GearSixIcon size={15} aria-hidden="true" />}
                  name={item.actor?.name ?? t("System")}
                  description={item.actor_id ?? undefined}
                  resourceId={item.actor_id ?? undefined}
                />
              );
            },
          },
          {
            label: t("Action"),
            render: (item) => item.action,
          },
          {
            label: t("Resource"),
            render: (item) => (
              <span className={settings.stacked}>
                <span>{item.target_kind}</span>
                <CopyableId value={item.target_id} />
              </span>
            ),
          },
          {
            label: t("When"),
            tone: "muted",
            render: (item) => <Timestamp value={item.occurred_at} relative />,
          },
        ]}
      />
      <CollectionFooter count={t("{{count}} events", { count: items.length })}>
        <Pagination page={page} next={query.data.next_cursor} />
      </CollectionFooter>
    </div>
  );
}
