// @vitest-environment jsdom
import { act, renderHook } from "@testing-library/react";
import { expect, it } from "vitest";
import { useCursor } from "./use-cursor";

it("restarts paging whenever its filters change, without pairing a cursor with other filters", () => {
  const seen: [string, string | undefined][] = [];
  const { result, rerender } = renderHook(
    ({ q }: { q: string }) => {
      const page = useCursor({ q });
      seen.push([q, page.cursor]);
      return page;
    },
    { initialProps: { q: "" } },
  );
  act(() => result.current.next("two"));
  expect(result.current.cursor).toBe("two");
  expect(result.current.previous).toBeTypeOf("function");
  rerender({ q: "scout" });
  expect(result.current.cursor).toBeUndefined();
  expect(result.current.previous).toBeUndefined();
  // Returning to the earlier filters starts at their first page again.
  rerender({ q: "" });
  expect(result.current.cursor).toBeUndefined();
  expect(seen).not.toContainEqual(["scout", "two"]);
  // Equal filters, even as a new object, keep the page.
  act(() => result.current.next("two"));
  rerender({ q: "" });
  expect(result.current.cursor).toBe("two");
});
