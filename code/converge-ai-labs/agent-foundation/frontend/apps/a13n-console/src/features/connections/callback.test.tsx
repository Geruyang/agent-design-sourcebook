// @vitest-environment jsdom
import { StrictMode } from "react";
import { MemoryRouter } from "react-router";
import { afterEach, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { ConnectionAuthorizationCallback } from "./callback";
const mocks = vi.hoisted(() => ({ clear: vi.fn() }));
vi.mock("./authorization-context", () => ({
  takeCallback: () => ({
    connectionId: "conn_test",
    status: "pending",
    error: "access_denied",
  }),
  readAuthorization: () => ({
    returnPath: "/workspace/design/connections",
    connectionId: "conn_test",
  }),
  clearAuthorization: mocks.clear,
}));
vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    i18n: { resolvedLanguage: "en" },
  }),
}));
afterEach(cleanup);
it("reports a refused authorization once under StrictMode and directs to connection status", async () => {
  render(
    <StrictMode>
      <MemoryRouter>
        <ConnectionAuthorizationCallback />
      </MemoryRouter>
    </StrictMode>,
  );
  await screen.findByText("access_denied (conn_test)");
  expect(mocks.clear).toHaveBeenCalledTimes(1);
  expect(
    screen.getByRole("link", { name: "Continue" }).getAttribute("href"),
  ).toBe("/workspace/design/connections?connection=conn_test");
});
