"""Read NISAR HDF5 granules straight from ASF over HTTP range requests (no full download).

GCOV rasters are stored in 512x512 gzip chunks, so h5py only fetches the chunks a window touches
(~5 requests for metadata, then a few MB per window per date). Files are 0.2–8 GB, windows a few MB.
"""
import io


def get_retry(session, url, tries=5, **kw):
    """GET with retries: ASF / CloudFront sometimes drop a connection ('Remote end closed connection') or return 5xx."""
    import time, requests
    for k in range(tries):
        try:
            r = session.get(url, **kw)
            if r.status_code >= 500 and k < tries - 1:
                raise requests.ConnectionError(f"HTTP {r.status_code}")
            r.raise_for_status()
            return r
        except (requests.ConnectionError, requests.Timeout, requests.exceptions.ChunkedEncodingError):
            if k == tries - 1:
                raise
            time.sleep(min(30, 2 * 2 ** k))


class RangeFile(io.RawIOBase):
    """Read-only, block-cached, seekable file over HTTP range requests (each request retried on network hiccups)."""

    def __init__(self, url, session, block=4 << 20):
        r = get_retry(session, url, headers={"Range": "bytes=0-0"}, allow_redirects=True, timeout=60)
        self.s, self.url = session, r.url          # signed CloudFront URL after the Earthdata redirects
        self.size = int(r.headers["Content-Range"].split("/")[-1])
        self.pos, self.block, self.cache = 0, block, {}

    def readable(self): return True
    def seekable(self): return True
    def tell(self): return self.pos

    def seek(self, off, whence=0):
        self.pos = {0: off, 1: self.pos + off, 2: self.size + off}[whence]
        return self.pos

    def _block(self, i):
        if i not in self.cache:
            a = i * self.block
            r = get_retry(self.s, self.url, headers={"Range": f"bytes={a}-{min(a + self.block, self.size) - 1}"}, timeout=120)
            self.cache[i] = r.content
        return self.cache[i]

    def readinto(self, buf):
        n = min(len(buf), self.size - self.pos)
        if n <= 0:
            return 0
        out, p = bytearray(), self.pos
        while len(out) < n:
            i, o = divmod(p, self.block)
            chunk = self._block(i)[o:o + n - len(out)]
            out += chunk
            p += len(chunk)
        buf[:n] = out
        self.pos += n
        return n


def open_h5(path_or_url, session=None):
    import h5py
    if str(path_or_url).startswith("http"):
        from .auth import session as default_session
        return h5py.File(RangeFile(path_or_url, session or default_session()), "r")
    return h5py.File(path_or_url, "r")
