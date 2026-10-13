import { useEffect, useRef, useState } from "react";
import { Link } from "react-router";
import { useTranslation } from "react-i18next";
import { ErrorNotice, Loading } from "../../shared/feedback";
import { Page } from "../../shared/page";
import {
  clearAuthorization,
  readAuthorization,
  takeCallback,
} from "./authorization-context";

let callback = takeCallback();
export function ConnectionAuthorizationCallback() {
  const { t } = useTranslation();
  const started = useRef(false),
    [context] = useState(readAuthorization),
    [error, setError] = useState<unknown>(null);
  useEffect(() => {
    if (started.current) return;
    started.current = true;
    const outcome = callback;
    callback = null;
    clearAuthorization();
    if (!context || !outcome) {
      setError(
        new Error(
          t(
            "Authorization context is missing or expired. Sign in and start authorization again in this tab.",
          ),
        ),
      );
      return;
    }
    if (outcome.connectionId !== context.connectionId) {
      setError(new Error(t("Authorization returned a different connection.")));
      return;
    }
    if (outcome.error || outcome.status !== "ready") {
      setError(
        new Error(
          `${outcome.error ?? outcome.status} (${outcome.connectionId})`,
        ),
      );
      return;
    }
    const target = new URL(context.returnPath, window.location.origin);
    target.searchParams.set("connection", outcome.connectionId);
    window.location.replace(target.href);
  }, [context, t]);
  return (
    <Page title={t("Verifying authorization")}>
      {error ? (
        <>
          <ErrorNotice error={error} />
          <p>
            {t(
              "Check the connection status before starting another authorization.",
            )}
          </p>
          <Link
            to={
              context
                ? `${context.returnPath}?connection=${encodeURIComponent(context.connectionId)}`
                : "/login"
            }
          >
            {t("Continue")}
          </Link>
        </>
      ) : (
        <Loading />
      )}
    </Page>
  );
}
