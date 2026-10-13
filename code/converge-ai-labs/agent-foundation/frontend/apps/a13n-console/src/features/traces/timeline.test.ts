import { describe, expect, it } from "vitest";
import type { Schema } from "../../shared/api";
import { observationRows, visibleRows } from "./timeline";
function observation(id: string, parent_id: string | null): Schema["Span"] {
  return {
    trace_id: "trace",
    id,
    parent_id,
    kind: "span",
    name: id,
    started_at: "2026-09-08T00:00:00Z",
    ended_at: null,
    status: "ok",
    level: null,
    status_message: null,
    model: null,
    usage: {},
    cost_usd: null,
    input: null,
    output: null,
    attributes: {},
    resource_attributes: {},
    scope: null,
    events: [],
    links: [],
    source_url: null,
  };
}
describe("trace topology", () => {
  it("places children after parents regardless of backend ordering and retains orphans", () => {
    expect(
      observationRows([
        observation("child", "root"),
        observation("orphan", "absent"),
        observation("root", null),
      ]).map((row) => [row.observation.id, row.depth]),
    ).toEqual([
      ["orphan", 0],
      ["root", 0],
      ["child", 1],
    ]);
  });
  it("retains cyclic observations without looping or duplicating nodes", () => {
    const rows = observationRows([
      observation("a", "b"),
      observation("b", "a"),
      observation("c", "c"),
    ]);
    expect(rows.map((row) => row.observation.id)).toEqual(["a", "b", "c"]);
    expect(rows[1]?.depth).toBe(1);
    expect(rows[0]?.observation.ended_at).toBeNull();
  });
});

describe("collapsed rows", () => {
  const rows = observationRows([
    observation("root", null),
    observation("branch", "root"),
    observation("leaf", "branch"),
    observation("sibling", "root"),
  ]);
  it("counts only the children placed directly beneath a row", () => {
    expect(
      rows.map((row) => [row.observation.id, row.depth, row.childCount]),
    ).toEqual([
      ["root", 0, 2],
      ["branch", 1, 1],
      ["leaf", 2, 0],
      ["sibling", 1, 0],
    ]);
  });
  it("hides the whole subtree of a collapsed row and nothing beside it", () => {
    expect(
      visibleRows(rows, new Set(["branch"])).map((row) => row.observation.id),
    ).toEqual(["root", "branch", "sibling"]);
    expect(
      visibleRows(rows, new Set(["root"])).map((row) => row.observation.id),
    ).toEqual(["root"]);
  });
  it("ignores collapsed rows that are themselves hidden or childless", () => {
    expect(
      visibleRows(rows, new Set(["root", "leaf"])).map(
        (row) => row.observation.id,
      ),
    ).toEqual(["root"]);
    expect(
      visibleRows(rows, new Set(["sibling"])).map((row) => row.observation.id),
    ).toEqual(["root", "branch", "leaf", "sibling"]);
  });
});
