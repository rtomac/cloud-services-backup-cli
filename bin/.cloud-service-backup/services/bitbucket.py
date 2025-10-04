import sys
import requests
from lib import *
from tools.git import *


@register_service("bitbucket")
class Bitbucket(GitHostService):
    """
Backs up Bitbucket repos owned by the specified user using
git and the Bitbucket API.

Subcommands:
  setup <atlassian_username>
        Requests and stores an API token from Atlassian
        to make API requests and clone repos.
  copy <atlassian_username>
        Fetches repos and clones them as bare repositories locally.
  sync <atlassian_username>
        Removes local repos and re-clones all repos.

API access tokens:
  Ensure you create an API access token with the following:
   - API token app = Bitbucket
   - Scope(s): read:repository:bitbucket
    """

    def __init__(self, username: str):
        super().__init__("bitbucket", "bitbucket.org",
            require_username(username, "atlassian_username"))

    def _get_repo_urls(self) -> list[str]:
        repos_uri = "https://api.bitbucket.org/2.0/repositories?role=owner"
        auth = self._get_credentials()
        pagelen = 100
        page = 1
        repo_urls = []
        while True:
            response = requests.get(repos_uri,
                params={'pagelen': pagelen, 'page': page},
                auth=auth)
            response.raise_for_status()
            repos_on_page = response.json()['values']
            for repo in repos_on_page:
                if repo['scm'] == 'git':
                    for clone_link in repo['links']['clone']:
                        if clone_link['name'] == 'https':
                            repo_urls.append(clone_link['href'])

            if len(repos_on_page) < pagelen:
                break
            page = page + 1
        return repo_urls
