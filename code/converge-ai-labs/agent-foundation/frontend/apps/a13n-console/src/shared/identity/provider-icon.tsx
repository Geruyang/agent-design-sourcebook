import { DesktopIcon } from "@phosphor-icons/react";
import { BrandIcon } from "a13n-ui";

export function ProviderIcon({ type }: { type: string }) {
  // The development-only local environment type is the one without a brand.
  return type === "local" ? (
    <DesktopIcon
      aria-hidden
      className="size-5 shrink-0 text-muted-foreground"
    />
  ) : (
    // The type doubles as an alias so vendor-prefixed types still find their mark.
    <BrandIcon identity={type} alias={type} />
  );
}
