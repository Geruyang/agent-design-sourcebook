import type { components } from "./schema.js";

/** The body of the Service's one declared error envelope, `{"error": ErrorBody}`. */
type ErrorBody = components["schemas"]["ErrorBody"];

/**
 * Errors preserve safe Service evidence without retaining requests or
 * credentials. A response outside the envelope, such as a proxy's, keeps its
 * status with the code `http_error`.
 */
export class ApiError extends Error {
  override readonly name: string = "ApiError";
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
    readonly details: ErrorBody["details"],
    readonly requestId: ErrorBody["request_id"],
    readonly retryAfter: string | null = null,
  ) {
    super(message);
  }
}

export class ProtocolError extends Error {
  override readonly name = "ProtocolError";
}

export function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export async function requireSuccess(response: Response): Promise<void> {
  if (response.ok) return;
  let payload: unknown;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }
  const error =
    isRecord(payload) && isRecord(payload.error) ? payload.error : {};
  const code = typeof error.code === "string" ? error.code : "http_error";
  throw new ApiError(
    response.status,
    code,
    typeof error.message === "string"
      ? error.message
      : `Service request failed (${response.status}).`,
    isRecord(error.details) ? error.details : {},
    typeof error.request_id === "string"
      ? error.request_id
      : response.headers.get("X-Request-ID"),
    response.headers.get("Retry-After"),
  );
}

/** Extract a required representation; 204 operations should await their response directly. */
export function data<T>(result: { data?: T; response: Response }): T {
  if (result.data === undefined)
    throw new ProtocolError("The Service returned no representation.");
  return result.data;
}
