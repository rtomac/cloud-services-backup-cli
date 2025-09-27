import sys
import requests

uid = sys.argv[1]
pwd = sys.argv[2]

repos_uri = "https://api.github.com/user/repos?type=owner"
auth = (uid, pwd)
headers = {'accept': 'application/vnd.github.v3+json'}
per_page = 100
page = 1
while True:
    response = requests.get(repos_uri,
        params={'per_page': per_page, 'page': page},
        auth=auth,
        headers=headers)
    response.raise_for_status()
    repos = response.json()
    for repo in response.json():
        print(repo['clone_url'])
    
    if len(repos) < per_page:
        break
    page = page + 1
