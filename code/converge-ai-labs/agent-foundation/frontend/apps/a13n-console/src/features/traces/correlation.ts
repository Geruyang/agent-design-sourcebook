import type { Schema } from "../../shared/api";

const metadata = "a13n.observation.metadata.";

/** The span attribute naming each correlation field; the Service stamps them on every span of an attempt. */
export const correlationAttributes = {
  organization_id: `${metadata}organization_id`,
  workspace_id: `${metadata}workspace_id`,
  session_id: `${metadata}session_id`,
  thread_id: "a13n.observation.session.id",
  run_id: `${metadata}service_run_id`,
  run_attempt_id: `${metadata}run_attempt_id`,
} as const;

export type TraceCorrelation = Record<
  keyof typeof correlationAttributes,
  string | null
>;

/** The Service scope a trace was recorded in, read from its root span. */
export function traceCorrelation(root: Schema["Span"]): TraceCorrelation {
  const text = (key: string) => {
    const value = root.attributes[key];
    return typeof value === "string" ? value : null;
  };
  return {
    organization_id: text(correlationAttributes.organization_id),
    workspace_id: text(correlationAttributes.workspace_id),
    session_id: text(correlationAttributes.session_id),
    thread_id: text(correlationAttributes.thread_id),
    run_id: text(correlationAttributes.run_id),
    run_attempt_id: text(correlationAttributes.run_attempt_id),
  };
}

/** The Console path of the traced run, which is addressed by its session and thread. */
export function runPath(basePath: string, correlation: TraceCorrelation) {
  const { session_id, thread_id, run_id } = correlation;
  return session_id && thread_id && run_id
    ? `${basePath}/sessions/${session_id}/threads/${thread_id}/runs/${run_id}`
    : null;
}
