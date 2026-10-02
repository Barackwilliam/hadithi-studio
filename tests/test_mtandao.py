import io
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, unquote, urlparse

from PIL import Image

from hadithi.images import MchorajiWaMtandao

MAOMBI = []


class Seva(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        u = urlparse(self.path)
        MAOMBI.append((unquote(u.path), parse_qs(u.query), self.headers.get("Authorization")))
        if len(MAOMBI) == 1:  # ombi la kwanza linashindwa ili kujaribu kurudia
            self.send_response(502); self.end_headers(); return
        q = parse_qs(u.query)
        buf = io.BytesIO()
        Image.new("RGB", (int(q["width"][0]), int(q["height"][0])), "red").save(buf, "JPEG")
        self.send_response(200); self.send_header("Content-Type", "image/jpeg"); self.end_headers()
        self.wfile.write(buf.getvalue())

    def log_message(self, *a):
        pass


def test_mchoraji_wa_mtandao(monkeypatch):
    srv = HTTPServer(("127.0.0.1", 0), Seva)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    monkeypatch.setenv("PICHA_URL", f"http://127.0.0.1:{srv.server_port}/prompt/{{maelezo}}")
    monkeypatch.setenv("PICHA_TOKEN", "siri")
    monkeypatch.setattr("hadithi.images.time.sleep", lambda s: None)
    img = MchorajiWaMtandao().chora("a girl, yellow dress / village", 640, 360, 7)
    srv.shutdown()
    assert img.size == (640, 360)
    njia, q, auth = MAOMBI[-1]
    assert njia == "/prompt/a girl, yellow dress / village"
    assert q["seed"] == ["7"] and q["model"] == ["flux"] and auth == "Bearer siri"
    assert len(MAOMBI) == 2


def test_torchao_ya_zamani_inaondolewa(monkeypatch):
    import importlib.metadata
    import subprocess
    import sys

    from hadithi.images import _ondoa_torchao_ya_zamani

    amri = []
    monkeypatch.setattr(subprocess, "run", lambda a, **k: amri.append(a))
    monkeypatch.delitem(sys.modules, "torchao", raising=False)
    for toleo, inaondolewa in (("0.10.0", True), ("0.16.1", False)):
        amri.clear()
        monkeypatch.setattr(importlib.metadata, "version", lambda n, t=toleo: t)
        _ondoa_torchao_ya_zamani()
        assert bool(amri) == inaondolewa
    assert amri == [] or "uninstall" in amri[0]
