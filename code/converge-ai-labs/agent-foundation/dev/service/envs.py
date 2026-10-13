"""List this machine's checkout instances, and remove selected ones with their local data. Stdlib only."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

from dev.service import lifecycle, stores
from dev.service.checkout import ROOT
from dev.service.instance import Instance, load_instance, machine_lock, registered_instances, save_registry


def _worktrees() -> dict[str, str | None]:
    """Git worktrees of this repository, by path, with their branch."""
    listed = subprocess.run(
        ["git", "-C", str(ROOT), "worktree", "list", "--porcelain"], check=True, capture_output=True, text=True
    ).stdout
    worktrees: dict[str, str | None] = {}
    for block in listed.strip().split("\n\n"):
        fields: dict[str, str] = {}
        for line in block.splitlines():
            key, _, value = line.partition(" ")
            fields[key] = value
        worktrees[str(Path(fields["worktree"]).resolve())] = (
            fields.get("branch", "").removeprefix("refs/heads/") or None
        )
    return worktrees


def _projects() -> dict[str, str]:
    """Status of every local Compose project of this workflow, including stopped ones."""
    listed = subprocess.run(
        ["docker", "compose", "ls", "--all", "--format", "json"], check=True, capture_output=True, text=True
    ).stdout
    return {
        project["Name"]: project["Status"]
        for project in json.loads(listed or "[]")
        if project["Name"].startswith(stores.PROJECT_PREFIX)
    }


def list_environments() -> list[dict[str, object]]:
    worktrees, registered, projects = _worktrees(), registered_instances(), _projects()
    rows: list[dict[str, object]] = []
    for root in sorted(set(worktrees) | set(registered)):
        instance = registered.get(root)
        rows.append(
            {
                "instance": instance.id if instance else None,
                "root": root,
                "branch": worktrees.get(root),
                "worktree": root in worktrees,
                "ports": instance.ports.named() if instance else None,
                "stores": projects.pop(stores.project(instance), None) if instance else None,
                "owner": lifecycle.owner(Path(root)) if instance else None,
            }
        )
    # Projects whose checkout registration is gone are listed for investigation, never removed from here.
    for name, state in projects.items():
        rows.append({"instance": name.removeprefix(stores.PROJECT_PREFIX), "stores": state})
    return rows


def remove(instance: Instance) -> None:
    """Stop the checkout's applications, then delete its stores, its var/dev and its port reservation."""
    root = Path(instance.root)
    state = root / "var/dev"
    if state.resolve() != state or load_instance(root) != instance:
        raise ValueError(f"{state} does not hold this registered instance")
    lifecycle.stop_applications(root)
    with lifecycle.owning(root, "remove"):
        stores.delete(instance)
        with machine_lock():
            records = registered_instances()
            records.pop(str(root), None)
            save_registry(records)
        shutil.rmtree(state)


def main() -> None:
    parser = argparse.ArgumentParser(prog="python3 -m dev.service.envs", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    listed = commands.add_parser("list", help="list checkouts and their local instances")
    listed.add_argument("--json", action="store_true")
    removed = commands.add_parser("rm", help="remove registered instances with their containers, volumes and var/dev")
    removed.add_argument("ids", nargs="+")
    confirm = removed.add_mutually_exclusive_group(required=True)
    confirm.add_argument("--dry-run", action="store_true")
    confirm.add_argument("--yes", action="store_true", help="confirm the deletion")
    args = parser.parse_args()
    try:
        if args.command == "list":
            _print(list_environments(), as_json=args.json)
            return
        by_id = {instance.id: instance for instance in registered_instances().values()}
        if unknown := [item for item in args.ids if item not in by_id]:
            raise ValueError(f"Not a registered instance: {', '.join(unknown)}")
        for item in dict.fromkeys(args.ids):
            instance = by_id[item]
            if args.dry_run:
                print(
                    f"{item}: would stop its applications and delete {stores.project(instance)} and {instance.root}/var/dev"
                )
            else:
                remove(instance)
                print(f"{item}: removed")
    except (ValueError, RuntimeError, OSError, subprocess.CalledProcessError) as error:
        print(error, file=sys.stderr)
        raise SystemExit(1) from None


def _print(rows: list[dict[str, object]], *, as_json: bool) -> None:
    if as_json:
        print(json.dumps(rows, indent=2))
        return
    print(f"{'INSTANCE':12}  {'STORES':12}  {'APPLICATIONS':14}  {'BRANCH':36}  PATH")
    for row in rows:
        owner = row.get("owner")
        running = owner.get("command") if isinstance(owner, dict) else "-"
        print(
            f"{row['instance'] or '-':12}  {row['stores'] or '-':12}  {running:14}  "
            f"{row.get('branch') or '-':36}  {row.get('root') or '(checkout not registered)'}"
        )


if __name__ == "__main__":
    main()
