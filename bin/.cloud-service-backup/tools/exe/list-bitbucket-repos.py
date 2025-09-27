import sys
import requests

uid = sys.argv[1]
pwd = sys.argv[2]

repos_uri = "https://api.bitbucket.org/2.0/repositories?role=owner"
auth = (uid, pwd)
pagelen = 100
page = 1
while True:
    response = requests.get(repos_uri,
        params={'pagelen': pagelen, 'page': page},
        auth=auth)
    response.raise_for_status()
    repos = response.json()['values']
    for repo in repos:
        if repo['scm'] == 'git':
            for clone_link in repo['links']['clone']:
                if clone_link['name'] == 'https':
                    print(clone_link['href'])
    
    if len(repos) < pagelen:
        break
    page = page + 1
