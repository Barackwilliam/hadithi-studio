"""Seva ya Hadithi Studio Pro: API (JSON) na ukurasa wa kitaalamu wa /studio.

Ukurasa (hadithi/web/) huongea na API hii. Kazi ndefu (picha, video) huendeshwa moja baada ya
nyingine kwenye "foleni", na ukurasa husoma maendeleo yake kupitia /api/hs/kazi/<id>.
"""
from __future__ import annotations

import io
import json
import os
import queue
import re
import shutil
import sys
import threading
import time
import traceback
import urllib.request
import uuid
from pathlib import Path

import yaml
from PIL import Image, ImageOps
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

from . import fomu
from .chat import KosaLaAI, Mwandishi, ondoa_yaml, toa_yaml
from .hariri import hariri_picha, katuni_kutoka_picha, matoleo_ya, rudisha_toleo, weka_picha_mpya
from .pipeline import Studio
from .story import MSIMULIZI, SAUTI, KosaLaHadithi, kutoka_data
from .voices import jaribu_sauti

WEB = Path(__file__).parent / "web"
KARIBU = ("👋 Karibu! Niambie wazo la hadithi yako, nami nitakuandikia hadithi kamili: wahusika, matukio na "
          "mazungumzo. Unaweza pia kunipa mpango wa series nzima, nikaanza na Episode 1.")


def slug(jina: str) -> str:
    return re.sub(r"[^a-z0-9_]+", "_", jina.lower()).strip("_")[:60] or "hadithi"


def _hakiki(data: dict) -> str | None:
    try:
        kutoka_data(data)
        return None
    except (KosaLaHadithi, TypeError, ValueError) as e:
        return str(e)


class _Tee(io.TextIOBase):
    """Andika kwenye kumbukumbu ya kazi na pia kwenye skrini ya Colab."""

    def __init__(self, asili, mistari: list[str]):
        self.asili, self.mistari, self._kipande = asili, mistari, ""

    def write(self, s: str) -> int:
        self.asili.write(s)
        self._kipande += s
        while "\n" in self._kipande:
            mstari, self._kipande = self._kipande.split("\n", 1)
            if mstari.strip():
                self.mistari.append(mstari.rstrip())
        return len(s)

    def flush(self) -> None:
        self.asili.flush()


class Kazi:
    def __init__(self, aina: str, mradi: str):
        self.id = uuid.uuid4().hex[:10]
        self.aina, self.mradi = aina, mradi
        self.hali = "inasubiri"
        self.log: list[str] = []
        self.matokeo: dict = {}
        self.kosa: str | None = None
        self.mwanzo = time.time()
        self.mwisho: float | None = None

    def json(self, mistari: int = 40) -> dict:
        return {"id": self.id, "aina": self.aina, "mradi": self.mradi, "hali": self.hali,
                "log": self.log[-mistari:], "matokeo": self.matokeo, "kosa": self.kosa,
                "sekunde": round((self.mwisho or time.time()) - self.mwanzo)}


class Kiini:
    """Hali yote ya Studio: miradi, hadithi, chat, foleni ya kazi."""

    def __init__(self, mzizi: str | Path, mradi: str = "hadithi_yangu", api_key: str = "",
                 picha: str = "sdxl", sauti: str = "edge"):
        self.mzizi = Path(mzizi)
        self.mzizi.mkdir(parents=True, exist_ok=True)
        self.api_key = api_key or ""
        self.injini_ya_picha, self.injini_ya_sauti = picha, sauti
        self._studio: Studio | None = None
        self._kufuli = threading.RLock()
        self.kazi: dict[str, Kazi] = {}
        self._foleni: queue.Queue = queue.Queue()
        threading.Thread(target=self._mfanyakazi, daemon=True).start()
        self.mradi = slug(mradi)
        # injini ya GPU (Colab) iliyojisajili kwenye ukurasa huu wa kudumu
        self._injini_faili = self.mzizi / ".injini.json"
        self.injini_url: str | None = None
        if self._injini_faili.exists():
            try:
                self.injini_url = json.loads(self._injini_faili.read_text()).get("url")
            except ValueError:
                pass
        self._injini_hali: tuple[float, bool] = (0.0, False)
        if not (self.folda / "hadithi.yaml").exists():
            self._unda_mradi(self.mradi)

    # ------------------------------------------------------------ miradi
    @property
    def folda(self) -> Path:
        return self.mzizi / self.mradi

    @property
    def faili(self) -> Path:
        return self.folda / "hadithi.yaml"

    def _unda_mradi(self, jina: str, data: dict | None = None) -> str:
        jina = slug(jina)
        msingi, i = jina, 2
        while (self.mzizi / jina / "hadithi.yaml").exists():
            jina, i = f"{msingi}_{i}", i + 1
        (self.mzizi / jina).mkdir(parents=True, exist_ok=True)
        (self.mzizi / jina / "hadithi.yaml").write_text(fomu.kwa_yaml(data or fomu.hadithi_tupu()), encoding="utf-8")
        return jina

    def miradi(self) -> list[dict]:
        orodha = []
        for f in self.mzizi.iterdir() if self.mzizi.exists() else []:
            y = f / "hadithi.yaml"
            if not y.exists():
                continue
            try:
                d = yaml.safe_load(y.read_text(encoding="utf-8")) or {}
            except yaml.YAMLError:
                d = {}
            jalada = next((p for p in sorted((f / "matukio").glob("tukio*.png"))), None) if (f / "matukio").exists() else None
            if jalada is None and (f / "wahusika").exists():
                jalada = next(iter(sorted((f / "wahusika").glob("*.png"))), None)
            video = sorted(f.glob("*.mp4"), key=lambda p: p.stat().st_mtime)
            orodha.append({
                "jina": f.name, "kichwa": str(d.get("kichwa", f.name)), "matukio": len(d.get("matukio") or []),
                "wahusika": len([k for k in (d.get("wahusika") or {}) if k != MSIMULIZI]),
                "jalada": self.url(jalada, f.name) if jalada else None, "video": bool(video),
                "ukubwa": d.get("ukubwa", "16:9"), "imebadilishwa": y.stat().st_mtime,
            })
        return sorted(orodha, key=lambda m: -m["imebadilishwa"])

    def chagua(self, jina: str) -> None:
        jina = slug(jina)
        if not (self.mzizi / jina / "hadithi.yaml").exists():
            raise HTTPException(404, "Mradi haupo.")
        self.mradi = jina

    # ------------------------------------------------------------ hadithi
    def data(self) -> dict:
        try:
            return fomu.kutoka_yaml(self.faili.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            return fomu.hadithi_tupu()

    def hifadhi(self, data: dict) -> None:
        self.faili.write_text(fomu.kwa_yaml(data), encoding="utf-8")

    def studio(self) -> Studio:
        kosa = _hakiki(self.data())
        if kosa:
            raise KosaLaHadithi(kosa)
        if self._studio is None:
            self._studio = Studio(self.faili, self.folda, self.injini_ya_picha, self.injini_ya_sauti)
        elif self._studio.folda != self.folda:
            self._studio.badilisha_mradi(self.faili, self.folda)
        else:
            self._studio.pakia_upya()
        return self._studio

    def url(self, faili: Path, mradi: str | None = None) -> str:
        mradi = mradi or self.mradi
        rel = faili.relative_to(self.mzizi / mradi).as_posix()
        return f"/api/hs/faili/{mradi}/{rel}?v={faili.stat().st_mtime_ns}"

    def hali(self) -> dict:
        d = self.data()
        f = self.folda
        picha_w = {k: self.url(f / "wahusika" / f"{k}.png") for k in (d.get("wahusika") or {})
                   if (f / "wahusika" / f"{k}.png").exists()}
        picha_m = {}
        for i in range(1, len(d.get("matukio") or []) + 1):
            p = f / "matukio" / f"tukio{i:03d}.png"
            if p.exists():
                picha_m[str(i)] = self.url(p)
        matoleo = {f"mhusika:{k}": len(matoleo_ya(f / "wahusika" / f"{k}.png")) for k in picha_w}
        matoleo |= {f"tukio:{n}": len(matoleo_ya(f / "matukio" / f"tukio{int(n):03d}.png")) for n in picha_m}
        video = [{"jina": v.name, "url": self.url(v), "mb": round(v.stat().st_size / 1e6, 1),
                  "saa": v.stat().st_mtime} for v in sorted(f.glob("*.mp4"), key=lambda p: -p.stat().st_mtime)]
        mfululizo = self._mfululizo()
        return {
            "mradi": self.mradi, "hadithi": d, "kosa": _hakiki(d), "picha": {"wahusika": picha_w, "matukio": picha_m},
            "matoleo": matoleo, "video": video, "chat": self.historia(), "mfululizo": mfululizo,
            "muziki": self.url(f / d["mipangilio"]["muziki"]) if (d.get("mipangilio") or {}).get("muziki")
            and (f / d["mipangilio"]["muziki"]).exists() else None,
            "mfumo": {"picha": self.injini_ya_picha, "sauti": self.injini_ya_sauti, "gemini": bool(self.api_key),
                      "gpu": self._ina_gpu()},
            "sauti": list(SAUTI), "mitindo": fomu.MITINDO,
            "kazi": [k.json(3) for k in self.kazi.values() if k.hali in ("inasubiri", "inaendelea")],
        }

    @staticmethod
    def _ina_gpu() -> bool:
        try:
            import torch

            return bool(torch.cuda.is_available())
        except Exception:  # noqa: BLE001
            return False

    # ------------------------------------------------------------ injini ya GPU (Colab)
    def sajili_injini(self, url: str) -> None:
        self.injini_url = url.rstrip("/")
        self._injini_hali = (time.time(), True)
        self._injini_faili.write_text(json.dumps({"url": self.injini_url, "saa": time.time()}))

    def injini(self) -> dict:
        """Je, Colab (GPU) iko hewani sasa hivi? Jibu huhifadhiwa kwa sekunde 20."""
        if not self.injini_url:
            return {"url": None, "hai": False}
        saa, hai = self._injini_hali
        if time.time() - saa > 20:
            try:
                with urllib.request.urlopen(f"{self.injini_url}/api/hs/ping", timeout=5) as r:
                    hai = json.loads(r.read()).get("sawa") is True
            except Exception:  # noqa: BLE001
                hai = False
            self._injini_hali = (time.time(), hai)
        return {"url": self.injini_url, "hai": hai}

    # ------------------------------------------------------------ series
    def _mfululizo(self) -> dict | None:
        p = self.folda / "mfululizo.json"
        return json.loads(p.read_text()) if p.exists() else None

    def episode_ijayo(self) -> str:
        d = self.data()
        m = re.match(r"^(.*?)(?:_ep(\d+))?$", self.mradi)
        msingi, n = m.group(1), int(m.group(2) or 1)
        if not m.group(2):  # mradi huu ni Episode 1: upe jina la series
            msingi = self.mradi
        kichwa_msingi = re.sub(r"\s*[-–:]\s*Episode\s*\d+$", "", str(d.get("kichwa", "")), flags=re.I)
        mpya = {
            "kichwa": f"{kichwa_msingi} - Episode {n + 1}", "mtindo": d.get("mtindo"), "ukubwa": d.get("ukubwa", "16:9"),
            "wahusika": d.get("wahusika") or {},
            "matukio": [{"picha": "...", "mazungumzo": [f"Episode {n + 1}..."]}],
        }
        if d.get("mipangilio"):
            mpya["mipangilio"] = d["mipangilio"]
        iliyotangulia = self.mradi
        jina = self._unda_mradi(f"{msingi}_ep{n + 1:02d}", mpya)
        if (self.folda / "wahusika").exists():  # sura za wahusika zibaki zile zile
            shutil.copytree(self.folda / "wahusika", self.mzizi / jina / "wahusika", dirs_exist_ok=True)
        if d.get("mipangilio", {}).get("muziki") and (self.folda / d["mipangilio"]["muziki"]).exists():
            shutil.copy2(self.folda / d["mipangilio"]["muziki"], self.mzizi / jina / d["mipangilio"]["muziki"])
        (self.mzizi / jina / "mfululizo.json").write_text(json.dumps({"iliyotangulia": iliyotangulia, "episode": n + 1}))
        self.mradi = jina
        self.hifadhi_historia([{"role": "assistant", "content":
                                f"📺 **Episode {n + 1}** iko tayari kuandikwa. Wahusika na sura zao wamebaki vile vile. "
                                "Niambie kinachotokea kwenye episode hii, au sema tu *\"Endelea na episode inayofuata\"*."}])
        return jina

    # ------------------------------------------------------------ chat
    def historia(self) -> list[dict]:
        p = self.folda / "chat.json"
        if p.exists():
            try:
                return json.loads(p.read_text(encoding="utf-8"))
            except ValueError:
                pass
        return [{"role": "assistant", "content": KARIBU}]

    def hifadhi_historia(self, h: list[dict]) -> None:
        (self.folda / "chat.json").write_text(json.dumps(h[-60:], ensure_ascii=False, indent=1), encoding="utf-8")

    def chat(self, ujumbe: str) -> dict:
        if not self.api_key:
            raise HTTPException(400, "Weka API key ya Gemini kwenye ⚙️ Mipangilio ili kutumia Chat.")
        data = self.data()
        historia = self.historia()
        muktadha = fomu.kwa_yaml(data)
        mf = self._mfululizo()
        if mf and (self.mzizi / mf["iliyotangulia"] / "hadithi.yaml").exists():
            awali = (self.mzizi / mf["iliyotangulia"] / "hadithi.yaml").read_text(encoding="utf-8")
            muktadha += ("\n\n# EPISODE ILIYOTANGULIA (kwa kumbukumbu tu; endeleza hadithi kutoka hapo, "
                         "tumia wahusika wale wale bila kubadilisha maelezo yao ya sura):\n" + awali)
        mw = Mwandishi(self.api_key)
        imesasishwa = False
        try:
            jibu = mw.jibu(historia, ujumbe, muktadha)
            y = toa_yaml(jibu)
            if y:
                kosa = None
                try:
                    mpya = fomu.kutoka_yaml(y)
                    kosa = _hakiki(mpya)
                except Exception as e:  # noqa: BLE001
                    kosa = str(e)
                if kosa:
                    jibu = mw.jibu(historia + [{"role": "user", "content": ujumbe}, {"role": "assistant", "content": jibu}],
                                   f"Hadithi uliyoandika ina kosa: {kosa}. Irekebishe na uiandike yote tena.", muktadha)
                    y = toa_yaml(jibu)
                    mpya = fomu.kutoka_yaml(y) if y else None
                    kosa = _hakiki(mpya) if mpya else "hakuna hadithi"
                if not kosa:
                    self.hifadhi(mpya)
                    imesasishwa = True
                else:
                    jibu += f"\n\n⚠️ Hadithi ina kosa ({kosa}), sijaihifadhi. Niambie nijaribu tena."
        except KosaLaAI as e:
            jibu = f"⚠️ {e}"
        except Exception as e:  # noqa: BLE001
            traceback.print_exc()
            jibu = f"⚠️ Imeshindikana kuwasiliana na AI: {str(e)[:300]}"
        safi = ondoa_yaml(jibu).replace("*(Hadithi imewekwa. Iangalie kwenye tabo ya 📝 Hadithi, au nenda 🎬 Video "
                                        "kutengeneza video)*", "*(Hadithi imesasishwa ✅)*")
        historia += [{"role": "user", "content": ujumbe}, {"role": "assistant", "content": safi}]
        self.hifadhi_historia(historia)
        return {"jibu": safi, "imesasishwa": imesasishwa}

    # ------------------------------------------------------------ picha za matukio (kuhamisha)
    def _panga_upya_picha(self, ramani: dict[int, int | None]) -> None:
        """Hamisha picha za matukio baada ya kupanga upya/kufuta. ramani: {namba_ya_zamani: mpya | None}."""
        folda = self.folda / "matukio"
        if not folda.exists():
            return
        tmp = folda / "_kuhamisha"
        tmp.mkdir(exist_ok=True)
        for zamani, mpya in ramani.items():
            for f in folda.glob(f"tukio{zamani:03d}.*"):
                if mpya is None:
                    f.unlink()
                else:
                    f.rename(tmp / f.name.replace(f"tukio{zamani:03d}", f"tukio{mpya:03d}", 1))
        for f in tmp.iterdir():
            f.replace(folda / f.name)
        tmp.rmdir()

    # ------------------------------------------------------------ kazi ndefu
    def anzisha(self, aina: str, kazi_yenyewe) -> Kazi:
        k = Kazi(aina, self.mradi)
        self.kazi[k.id] = k
        self._foleni.put((k, kazi_yenyewe))
        return k

    def _mfanyakazi(self) -> None:
        while True:
            k, fn = self._foleni.get()
            k.hali = "inaendelea"
            asili = sys.stdout
            sys.stdout = _Tee(asili, k.log)
            try:
                with self._kufuli:
                    k.matokeo = fn() or {}
                k.hali = "imekamilika"
            except (KosaLaHadithi, KosaLaAI) as e:
                k.hali, k.kosa = "imeshindwa", str(e)
            except Exception as e:  # noqa: BLE001
                traceback.print_exc()
                k.hali, k.kosa = "imeshindwa", f"{type(e).__name__}: {str(e)[:400]}"
            finally:
                sys.stdout = asili
                k.mwisho = time.time()


def _mlinzi(request: Request) -> None:
    """Ikiwa Gradio ina kuingia (auth), Studio nayo inalindwa na kuingia kule kule."""
    app = request.app
    if getattr(app, "auth", None) is None:
        return
    cid = getattr(app, "cookie_id", "")
    token = request.cookies.get(f"access-token-{cid}") or request.cookies.get(f"access-token-unsecure-{cid}")
    if token and token in getattr(app, "tokens", {}):
        return
    if request.url.path.startswith("/studio"):
        raise HTTPException(307, headers={"Location": "/"})  # ukurasa wa kuingia wa Gradio
    raise HTTPException(401, "Ingia kwanza.")


def tengeneza_router(kiini: Kiini) -> APIRouter:
    r = APIRouter(dependencies=[Depends(_mlinzi)])

    def ok(**ziada):
        return JSONResponse({"sawa": True, **ziada})

    # --------------------------------------------------------------- ukurasa
    @r.get("/studio")
    def ukurasa():
        return HTMLResponse((WEB / "index.html").read_text(encoding="utf-8"), headers={"Cache-Control": "no-cache"})

    @r.get("/studio/{jina}")
    def faili_za_ukurasa(jina: str):
        p = (WEB / jina).resolve()
        if p.parent != WEB.resolve() or not p.exists():
            raise HTTPException(404)
        return FileResponse(p, headers={"Cache-Control": "no-cache"})

    # --------------------------------------------------------------- hali & miradi
    @r.get("/api/hs/hali")
    def hali():
        return kiini.hali()

    @r.get("/api/hs/miradi")
    def miradi():
        return {"miradi": kiini.miradi(), "mradi": kiini.mradi}

    @r.post("/api/hs/mradi/mpya")
    def mradi_mpya(d: dict):
        data = fomu.hadithi_tupu()
        data["kichwa"] = (d.get("kichwa") or "Hadithi Mpya").strip()
        if d.get("ukubwa") in ("16:9", "9:16", "1:1"):
            data["ukubwa"] = d["ukubwa"]
        if d.get("mtindo"):
            data["mtindo"] = fomu.MITINDO.get(d["mtindo"], d["mtindo"])
        kiini.mradi = kiini._unda_mradi(d.get("jina") or data["kichwa"], data)
        return ok(mradi=kiini.mradi)

    @r.post("/api/hs/mradi/chagua")
    def mradi_chagua(d: dict):
        kiini.chagua(d.get("jina", ""))
        return ok(mradi=kiini.mradi)

    @r.post("/api/hs/mradi/pakia")
    async def mradi_pakia(faili: UploadFile = File(...)):
        try:
            data = fomu.kutoka_yaml((await faili.read()).decode("utf-8"))
        except Exception as e:  # noqa: BLE001
            raise HTTPException(400, f"Faili si hadithi sahihi (.yaml): {e}") from e
        kosa = _hakiki(data)
        if kosa:
            raise HTTPException(400, kosa)
        kiini.mradi = kiini._unda_mradi(Path(faili.filename or "hadithi").stem or data.get("kichwa", "hadithi"), data)
        return ok(mradi=kiini.mradi)

    @r.get("/api/hs/injini")
    def injini():
        return kiini.injini()

    @r.post("/api/hs/mradi/mfano")
    def mradi_mfano():
        mfano = Path(__file__).parent.parent / "mifano" / "siri_ya_kisima.yaml"
        data = fomu.kutoka_yaml(mfano.read_text(encoding="utf-8"))
        kiini.mradi = kiini._unda_mradi("siri_ya_kisima", data)
        return ok(mradi=kiini.mradi)

    @r.post("/api/hs/mradi/episode")
    def episode():
        return ok(mradi=kiini.episode_ijayo())

    @r.post("/api/hs/mradi/futa")
    def mradi_futa(d: dict):
        jina = slug(d.get("jina", ""))
        f = kiini.mzizi / jina
        if not (f / "hadithi.yaml").exists():
            raise HTTPException(404, "Mradi haupo.")
        shutil.rmtree(f)
        if kiini.mradi == jina:
            baki = kiini.miradi()
            kiini.mradi = baki[0]["jina"] if baki else kiini._unda_mradi("hadithi_yangu")
        return ok(mradi=kiini.mradi)

    # --------------------------------------------------------------- hadithi
    @r.post("/api/hs/hadithi/msingi")
    def msingi(d: dict):
        data = kiini.data()
        for k in ("kichwa", "mtindo", "ukubwa"):
            if d.get(k):
                data[k] = d[k].strip() if isinstance(d[k], str) else d[k]
        if isinstance(d.get("mipangilio"), dict):
            mp = dict(data.get("mipangilio") or {})
            mp.update({k: v for k, v in d["mipangilio"].items() if v is not None})
            data["mipangilio"] = mp
        kiini.hifadhi(data)
        return ok()

    @r.post("/api/hs/hadithi/yaml")
    def hadithi_yaml(d: dict):
        try:
            data = fomu.kutoka_yaml(d.get("yaml", ""))
        except Exception as e:  # noqa: BLE001
            raise HTTPException(400, f"YAML ina kosa: {e}") from e
        kosa = _hakiki(data)
        if kosa:
            raise HTTPException(400, kosa)
        kiini.hifadhi(data)
        return ok()

    @r.post("/api/hs/mhusika")
    def mhusika(d: dict):
        data = kiini.data()
        id_ = d.get("id") or None
        if id_ != MSIMULIZI and not (d.get("jina") or "").strip():
            raise HTTPException(400, "Andika jina la mhusika.")
        data, id_ = fomu.weka_mhusika(data, id_, d.get("jina", ""), d.get("maelezo", ""), d.get("sauti", "daudi"),
                                      int(d.get("kina", 0)), int(d.get("kasi", 0)))
        kiini.hifadhi(data)
        return ok(id=id_)

    @r.post("/api/hs/mhusika/futa")
    def mhusika_futa(d: dict):
        kiini.hifadhi(fomu.futa_mhusika(kiini.data(), d.get("id", "")))
        for f in (kiini.folda / "wahusika").glob(f"{d.get('id')}.*"):
            f.unlink()
        return ok()

    @r.post("/api/hs/tukio")
    def tukio(d: dict):
        data = kiini.data()
        n = d.get("namba")
        mazungumzo = "\n".join(
            (m.get("maneno", "").strip() if m.get("msemaji") in (None, "", MSIMULIZI)
             else f"{m['msemaji']}: {m.get('maneno', '').strip()}")
            for m in d.get("mistari") or [] if (m.get("maneno") or "").strip())
        if not (d.get("picha") or "").strip():
            raise HTTPException(400, "Eleza picha ya tukio.")
        data, n = fomu.weka_tukio(data, int(n) if n else None, d["picha"], d.get("wahusika") or [],
                                  d.get("mwendo") or "auto", mazungumzo, bool(d.get("mwendo_ai")))
        kiini.hifadhi(data)
        return ok(namba=n)

    @r.post("/api/hs/tukio/ongeza")
    def tukio_ongeza(d: dict):
        data = kiini.data()
        baada = int(d.get("baada_ya", len(data["matukio"])))
        mpya = {"picha": d.get("picha") or "a new scene", "mazungumzo": []}
        data["matukio"].insert(baada, mpya)
        kiini._panga_upya_picha({i: i + 1 for i in range(len(data["matukio"]) - 1, baada, -1)})
        kiini.hifadhi(data)
        return ok(namba=baada + 1)

    @r.post("/api/hs/tukio/hamisha")
    def tukio_hamisha(d: dict):
        n, mw = int(d["namba"]), int(d["mwelekeo"])
        data, mpya = fomu.hamisha_tukio(kiini.data(), n, mw)
        if mpya != n:
            kiini._panga_upya_picha({n: mpya, mpya: n})
        kiini.hifadhi(data)
        return ok(namba=mpya)

    @r.post("/api/hs/tukio/futa")
    def tukio_futa(d: dict):
        data = kiini.data()
        n = int(d["namba"])
        if len(data["matukio"]) <= 1:
            raise HTTPException(400, "Hadithi lazima iwe na angalau tukio moja.")
        jumla = len(data["matukio"])
        data = fomu.futa_tukio(data, n)
        kiini._panga_upya_picha({n: None, **{i: i - 1 for i in range(n + 1, jumla + 1)}})
        kiini.hifadhi(data)
        return ok()

    # --------------------------------------------------------------- chat & key
    @r.post("/api/hs/chat")
    def chat(d: dict):
        if not (d.get("ujumbe") or "").strip():
            raise HTTPException(400, "Andika ujumbe.")
        return kiini.chat(d["ujumbe"].strip())

    @r.post("/api/hs/chat/futa")
    def chat_futa():
        kiini.hifadhi_historia([{"role": "assistant", "content": KARIBU}])
        return ok()

    @r.post("/api/hs/key")
    def key(d: dict):
        kiini.api_key = (d.get("api_key") or "").strip()
        return ok(gemini=bool(kiini.api_key))

    # --------------------------------------------------------------- sauti & muziki
    @r.post("/api/hs/sauti/jaribu")
    def sauti_jaribu(d: dict):
        sauti = d.get("sauti", "rehema")
        f = kiini.folda / f"jaribio_{slug(sauti)}.mp3"
        try:
            jaribu_sauti(d.get("maneno") or "Habari! Karibu kwenye hadithi yetu.", sauti,
                         f"{int(d.get('kasi', 0)):+d}%", f"{int(d.get('kina', 0)):+d}Hz", str(f), kiini.injini_ya_sauti)
        except Exception as e:  # noqa: BLE001
            raise HTTPException(500, f"Sauti imeshindikana: {e}") from e
        return ok(url=kiini.url(f))

    @r.post("/api/hs/muziki")
    async def muziki(faili: UploadFile = File(...)):
        ext = Path(faili.filename or "muziki.mp3").suffix.lower() or ".mp3"
        if ext not in (".mp3", ".wav", ".m4a", ".ogg", ".aac"):
            raise HTTPException(400, "Pakia faili la sauti (mp3, wav, m4a, ogg).")
        jina = f"muziki{ext}"
        (kiini.folda / jina).write_bytes(await faili.read())
        data = kiini.data()
        data.setdefault("mipangilio", {})["muziki"] = jina
        kiini.hifadhi(data)
        return ok()

    @r.post("/api/hs/muziki/ondoa")
    def muziki_ondoa():
        data = kiini.data()
        (data.get("mipangilio") or {}).pop("muziki", None)
        kiini.hifadhi(data)
        return ok()

    # --------------------------------------------------------------- picha
    def _faili_la_lengo(lengo: str, id_: str) -> Path:
        if lengo == "mhusika":
            return kiini.folda / "wahusika" / f"{slug(id_)}.png"
        return kiini.folda / "matukio" / f"tukio{int(id_):03d}.png"

    @r.post("/api/hs/kazi/chora")
    def kazi_chora(d: dict):
        upya_w = tuple(d.get("upya_wahusika") or ())
        upya_m = tuple(int(x) for x in d.get("upya_matukio") or ())
        aina = d.get("aina", "yote")

        def fanya():
            s = kiini.studio()
            s.wahusika(chora_upya=upya_w)
            if aina != "wahusika":
                s.matukio(chora_upya=upya_m)
            return {}

        return kiini.anzisha("chora", fanya).json()

    @r.post("/api/hs/kazi/hariri")
    def kazi_hariri(d: dict):
        lengo, id_, agizo = d.get("lengo"), str(d.get("id")), (d.get("agizo") or "").strip()
        if not agizo:
            raise HTTPException(400, "Andika unachotaka kibadilike kwenye picha.")
        faili = _faili_la_lengo(lengo, id_)
        if not faili.exists():
            raise HTTPException(400, "Chora picha kwanza, kisha uihariri.")

        def fanya():
            s = kiini.studio()
            h = s.hadithi
            if lengo == "mhusika":
                m = h.wahusika[slug(id_)]
                asili, kumb = m.maelezo, None
            else:
                t = h.matukio[int(id_) - 1]
                asili = ", ".join([t.picha, *(h.wahusika[w].maelezo for w in t.wahusika)])
                kumb = [Image.open(kiini.folda / "wahusika" / f"{w}.png").convert("RGB")
                        for w in t.wahusika if (kiini.folda / "wahusika" / f"{w}.png").exists()] or None
            mchoraji = s.mchoraji if s.injini_ya_picha == "sdxl" and kiini._ina_gpu() else None
            njia = hariri_picha(faili, agizo, api_key=kiini.api_key, mtindo=h.mtindo, maelezo_ya_asili=asili,
                                mchoraji=mchoraji, injini=s.injini_ya_picha, mbegu=int(time.time()) % 100000,
                                kumbukumbu=kumb)
            return {"njia": njia}

        return kiini.anzisha("hariri", fanya).json()

    @r.post("/api/hs/pakia")
    async def pakia(lengo: str = Form(...), id: str = Form(...), geuza: str = Form("hapana"),
                    faili: UploadFile = File(...)):
        data_ya_picha = await faili.read()
        try:
            img = Image.open(io.BytesIO(data_ya_picha)).convert("RGB")
        except Exception as e:  # noqa: BLE001
            raise HTTPException(400, "Faili si picha.") from e
        lengwa = _faili_la_lengo(lengo, id)
        lengwa.parent.mkdir(parents=True, exist_ok=True)
        if geuza != "ndiyo":
            if lengo == "tukio":
                upana, urefu = kutoka_data(kiini.data()).picha_size
                img = ImageOps.fit(img, (upana, urefu))
            weka_picha_mpya(lengwa, img)
            lengwa.with_suffix(".json").unlink(missing_ok=True)  # picha yako: isichorwe upya yenyewe
            return ok()
        halisi = kiini.folda / "vipakiwa" / f"{lengo}_{slug(id)}.png"
        halisi.parent.mkdir(exist_ok=True)
        img.save(halisi)

        def fanya():
            s = kiini.studio()
            m = s.hadithi.wahusika.get(slug(id))
            mchoraji = s.mchoraji if s.injini_ya_picha == "sdxl" and kiini._ina_gpu() else None
            njia = katuni_kutoka_picha(halisi, lengwa, api_key=kiini.api_key, mtindo=s.hadithi.mtindo,
                                       maelezo=m.maelezo if m else "", mchoraji=mchoraji, injini=s.injini_ya_picha)
            lengwa.with_suffix(".json").unlink(missing_ok=True)
            return {"njia": njia}

        return kiini.anzisha("katuni", fanya).json()

    @r.post("/api/hs/rudisha")
    def rudisha(d: dict):
        if not rudisha_toleo(_faili_la_lengo(d.get("lengo"), str(d.get("id")))):
            raise HTTPException(400, "Hakuna toleo la awali.")
        return ok()

    # --------------------------------------------------------------- video
    @r.post("/api/hs/kazi/video")
    def kazi_video(d: dict):
        kichwa, manukuu = bool(d.get("kichwa", True)), bool(d.get("manukuu", True))

        def fanya():
            v = kiini.studio().video(kadi_ya_kichwa=kichwa, manukuu=manukuu)
            return {"url": kiini.url(v)}

        return kiini.anzisha("video", fanya).json()

    @r.get("/api/hs/kazi/{id_}")
    def kazi(id_: str):
        k = kiini.kazi.get(id_)
        if not k:
            raise HTTPException(404, "Kazi haipo.")
        nafasi = sum(1 for x in kiini.kazi.values() if x.hali == "inasubiri" and x.mwanzo < k.mwanzo)
        return {**k.json(), "foleni": nafasi}

    # --------------------------------------------------------------- faili
    @r.get("/api/hs/faili/{mradi}/{njia:path}")
    def faili(mradi: str, njia: str):
        msingi = (kiini.mzizi / slug(mradi)).resolve()
        p = (msingi / njia).resolve()
        if msingi not in p.parents or not p.is_file():
            raise HTTPException(404)
        return FileResponse(p)

    @r.get("/api/hs/pakua/hadithi")
    def pakua_hadithi():
        return FileResponse(kiini.faili, filename=f"{kiini.mradi}.yaml", media_type="text/yaml")

    return r


def tengeneza_router_wazi(kiini: Kiini) -> APIRouter:
    """Njia zisizohitaji kuingia: ping (kwa ukaguzi wa uhai) na usajili wa injini (unalindwa kwa siri)."""
    r = APIRouter()

    @r.get("/api/hs/ping")
    def ping():
        return {"sawa": True, "gpu": kiini._ina_gpu(), "picha": kiini.injini_ya_picha}

    @r.post("/api/hs/injini/sajili")
    def sajili(d: dict):
        siri = os.environ.get("APP_PASSWORD", "")
        if not siri or d.get("siri") != siri:
            raise HTTPException(403, "Siri si sahihi.")
        url = str(d.get("url") or "")
        if not re.match(r"^https://[\w.-]+(:\d+)?(/.*)?$", url):
            raise HTTPException(400, "Anwani si sahihi.")
        kiini.sajili_injini(url)
        print(f"⚡ Injini ya GPU imejisajili: {url}")
        return {"sawa": True}

    return r


def weka_kwenye(app, kiini: Kiini) -> None:
    """Ongeza njia za Studio Pro mbele ya njia za Gradio kwenye app inayoendeshwa."""
    idadi = len(app.router.routes)
    app.include_router(tengeneza_router_wazi(kiini))
    app.include_router(tengeneza_router(kiini))
    mpya = app.router.routes[idadi:]
    del app.router.routes[idadi:]
    app.router.routes[:0] = mpya
