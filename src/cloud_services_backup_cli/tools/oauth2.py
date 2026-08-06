import base64
import json
import webbrowser

from ..lib import error, google_oauth_creds


def has_browser() -> bool:
    try:
        webbrowser.get()
        return True
    except webbrowser.Error:
        return False


def require_browser() -> None:
    if not has_browser():
        error(
            "No web browser detected. OAuth2 authorization cannot proceed in headless mode. "
            "Please run this operation on a machine with a web browser."
        )


def prompt_for_authorize(service_slug: str, username: str) -> str:
    payload = encode_payload(username)
    cmd = f"cloud-service-backup {service_slug} authorize {payload}"
    print(f'''
No web browser detected. OAuth2 authorization cannot proceed in headless mode.

On a machine with a web browser, run the following to generate a token and paste it below:
   {cmd}

This is a one-time operation. If successful, this process can proceed in headless mode
from this point forward.
''')
    token = input("Paste the token here:\n").strip()
    if not token:
        raise RuntimeError("No token provided")
    return token


def print_authorize_token_export(token: str) -> None:
    print(f'''
Authorization successful, paste the following into your remote machine --->
{token}
<--- end paste
''')


def encode_payload(username: str) -> str:
    data = {"username": username}
    creds = google_oauth_creds()
    if creds:
        client_id, client_secret = creds
        data["client_id"] = client_id
        data["client_secret"] = client_secret
    return base64.b64encode(json.dumps(data).encode()).decode()


def decode_payload(payload: str):
    if not payload:
        return None, None
    data = json.loads(base64.b64decode(payload.encode()).decode())
    username = data.get("username")
    client_id = data.get("client_id")
    client_secret = data.get("client_secret")
    creds = (client_id, client_secret) if client_id and client_secret else None
    return username, creds
