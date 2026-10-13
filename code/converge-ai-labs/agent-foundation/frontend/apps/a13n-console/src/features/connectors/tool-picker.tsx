import { Button, Checkbox, Input, Label } from "a13n-ui";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import type { Schema } from "../../shared/api";
import layout from "./connectors.module.css";

/** A connection offers agents at most this many tools; each definition costs model context. */
export const MAX_TOOLS = 128;
const PAGE = 40;

/** The app actions a connection offers; saved names the app no longer lists stay visible so they can be removed. */
export function ConnectorToolPicker({
  catalog,
  value,
  disabled = false,
  onChange,
}: {
  catalog: readonly Schema["ToolInfo"][];
  value: readonly string[];
  disabled?: boolean;
  onChange: (value: string[]) => void;
}) {
  const { t } = useTranslation();
  const [search, setSearch] = useState(""),
    [limit, setLimit] = useState(PAGE);
  const known = new Set(catalog.map((tool) => tool.name));
  const tools = [
    ...catalog.map((tool) => ({
      name: tool.name,
      description: tool.description ?? "",
      unavailable: false,
    })),
    ...value
      .filter((name) => !known.has(name))
      .map((name) => ({ name, description: "", unavailable: true })),
  ];
  const term = search.trim().toLocaleLowerCase();
  const shown = term
    ? tools.filter((tool) =>
        `${tool.name} ${tool.description}`.toLocaleLowerCase().includes(term),
      )
    : tools;
  const full = value.length >= MAX_TOOLS;
  return (
    <fieldset className={layout.tools}>
      <legend className={layout.toolsHeader}>
        <span>{t("Tools")}</span>
        <span className={layout.checkNote}>
          {t("{{count}} of {{total}} on", {
            count: value.length,
            total: tools.length,
          })}
        </span>
      </legend>
      <p className={layout.checkNote}>
        {t("Choose up to {{max}} tools for agents to use.", {
          max: MAX_TOOLS,
        })}
      </p>
      {tools.length > PAGE && (
        <Input
          type="search"
          aria-label={t("Search tools")}
          placeholder={t("Search tools")}
          value={search}
          disabled={disabled}
          onChange={(event) => setSearch(event.target.value)}
        />
      )}
      <div className={`a13n-scrollbar ${layout.toolList}`}>
        {shown.slice(0, limit).map((tool) => {
          const checked = value.includes(tool.name);
          return (
            <div className={layout.tool} key={tool.name}>
              <Label className={layout.toolName}>
                <Checkbox
                  checked={checked}
                  disabled={disabled || (!checked && full)}
                  onCheckedChange={(next) =>
                    onChange(
                      next === true
                        ? [...value, tool.name]
                        : value.filter((name) => name !== tool.name),
                    )
                  }
                />
                <span title={tool.name}>{tool.name}</span>
              </Label>
              <span className={layout.toolDescription}>
                {tool.unavailable
                  ? t("Not in the current tool catalog")
                  : tool.description}
              </span>
            </div>
          );
        })}
        {shown.length > limit && (
          <Button
            type="button"
            variant="ghost"
            size="sm"
            className={layout.showMore}
            onClick={() => setLimit((current) => current + PAGE)}
          >
            {t("Show more tools")}
          </Button>
        )}
        {!shown.length && (
          <p className={layout.toolStatus}>{t("No tools found")}</p>
        )}
      </div>
    </fieldset>
  );
}
