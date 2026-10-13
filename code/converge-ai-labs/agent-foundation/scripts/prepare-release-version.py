from __future__ import annotations

import argparse
from pathlib import Path

from release_version import COMPONENTS, ReleaseVersionError, prepare_component_version


def main() -> None:
    parser = argparse.ArgumentParser(description="Inject a release version into known manifests and lockfiles.")
    parser.add_argument("component", choices=COMPONENTS)
    parser.add_argument("version")
    args = parser.parse_args()

    try:
        changed = prepare_component_version(Path.cwd(), args.component, args.version)
    except ReleaseVersionError as error:
        raise SystemExit(str(error)) from error

    if changed:
        print(f"Prepared {args.component} version {args.version}:")
        for path in changed:
            print(f"- {path}")
    else:
        print(f"Prepared {args.component} version {args.version}; no files changed")


if __name__ == "__main__":
    main()
