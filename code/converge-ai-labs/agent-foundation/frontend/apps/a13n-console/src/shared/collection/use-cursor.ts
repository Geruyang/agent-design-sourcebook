import { useState } from "react";

/**
 * Previous/Next over a list's opaque cursors. A cursor is bound to the filters
 * that produced it, so other filters restart at the first page in the same
 * render: no request ever pairs a cursor with filters it was not issued for.
 */
export function useCursor(filters?: unknown) {
  const binding = JSON.stringify(filters ?? null);
  const [paged, setPaged] = useState({
    binding,
    history: [undefined] as (string | undefined)[],
  });
  const current = paged.binding === binding;
  // Forget the pages of other filters, so returning to them starts over too.
  if (!current) setPaged({ binding, history: [undefined] });
  const history = current ? paged.history : [undefined];
  return {
    cursor: history[history.length - 1],
    next: (cursor: string) =>
      setPaged({ binding, history: [...history, cursor] }),
    previous:
      history.length > 1
        ? () => setPaged({ binding, history: history.slice(0, -1) })
        : undefined,
  };
}
