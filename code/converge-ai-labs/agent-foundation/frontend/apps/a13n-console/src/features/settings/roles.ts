/** Membership is granted on a workspace or on the organization itself. */
export type MembershipScope = {
  kind: "workspace" | "organization";
  id: string;
};

/** A grant at organization scope applies its role to every workspace. */
export const roles = ["viewer", "runner", "builder", "admin"] as const;

export type Role = (typeof roles)[number];
