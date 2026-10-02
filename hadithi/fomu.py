"""Kubadilisha hadithi kati ya YAML na sehemu za fomu (zinazotumiwa na ukurasa wa wavuti)."""
from __future__ import annotations

import copy
import re

import yaml

from .story import MSIMULIZI

MITINDO = {
    "Katuni 2D (kitabu cha hadithi)": "colorful 2D cartoon illustration, children's storybook style, warm colors",
    "Katuni 3D (kama Pixar)": "3D animated movie style, pixar-like, soft cinematic lighting, cute characters",
    "Anime": "anime style, studio ghibli inspired, soft warm colors, detailed background",
    "Uchoraji wa rangi za maji": "watercolor painting illustration, soft textures, gentle colors",
    "Komiki (comic book)": "comic book style, bold outlines, vibrant flat colors",
    "Tamthiliya halisi (sinema)": "cinematic realistic film still, dramatic lighting, shallow depth of field",
}

MIENDO_YA_FOMU = ["auto", "karibia", "mbali", "kulia", "kushoto", "tuli"]
SAUTI_ZA_FOMU = ["daudi", "rafiki", "rehema", "zuri"]


def hadithi_tupu() -> dict:
    return {
        "kichwa": "Hadithi Yangu",
        "mtindo": MITINDO["Katuni 2D (kitabu cha hadithi)"],
        "ukubwa": "16:9",
        "wahusika": {MSIMULIZI: {"sauti": "daudi", "kasi": "-5%"}},
        "matukio": [{"picha": "a beautiful African village at sunrise", "mazungumzo": ["Hapo zamani za kale..."]}],
    }


def kwa_yaml(data: dict) -> str:
    return yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=1000)


def kutoka_yaml(maandishi: str) -> dict:
    data = yaml.safe_load(maandishi) or {}
    if not isinstance(data, dict):
        raise ValueError("Hadithi haina muundo sahihi.")
    data.setdefault("wahusika", {})
    data.setdefault("matukio", [])
    return data


def id_ya_jina(jina: str, zilizopo: set[str] | None = None) -> str:
    """'Bibi Zawadi' -> 'bibi_zawadi' (bila kurudia id iliyopo)."""
    msingi = re.sub(r"[^a-z0-9]+", "_", jina.lower()).strip("_") or "mhusika"
    id_, i = msingi, 2
    while zilizopo and id_ in zilizopo:
        id_, i = f"{msingi}_{i}", i + 1
    return id_


# ---------- mazungumzo: orodha <-> maandishi ya mistari ----------

def mazungumzo_kwa_maandishi(mazungumzo: list) -> str:
    """[ "maneno", {"neema": "habari"} ] -> 'maneno\\nneema: habari'"""
    mistari = []
    for m in mazungumzo or []:
        if isinstance(m, dict) and len(m) == 1:
            msemaji, maneno = next(iter(m.items()))
            mistari.append(str(maneno) if msemaji == MSIMULIZI else f"{msemaji}: {maneno}")
        else:
            mistari.append(str(m))
    return "\n".join(mistari)


def maandishi_kwa_mazungumzo(maandishi: str, wahusika: dict) -> list:
    """Kila mstari ni sentensi moja. 'neema: Habari' = Neema anaongea; mstari bila jina = msimulizi.
    Jina linaweza kuwa id (neema) au jina kamili (Bibi Zawadi)."""
    majina = {}
    for id_, w in wahusika.items():
        majina[id_.lower()] = id_
        if isinstance(w, dict) and w.get("jina"):
            majina[str(w["jina"]).lower()] = id_
    matokeo: list = []
    for mstari in maandishi.splitlines():
        mstari = mstari.strip()
        if not mstari:
            continue
        m = re.match(r"^([^:]{1,40}):\s*(.+)$", mstari)
        if m and m.group(1).strip().lower() in majina:
            id_ = majina[m.group(1).strip().lower()]
            maneno = m.group(2).strip()
            matokeo.append(maneno if id_ == MSIMULIZI else {id_: maneno})
        else:
            matokeo.append(mstari)
    return matokeo


# ---------- kuhariri wahusika na matukio ----------

def weka_mhusika(data: dict, id_: str | None, jina: str, maelezo: str, sauti: str, kina: int, kasi: int) -> tuple[dict, str]:
    """Ongeza (id_=None) au badilisha mhusika. kina: Hz (-40..40), kasi: % (-40..40)."""
    data = copy.deepcopy(data)
    wahusika = data.setdefault("wahusika", {})
    if not id_:
        id_ = id_ya_jina(jina, set(wahusika))
    w = dict(wahusika.get(id_) or {})
    if id_ != MSIMULIZI:
        w["jina"] = jina.strip() or id_
        w["maelezo"] = maelezo.strip()
    w["sauti"] = sauti
    w["kina"] = f"{int(kina):+d}Hz"
    w["kasi"] = f"{int(kasi):+d}%"
    wahusika[id_] = w
    return data, id_


def futa_mhusika(data: dict, id_: str) -> dict:
    """Futa mhusika na mistari yake yote (mistari yake inabaki kama ya msimulizi)."""
    if id_ == MSIMULIZI:
        return data
    data = copy.deepcopy(data)
    data.get("wahusika", {}).pop(id_, None)
    for t in data.get("matukio", []):
        t["wahusika"] = [w for w in t.get("wahusika") or [] if w != id_]
        t["mazungumzo"] = [next(iter(m.values())) if isinstance(m, dict) and id_ in m else m
                           for m in t.get("mazungumzo") or []]
    return data


def weka_tukio(data: dict, namba: int | None, picha: str, wahusika: list[str], mwendo: str, mazungumzo: str) -> tuple[dict, int]:
    """Ongeza (namba=None) au badilisha tukio. namba inaanzia 1."""
    data = copy.deepcopy(data)
    matukio = data.setdefault("matukio", [])
    t = {"picha": picha.strip()}
    if wahusika:
        t["wahusika"] = list(wahusika)
    if mwendo and mwendo != "auto":
        t["mwendo"] = mwendo
    t["mazungumzo"] = maandishi_kwa_mazungumzo(mazungumzo, data.get("wahusika", {}))
    if namba is None or namba > len(matukio):
        matukio.append(t)
        return data, len(matukio)
    zamani = matukio[namba - 1]
    for k in ("picha_faili", "kimya"):
        if k in zamani:
            t[k] = zamani[k]
    matukio[namba - 1] = t
    return data, namba


def futa_tukio(data: dict, namba: int) -> dict:
    data = copy.deepcopy(data)
    if 1 <= namba <= len(data.get("matukio", [])):
        data["matukio"].pop(namba - 1)
    return data


def hamisha_tukio(data: dict, namba: int, mwelekeo: int) -> tuple[dict, int]:
    """Sogeza tukio juu (-1) au chini (+1)."""
    data = copy.deepcopy(data)
    m = data.get("matukio", [])
    mpya = namba + mwelekeo
    if 1 <= namba <= len(m) and 1 <= mpya <= len(m):
        m[namba - 1], m[mpya - 1] = m[mpya - 1], m[namba - 1]
        return data, mpya
    return data, namba


def thamani_ya_hz(maandishi: str | None) -> int:
    try:
        return int(float(re.sub(r"[^0-9.+-]", "", str(maandishi or "0")) or 0))
    except ValueError:
        return 0
