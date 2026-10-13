"""GitHub import: resolve a ref to a commit and read one directory of it, before any transaction opens."""

import re
from dataclasses import dataclass
from urllib.parse import quote

import httpx2
from a13n_harness.providers.endpoint_policy import EndpointPolicy, EndpointPolicyError
from anyio import to_thread

from a13n_service.infra.errors import ServiceError, conflict, invalid, rate_limited
from a13n_service.infra.outbound import open_http
from a13n_service.resources.skills.package import read_directory
from a13n_service.resources.skills.schemas import GitHubSource

_HEADERS = {"accept": "application/vnd.github+json", "x-github-api-version": "2022-11-28", "user-agent": "a13n-service"}
_COMMIT = re.compile(r"^[0-9a-f]{40}$")


@dataclass(frozen=True, slots=True)
class GitHub:
    """Anonymous reads of public repositories under the deployment's outbound endpoint policy."""

    policy: EndpointPolicy
    timeout: float
    max_bytes: int  # bounds each response, including the whole repository archive
    api_url: str = "https://api.github.com"

    async def fetch(self, source: GitHubSource) -> tuple[str, dict[str, bytes]]:
        """The commit `source.ref` resolves to and the files below `source.path` at that commit."""
        repository = f"{self.api_url}/repos/{source.repository}"
        try:
            async with open_http(self.policy, timeout=self.timeout, max_bytes=self.max_bytes) as client:
                resolved = await client.get(
                    f"{repository}/commits/{quote(source.ref or 'HEAD', safe='/')}",
                    headers={**_HEADERS, "accept": "application/vnd.github.sha"},
                )
                _require_success(resolved)
                commit = resolved.text.strip()
                if _COMMIT.fullmatch(commit) is None:
                    raise ServiceError("unavailable", "GitHub returned an invalid commit", {"dependency": "github"})
                if source.commit is not None and source.commit != commit:
                    raise conflict("repository", source.repository, "commit_mismatch")
                # The archive endpoint answers with one redirect to its download host; the policy checks both.
                redirect = await client.get(f"{repository}/zipball/{commit}", headers=_HEADERS)
                if redirect.status_code != 302 or "location" not in redirect.headers:
                    _require_success(redirect)
                    raise ServiceError("unavailable", "GitHub did not provide an archive", {"dependency": "github"})
                archive = await client.get(redirect.headers["location"], headers={"user-agent": _HEADERS["user-agent"]})
                _require_success(archive)
        except (httpx2.HTTPError, EndpointPolicyError):
            raise ServiceError("unavailable", "GitHub could not be reached", {"dependency": "github"}) from None
        files = await to_thread.run_sync(read_directory, archive.content, source.path)
        if not files:
            raise invalid("source", "the path has no files at the resolved commit")
        return commit, files


def _require_success(response: httpx2.Response) -> None:
    if response.status_code == 200:
        return
    if response.status_code in {404, 422}:
        raise invalid("source", "the repository, ref or path was not found")
    if response.status_code in {403, 429}:
        retry_after = response.headers.get("retry-after", "")
        raise rate_limited("GitHub is rate limiting imports", int(retry_after) if retry_after.isdigit() else 60)
    raise ServiceError("unavailable", f"GitHub answered {response.status_code}", {"dependency": "github"})
