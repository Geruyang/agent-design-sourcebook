from __future__ import annotations

import argparse
from pathlib import Path

from release_version import COMPONENTS, ReleaseVersionError, validate_component_version


def main() -> None:
    parser = argparse.ArgumentParser(description="Check release manifest and lockfile versions.")
    parser.add_argument("component", choices=COMPONENTS)
    parser.add_argument("version")
    args = parser.parse_args()

    try:
        validate_component_version(Path.cwd(), args.component, args.version)
    except ReleaseVersionError as error:
        raise SystemExit(str(error)) from error

    print(f"Validated {args.component} version {args.version}")


if __name__ == "__main__":
    main()
