import shutil

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image

from hadithi import seva

pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg haipo")


@pytest.fixture()
def mteja(tmp_path):
    kiini = seva.Kiini(tmp_path, "jaribio", api_key="", picha="mfano", sauti="kimya")
    app = FastAPI()
    seva.weka_kwenye(app, kiini)
    return TestClient(app), kiini


def ngoja(c, k):
    import time
    for _ in range(300):
        x = c.get(f"/api/hs/kazi/{k['id']}").json()
        if x["hali"] in ("imekamilika", "imeshindwa"):
            return x
        time.sleep(0.1)
    raise AssertionError("kazi haikuisha")


def test_ukurasa_na_hali(mteja):
    c, _ = mteja
    assert "Hadithi Studio" in c.get("/studio").text
    assert c.get("/studio/studio.js").status_code == 200
    assert c.get("/studio/../seva.py").status_code == 404
    h = c.get("/api/hs/hali").json()
    assert h["mradi"] == "jaribio" and h["hadithi"]["matukio"]


def test_miradi_na_matukio(mteja):
    c, kiini = mteja
    assert c.post("/api/hs/mradi/mfano", json={}).json()["mradi"] == "siri_ya_kisima"
    x = ngoja(c, c.post("/api/hs/kazi/chora", json={"aina": "yote"}).json())
    assert x["hali"] == "imekamilika", x
    picha = kiini.folda / "matukio"
    rangi = {n: Image.open(picha / f"tukio{n:03d}.png").getpixel((5, 5)) for n in (1, 2, 3)}
    # sogeza tukio 1 chini: picha zake zihame pamoja nalo
    assert c.post("/api/hs/tukio/hamisha", json={"namba": 1, "mwelekeo": 1}).json()["namba"] == 2
    assert Image.open(picha / "tukio002.png").getpixel((5, 5)) == rangi[1]
    # futa tukio 1 (lililokuwa la 2): wengine wasogee juu
    c.post("/api/hs/tukio/futa", json={"namba": 1})
    assert Image.open(picha / "tukio001.png").getpixel((5, 5)) == rangi[1]
    assert Image.open(picha / "tukio002.png").getpixel((5, 5)) == rangi[3]
    # tukio jipya katikati
    n = c.post("/api/hs/tukio/ongeza", json={"baada_ya": 1}).json()["namba"]
    assert n == 2 and not (picha / "tukio002.png").exists()
    r = c.post("/api/hs/tukio", json={"namba": 2, "picha": "a rainy day", "wahusika": ["amani"], "mwendo": "kulia",
                                      "mwendo_ai": True, "mistari": [{"msemaji": "amani", "maneno": "Mvua!"},
                                                                     {"msemaji": "msimulizi", "maneno": "Ilinyesha."}]})
    assert r.status_code == 200
    t = c.get("/api/hs/hali").json()["hadithi"]["matukio"][1]
    assert t["mazungumzo"] == [{"amani": "Mvua!"}, "Ilinyesha."] and t["mwendo_ai"] is True


def test_hariri_rudisha_na_episode(mteja):
    c, kiini = mteja
    c.post("/api/hs/mradi/mfano", json={})
    ngoja(c, c.post("/api/hs/kazi/chora", json={"aina": "wahusika"}).json())
    x = ngoja(c, c.post("/api/hs/kazi/hariri", json={"lengo": "mhusika", "id": "neema", "agizo": "kofia nyekundu"}).json())
    assert x["hali"] == "imekamilika", x
    assert c.get("/api/hs/hali").json()["matoleo"]["mhusika:neema"] == 1
    assert c.post("/api/hs/rudisha", json={"lengo": "mhusika", "id": "neema"}).status_code == 200
    assert c.post("/api/hs/rudisha", json={"lengo": "mhusika", "id": "neema"}).status_code == 400
    mpya = c.post("/api/hs/mradi/episode", json={}).json()["mradi"]
    assert mpya == "siri_ya_kisima_ep02"
    h = c.get("/api/hs/hali").json()
    assert "Episode 2" in h["hadithi"]["kichwa"] and h["mfululizo"]["iliyotangulia"] == "siri_ya_kisima"
    assert "neema" in h["picha"]["wahusika"]  # sura za wahusika zimebaki


def test_pakia_picha_yangu(mteja, tmp_path):
    import io
    c, kiini = mteja
    buf = io.BytesIO()
    Image.new("RGB", (300, 300), "red").save(buf, "PNG")
    r = c.post("/api/hs/pakia", data={"lengo": "tukio", "id": "1", "geuza": "hapana"},
               files={"faili": ("p.png", buf.getvalue(), "image/png")})
    assert r.status_code == 200
    f = kiini.folda / "matukio" / "tukio001.png"
    assert f.exists() and not f.with_suffix(".json").exists()
    assert Image.open(f).size == (1344, 768)


def test_ulinzi_wa_kuingia(tmp_path):
    kiini = seva.Kiini(tmp_path, "x", picha="mfano", sauti="kimya")
    app = FastAPI()
    app.auth, app.cookie_id, app.tokens = {"u": "p"}, "abc", {"tok": "u"}
    seva.weka_kwenye(app, kiini)
    c = TestClient(app)
    assert c.get("/api/hs/hali").status_code == 401
    assert c.get("/studio", follow_redirects=False).status_code == 307
    c.cookies.set("access-token-abc", "tok")
    assert c.get("/api/hs/hali").status_code == 200


def test_injini_ya_gpu(tmp_path, monkeypatch):
    import io
    import json
    kiini = seva.Kiini(tmp_path, "x", picha="mtandao", sauti="kimya")
    app = FastAPI()
    seva.weka_kwenye(app, kiini)
    c = TestClient(app)
    assert c.get("/api/hs/ping").json()["sawa"] is True
    assert c.get("/api/hs/injini").json() == {"url": None, "hai": False}
    monkeypatch.delenv("APP_PASSWORD", raising=False)
    assert c.post("/api/hs/injini/sajili", json={"url": "https://a.gradio.live", "siri": ""}).status_code == 403
    monkeypatch.setenv("APP_PASSWORD", "siri")
    assert c.post("/api/hs/injini/sajili", json={"url": "https://a.gradio.live", "siri": "mbaya"}).status_code == 403
    assert c.post("/api/hs/injini/sajili", json={"url": "javascript:x", "siri": "siri"}).status_code == 400
    assert c.post("/api/hs/injini/sajili", json={"url": "https://a.gradio.live/", "siri": "siri"}).status_code == 200
    assert c.get("/api/hs/injini").json() == {"url": "https://a.gradio.live", "hai": True}
    # baada ya muda, uhai hukaguliwa upya kwa ping
    kiini._injini_hali = (0.0, True)
    monkeypatch.setattr(seva.urllib.request, "urlopen", lambda *a, **k: (_ for _ in ()).throw(OSError("off")))
    assert c.get("/api/hs/injini").json()["hai"] is False
    # anwani hukumbukwa Space ikianza upya
    assert seva.Kiini(tmp_path, "x", picha="mtandao", sauti="kimya").injini_url == "https://a.gradio.live"


def test_fungua_faili_la_hadithi(mteja):
    c, kiini = mteja
    yaml_text = open("mifano/siri_ya_kisima.yaml", encoding="utf-8").read()
    r = c.post("/api/hs/mradi/pakia", files={"faili": ("kisima_changu.yaml", yaml_text.encode(), "text/yaml")})
    assert r.json()["mradi"] == "kisima_changu"
    assert c.get("/api/hs/hali").json()["hadithi"]["kichwa"] == "Siri ya Kisima cha Kijiji"
    assert c.post("/api/hs/mradi/pakia", files={"faili": ("x.yaml", b"matukio: []", "text/yaml")}).status_code == 400
