import requests

from ..lib import *
from ..tools.git import *


@register_service("github")
class GitHub(GitHostService):
    """
Backs up GitHub repos owned by the specified user using
git and the GitHub API.

Subcommands:
  setup <github_username>
        Requests and stores a personal access token from GitHub
        to make API requests and clone repos.
  copy <github_username>
        Fetches repos and clones them as bare repositories locally.
  sync <github_username>
        Removes local repos and re-clones all repos.

Personal access tokens:
  Ensure you create personal access tokens with the following
  permissions:
   - Contents: read-only
   - Metadata: read-only
    """

    def __init__(self, username: str):
        super().__init__("github", "github.com",
            require_username(username, "github_username"))

    def _get_repo_urls(self) -> list[str]:
        repos_uri = "https://api.github.com/user/repos?type=owner"
        auth = self._get_credentials()
        headers = {'accept': 'application/vnd.github.v3+json'}
        per_page = 100
        page = 1
        repo_urls = []
        while True:
            response = requests.get(repos_uri,
                params={'per_page': per_page, 'page': page},
                auth=auth,
                headers=headers)
            response.raise_for_status()
            repos_on_page = response.json()
            repo_urls.extend([repo["clone_url"] for repo in repos_on_page])

            if len(repos_on_page) < per_page:
                break
            page = page + 1
        return repo_urls
