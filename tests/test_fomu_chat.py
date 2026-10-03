import types

import pytest

from hadithi import fomu
from hadithi.chat import Mwandishi, ondoa_yaml, toa_yaml
from hadithi.story import kutoka_data, soma

MFANO = "mifano/siri_ya_kisima.yaml"


def data_ya_mfano():
    return fomu.kutoka_yaml(open(MFANO, encoding="utf-8").read())


def test_mazungumzo_safari_ya_kwenda_na_kurudi():
    d = data_ya_mfano()
    for t in d["matukio"]:
        maandishi = fomu.mazungumzo_kwa_maandishi(t["mazungumzo"])
        assert fomu.maandishi_kwa_mazungumzo(maandishi, d["wahusika"]) == t["mazungumzo"]


def test_maandishi_kwa_mazungumzo_majina_na_nukta_mbili():
    w = {"msimulizi": {}, "bibi": {"jina": "Bibi Zawadi"}}
    m = fomu.maandishi_kwa_mazungumzo(
        "Bibi Zawadi: Karibu!\nbibi: Keti.\nAlisema: hapana\n\nmsimulizi: Mwisho.", w)
    assert m == [{"bibi": "Karibu!"}, {"bibi": "Keti."}, "Alisema: hapana", "Mwisho."]


def test_weka_mhusika_na_tukio_hutoa_hadithi_sahihi():
    d = fomu.hadithi_tupu()
    d, id_ = fomu.weka_mhusika(d, None, "Bibi Zawadi", "an old woman", "zuri", -10, -15)
    assert id_ == "bibi_zawadi"
    assert d["wahusika"][id_]["kina"] == "-10Hz" and d["wahusika"][id_]["kasi"] == "-15%"
    d, n = fomu.weka_tukio(d, None, "an old woman at a well", [id_], "karibia",
                           "Siku moja...\nBibi Zawadi: Habari watoto!")
    assert n == 2
    h = kutoka_data(d)
    assert h.matukio[1].mazungumzo[1].msemaji == id_
    assert h.matukio[1].mwendo == "karibia"


def test_futa_mhusika_huondoa_kila_mahali():
    d = fomu.futa_mhusika(data_ya_mfano(), "neema")
    assert "neema" not in d["wahusika"]
    h = kutoka_data(d)  # bado ni sahihi
    assert all(m.msemaji != "neema" for t in h.matukio for m in t.mazungumzo)


def test_hamisha_na_futa_tukio():
    d = data_ya_mfano()
    kwanza = d["matukio"][0]["picha"]
    d2, n = fomu.hamisha_tukio(d, 1, +1)
    assert n == 2 and d2["matukio"][1]["picha"] == kwanza
    assert fomu.hamisha_tukio(d, 1, -1)[1] == 1
    assert len(fomu.futa_tukio(d, 1)["matukio"]) == len(d["matukio"]) - 1


def test_yaml_ya_fomu_inasomeka_na_story():
    d = data_ya_mfano()
    h = kutoka_data(fomu.kutoka_yaml(fomu.kwa_yaml(d)))
    assert len(h.matukio) == len(soma(MFANO).matukio)


def test_toa_yaml_kutoka_jibu():
    jibu = "Hii hapa!\n```yaml\nkichwa: A\nmatukio:\n  - picha: x\n```\nNimeongeza tukio."
    assert toa_yaml(jibu).startswith("kichwa: A")
    assert toa_yaml("hakuna hadithi hapa") is None
    assert "```" not in ondoa_yaml(jibu)


def test_mwandishi_hubadilisha_modeli_ikiwa_haipo(monkeypatch):
    from google.genai import errors

    simu = []

    class Models:
        def generate_content(self, model, contents, config):
            simu.append(model)
            if model == "gemini-2.5-flash":
                raise errors.ClientError(404, {"error": {"message": "not found", "status": "NOT_FOUND"}})
            assert contents[-1].parts[0].text == "habari"
            assert "HADITHI YA SASA" in config.system_instruction
            return types.SimpleNamespace(text="Sawa!")

        def list(self):
            return [types.SimpleNamespace(name="models/gemini-3.0-flash", supported_actions=["generateContent"]),
                    types.SimpleNamespace(name="models/gemini-3.0-flash-lite", supported_actions=["generateContent"]),
                    types.SimpleNamespace(name="models/embedding", supported_actions=["embedContent"])]

    m = Mwandishi.__new__(Mwandishi)
    m.client = types.SimpleNamespace(models=Models())
    m.modeli, m._akiba = "gemini-2.5-flash", None
    jibu = m.jibu([{"role": "assistant", "content": "Karibu"}], "habari", "kichwa: A")
    assert jibu == "Sawa!" and simu == ["gemini-2.5-flash", "gemini-3.0-flash"]


def test_kosa_la_hadithi_linaeleweka():
    from hadithi.story import KosaLaHadithi
    d = fomu.hadithi_tupu()
    d["matukio"][0]["mazungumzo"] = [{"mgeni": "habari"}]
    with pytest.raises(KosaLaHadithi, match="mgeni"):
        kutoka_data(d)


def test_mwandishi_huruka_modeli_zisizo_na_mgao_wa_bure():
    from google.genai import errors

    from hadithi.chat import KosaLaAI

    simu = []

    def kosa(code, msg):
        return errors.ClientError(code, {"error": {"code": code, "message": msg, "status": "X"}})

    class Models:
        def __init__(self, zote_zimeisha=False):
            self.zote = zote_zimeisha

        def generate_content(self, model, contents, config):
            simu.append(model)
            if self.zote or model in ("gemini-2.5-flash", "gemini-3.0-flash"):
                raise kosa(429, "Quota exceeded ... limit: 0")
            return types.SimpleNamespace(text="Habari!")

        def list(self):
            return [types.SimpleNamespace(name=f"models/{n}", supported_actions=["generateContent"])
                    for n in ["gemini-omni-flash", "gemini-3.0-flash", "gemini-2.0-flash-lite",
                              "gemini-flash-latest", "gemini-3.0-pro", "gemini-2.5-flash-image"]]

    m = Mwandishi.__new__(Mwandishi)
    m.client = types.SimpleNamespace(models=Models())
    m.modeli, m._akiba = "gemini-2.5-flash", None
    assert m.jibu([], "habari") == "Habari!"
    assert simu == ["gemini-2.5-flash", "gemini-3.0-flash", "gemini-flash-latest"]
    assert m.modeli == "gemini-flash-latest"

    m.client = types.SimpleNamespace(models=Models(zote_zimeisha=True))
    m.modeli, m._akiba = "gemini-2.5-flash", None
    with pytest.raises(KosaLaAI, match="Mgao wa bure"):
        m.jibu([], "habari")


def test_mwendo_ai_kwenye_fomu():
    d = fomu.hadithi_tupu()
    d, n = fomu.weka_tukio(d, None, "children dancing", [], "auto", "Walicheza!", mwendo_ai=True)
    assert d["matukio"][n - 1]["mwendo_ai"] is True
    assert kutoka_data(d).matukio[n - 1].mwendo_ai is True
    d, n = fomu.weka_tukio(d, n, "children dancing", [], "auto", "Walicheza!")
    assert "mwendo_ai" not in d["matukio"][n - 1]
