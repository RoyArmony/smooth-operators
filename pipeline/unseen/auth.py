"""NASA Earthdata Login for ASF (NISAR) and other Earthdata DAACs (LP DAAC, PO.DAAC).

Credentials, in order:
  1. EARTHDATA_TOKEN (environment or repo .env): a revocable EDL token from urs.earthdata.nasa.gov ->
     "Generate Token". Safer to share with a helper machine than a password (revoke it when done).
  2. EARTHDATA_USERNAME + EARTHDATA_PASSWORD (environment or repo .env)
  3. ~/.netrc entry:  machine urs.earthdata.nasa.gov login <user> password <pass>
The same session works for every Earthdata-protected URL: it follows the login redirect and the signed
CloudFront/S3 redirect that serve the bytes.
"""
import os
from functools import lru_cache

from . import config  # noqa: F401  (loads .env)


@lru_cache(maxsize=1)
def session():
    import asf_search as asf
    s = asf.ASFSession()
    token = os.environ.get("EARTHDATA_TOKEN")
    user, pw = os.environ.get("EARTHDATA_USERNAME"), os.environ.get("EARTHDATA_PASSWORD")
    if token:
        # asf_search's auth_with_token() validates via an EDL OAuth endpoint that rejects valid user tokens
        # (seen Nov 2026); the plain Bearer header works for NISAR, HLS and DSWx downloads.
        s.headers["Authorization"] = f"Bearer {token}"
    elif user and pw:
        s.auth_with_creds(user, pw)
    return s   # otherwise requests/asf use ~/.netrc automatically


def check(url=None):
    """Return (ok, message). Reads 1 byte of a protected NISAR file to prove the login works end to end."""
    from .nisar import search
    try:
        if url is None:
            g = search((104.0, 12.8, 104.1, 12.9))
            if not g:
                return False, "ASF search returned nothing (network?)"
            url = g[0]["url"]
        r = session().get(url, headers={"Range": "bytes=0-0"}, allow_redirects=True, timeout=60)
        if r.status_code in (200, 206) and r.content[:1]:
            return True, f"OK: read a byte of {url.rsplit('/', 1)[-1]} (HTTP {r.status_code})"
        return False, f"HTTP {r.status_code} — check your Earthdata login (~/.netrc or .env)"
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"
