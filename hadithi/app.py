"""Ukurasa wa wavuti wa Hadithi Studio: Chat ya kuandika hadithi + Fomu + Picha na Video.

Kwenye Colab:   from hadithi.app import zindua; zindua(FOLDA, api_key=GEMINI_KEY)
Kwenye terminal: python -m hadithi.app --folda matokeo --picha mfano --sauti kimya
"""
from __future__ import annotations

import argparse
import functools
import os
import threading
import traceback
from pathlib import Path

import gradio as gr

from . import fomu
from .chat import KosaLaAI, Mwandishi, ondoa_yaml, toa_yaml
from .pipeline import Studio
from .story import MSIMULIZI, KosaLaHadithi, kutoka_data
from .voices import jaribu_sauti

MPYA = "__mpya__"

KARIBU = """👋 **Karibu!** Niambie wazo la hadithi yako, nami nitakuandikia hadithi kamili yenye wahusika, matukio na mazungumzo.

Mfano: *"Niandikie hadithi ya mtoto anayeitwa Juma anayeokoa mti wa zamani wa kijiji. Iwe ya katuni, kwa ajili ya TikTok."*

Baadaye unaweza kuniambia nibadilishe chochote, kwa mfano *"ongeza tukio la mvua"* au *"Bibi aongee kwa upole zaidi"*."""

CSS = """
.gradio-container {max-width: 1100px !important}
#kichwa h1 {margin-bottom: 0}
footer {display: none !important}
"""


def _hakiki(data: dict) -> str | None:
    """Rudisha ujumbe wa kosa ikiwa hadithi si sahihi."""
    try:
        kutoka_data(data)
        return None
    except (KosaLaHadithi, TypeError, ValueError) as e:
        return str(e)


class Programu:
    def __init__(self, folda: str | Path, api_key: str | None = None, picha: str = "sdxl", sauti: str = "edge"):
        self.folda = Path(folda)
        self.folda.mkdir(parents=True, exist_ok=True)
        self.faili = self.folda / "hadithi.yaml"
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY", "")
        self.injini_ya_picha = picha
        self.injini_ya_sauti = sauti
        self._studio: Studio | None = None
        self._kufuli = threading.Lock()  # kazi moja nzito (GPU) kwa wakati mmoja
        self._mwandishi: Mwandishi | None = None

    # ---------- hifadhi ----------
    def pakia(self) -> dict:
        if self.faili.exists():
            try:
                return fomu.kutoka_yaml(self.faili.read_text(encoding="utf-8"))
            except Exception:  # noqa: BLE001
                pass
        return fomu.hadithi_tupu()

    def hifadhi(self, data: dict) -> None:
        self.faili.write_text(fomu.kwa_yaml(data), encoding="utf-8")

    def studio(self, data: dict) -> Studio:
        self.hifadhi(data)
        kosa = _hakiki(data)
        if kosa:
            raise gr.Error(f"Hadithi ina kosa: {kosa}")
        if self._studio is None:
            self._studio = Studio(self.faili, self.folda, self.injini_ya_picha, self.injini_ya_sauti)
        else:
            self._studio.pakia_upya()
        return self._studio

    # ---------- fomu ----------
    def sehemu_za_fomu(self, data: dict, mhusika: str | None = None, tukio: int | None = None) -> tuple:
        """Thamani za sehemu zote za fomu kutoka kwenye hadithi."""
        wahusika = data.get("wahusika") or {}
        matukio = data.get("matukio") or []

        chaguo_w = [(("🎙️ Msimulizi" if id_ == MSIMULIZI else f"👤 {(w or {}).get('jina', id_)}"), id_)
                    for id_, w in wahusika.items()] + [("➕ Mhusika mpya", MPYA)]
        if mhusika not in wahusika and mhusika != MPYA:
            mhusika = next((i for i in wahusika if i != MSIMULIZI), MSIMULIZI if MSIMULIZI in wahusika else MPYA)
        w = (wahusika.get(mhusika) or {}) if mhusika != MPYA else {}

        chaguo_t = [(f"Tukio {i}: {str(t.get('picha', ''))[:45]}", i) for i, t in enumerate(matukio, 1)]
        chaguo_t.append(("➕ Tukio jipya", 0))
        if tukio is None or not (0 <= tukio <= len(matukio)):
            tukio = 1 if matukio else 0
        t = matukio[tukio - 1] if tukio else {}
        wanaoweza = [((v or {}).get("jina", k), k) for k, v in wahusika.items() if k != MSIMULIZI]

        return (
            data.get("kichwa", ""),
            data.get("mtindo", ""),
            data.get("ukubwa", "16:9"),
            gr.update(choices=chaguo_w, value=mhusika),
            "Msimulizi" if mhusika == MSIMULIZI else w.get("jina", ""),
            gr.update(value=w.get("maelezo", ""), interactive=mhusika != MSIMULIZI),
            w.get("sauti", "daudi"),
            fomu.thamani_ya_hz(w.get("kina")),
            fomu.thamani_ya_hz(w.get("kasi")),
            gr.update(choices=chaguo_t, value=tukio),
            t.get("picha", ""),
            gr.update(choices=wanaoweza, value=[x for x in t.get("wahusika") or [] if x in wahusika]),
            t.get("mwendo", "auto"),
            bool(t.get("mwendo_ai")),
            fomu.mazungumzo_kwa_maandishi(t.get("mazungumzo") or []),
            fomu.kwa_yaml(data),
        )

    # ---------- chat ----------
    def chat(self, ujumbe: str, historia: list, data: dict, api_key: str):
        ujumbe = (ujumbe or "").strip()
        if not ujumbe:
            return ("", historia, data, *self.sehemu_za_fomu(data))
        key = (api_key or self.api_key or "").strip()
        if not key:
            raise gr.Error("Weka API key ya Gemini kwanza (sehemu ya '🔑 API key' hapa chini).")
        if self._mwandishi is None or key != self.api_key:
            self.api_key = key
            self._mwandishi = Mwandishi(key)
        historia = list(historia or [])
        try:
            jibu = self._mwandishi.jibu(historia, ujumbe, fomu.kwa_yaml(data))
            yaml_mpya = toa_yaml(jibu)
            if yaml_mpya:
                kosa = None
                try:
                    mpya = fomu.kutoka_yaml(yaml_mpya)
                    kosa = _hakiki(mpya)
                except Exception as e:  # noqa: BLE001
                    kosa = str(e)
                if kosa:  # mwombe AI arekebishe mara moja
                    jibu = self._mwandishi.jibu(
                        historia + [{"role": "user", "content": ujumbe}, {"role": "assistant", "content": jibu}],
                        f"Hadithi uliyoandika ina kosa: {kosa}. Tafadhali irekebishe na uiandike yote tena.",
                        fomu.kwa_yaml(data),
                    )
                    yaml_mpya = toa_yaml(jibu)
                    mpya = fomu.kutoka_yaml(yaml_mpya) if yaml_mpya else None
                    kosa = _hakiki(mpya) if mpya else "hakuna hadithi"
                if not kosa:
                    data = mpya
                    self.hifadhi(data)
                else:
                    jibu += f"\n\n⚠️ Hadithi hii ina kosa ({kosa}), hivyo sijaiweka kwenye fomu. Niambie nijaribu tena."
        except gr.Error:
            raise
        except KosaLaAI as e:
            jibu = f"⚠️ {e}"
        except Exception as e:  # noqa: BLE001
            traceback.print_exc()
            jibu = f"⚠️ Samahani, imeshindikana kuwasiliana na AI: {e}"
        historia += [{"role": "user", "content": ujumbe}, {"role": "assistant", "content": ondoa_yaml(jibu)}]
        return ("", historia, data, *self.sehemu_za_fomu(data))

    # ---------- picha na video ----------
    def galeria_ya_wahusika(self, data: dict, picha: dict) -> list:
        w = data.get("wahusika") or {}
        return [(str(p), (w.get(id_) or {}).get("jina", id_)) for id_, p in picha.items()]

    def galeria_ya_matukio(self, data: dict, picha: dict) -> list:
        m = data.get("matukio") or []
        return [(str(p), f"Tukio {n}: {str(m[n - 1].get('picha', ''))[:60]}") for n, p in picha.items() if n <= len(m)]


def _namba(maandishi: str) -> tuple[int, ...]:
    return tuple(int(x) for x in str(maandishi or "").replace(" ", "").split(",") if x.isdigit())


def jenga(prog: Programu) -> gr.Blocks:
    data0 = prog.pakia()
    prog.hifadhi(data0)

    with gr.Blocks(title="Hadithi Studio", theme=gr.themes.Soft(primary_hue="orange"), css=CSS) as app:
        data = gr.State(data0)
        gr.Markdown("# 🎬 Hadithi Studio\nTengeneza video za masimulizi, tamthiliya na katuni kwa AI, bure.",
                    elem_id="kichwa")

        # ===== 1. CHAT =====
        with gr.Tab("💬 Chat"):
            chatbot = gr.Chatbot(value=[{"role": "assistant", "content": KARIBU}], type="messages", height=460,
                                 show_label=False, show_copy_button=True)
            with gr.Row():
                ujumbe = gr.Textbox(placeholder="Andika hapa... (mfano: Niandikie hadithi ya sungura mjanja)",
                                    show_label=False, lines=2, scale=5)
                tuma = gr.Button("Tuma ➤", variant="primary", scale=1)
            with gr.Row():
                anza_upya = gr.Button("🗑️ Anza mazungumzo upya", size="sm")
            with gr.Accordion("🔑 API key ya Gemini (bure)", open=not prog.api_key):
                gr.Markdown("Chat inatumia Google Gemini, ambayo ni bure. Pata key yako hapa: "
                            "[aistudio.google.com/apikey](https://aistudio.google.com/apikey). "
                            "Bonyeza **Create API key**, nakili, kisha bandika hapa.")
                # key iliyowekwa kwenye seva haitumwi kwenye browser
                api_key = gr.Textbox(type="password", show_label=False,
                                     placeholder="✅ Key imeshawekwa" if prog.api_key else "AIza...")

        # ===== 2. FOMU =====
        with gr.Tab("📝 Hadithi"):
            with gr.Group():
                kichwa = gr.Textbox(label="Kichwa cha hadithi")
                with gr.Row():
                    chagua_mtindo = gr.Dropdown(list(fomu.MITINDO), label="Chagua mtindo wa picha", value=None, scale=1)
                    ukubwa = gr.Radio([("YouTube 16:9", "16:9"), ("TikTok 9:16", "9:16"), ("Instagram 1:1", "1:1")],
                                      label="Ukubwa wa video", scale=1)
                mtindo = gr.Textbox(label="Mtindo (kwa Kiingereza)", lines=2)
                hifadhi_msingi = gr.Button("💾 Hifadhi", size="sm")

            gr.Markdown("### 👥 Wahusika")
            with gr.Group():
                chagua_mhusika = gr.Dropdown(label="Chagua mhusika", interactive=True)
                with gr.Row():
                    jina = gr.Textbox(label="Jina", scale=1)
                    sauti = gr.Dropdown([("Daudi (mwanamume TZ)", "daudi"), ("Rafiki (mwanamume KE)", "rafiki"),
                                         ("Rehema (mwanamke TZ)", "rehema"), ("Zuri (mwanamke KE)", "zuri")],
                                        label="Sauti", scale=1)
                maelezo = gr.Textbox(label="Sura yake (kwa Kiingereza)", lines=2,
                                     placeholder="a 9 year old girl, braided hair, yellow dress")
                with gr.Row():
                    kina = gr.Slider(-40, 40, step=5, label="Kina cha sauti (+ = mtoto, − = mzee)")
                    kasi = gr.Slider(-40, 40, step=5, label="Kasi ya kuongea (%)")
                with gr.Row():
                    hifadhi_mhusika = gr.Button("💾 Hifadhi mhusika", variant="primary", size="sm")
                    sikiliza = gr.Button("🔊 Sikiliza sauti", size="sm")
                    futa_mhusika = gr.Button("🗑️ Futa", size="sm", variant="stop")
                sauti_ya_jaribio = gr.Audio(label="Sauti", visible=False, autoplay=True)

            gr.Markdown("### 🎞️ Matukio")
            with gr.Group():
                chagua_tukio = gr.Dropdown(label="Chagua tukio", interactive=True)
                picha = gr.Textbox(label="Picha ya tukio (kwa Kiingereza): mahali, kitendo, hisia", lines=2)
                with gr.Row():
                    wahusika_tukio = gr.CheckboxGroup(label="Wanaoonekana kwenye picha", scale=3)
                    mwendo = gr.Dropdown([("Otomatiki", "auto"), ("Karibia (zoom in)", "karibia"),
                                          ("Mbali (zoom out)", "mbali"), ("Kulia ➡️", "kulia"),
                                          ("Kushoto ⬅️", "kushoto"), ("Tuli", "tuli")],
                                         label="Mwendo wa kamera", scale=1)
                mwendo_ai = gr.Checkbox(
                    label="🎥 Mwendo wa AI: wahusika na mazingira wasogee kweli",
                    info="Inafaa kwa matukio ya vitendo (kukimbia, kucheza, sherehe). Inahitaji GPU, na "
                         "huchukua dakika 3 hadi 6 kwa kila tukio. Matukio mengine hupata mwendo wa kina (2.5D).")
                mazungumzo = gr.Textbox(
                    label="Mazungumzo", lines=5,
                    info="Kila sentensi kwenye mstari wake. 'neema: Habari!' maana yake Neema anaongea. "
                         "Mstari usio na jina ni wa msimulizi.")
                with gr.Row():
                    hifadhi_tukio = gr.Button("💾 Hifadhi tukio", variant="primary", size="sm")
                    juu = gr.Button("⬆️ Juu", size="sm")
                    chini = gr.Button("⬇️ Chini", size="sm")
                    futa_tukio = gr.Button("🗑️ Futa", size="sm", variant="stop")

            with gr.Accordion("🧑‍💻 Hadithi kamili (YAML), kwa wataalamu", open=False):
                yaml_kamili = gr.Code(language="yaml", show_label=False)
                tumia_yaml = gr.Button("✅ Tumia YAML hii", size="sm")

            gr.Markdown("#### 💾 Nakala ya hadithi\nPakua nakala ya hadithi yako ili uweze kuendelea nayo baadaye, "
                        "hata kwenye Colab.")
            with gr.Row():
                pakua_hadithi = gr.DownloadButton("📤 Pakua hadithi", value=str(prog.faili), size="sm")
                pakia_hadithi = gr.UploadButton("📥 Fungua hadithi (.yaml)", file_types=[".yaml", ".yml", ".txt"],
                                                size="sm")

        # ===== 3. PICHA & VIDEO =====
        with gr.Tab("🎬 Video"):
            if prog.injini_ya_picha == "sdxl":
                gr.Markdown("Fanya hatua hizi kwa mpangilio. Mara ya kwanza, modeli ya AI hupakiwa kwa dakika 3 hadi 5. "
                            "Baada ya hapo, kila picha huchukua sekunde chache.")
            else:
                gr.Markdown("Fanya hatua hizi kwa mpangilio. Kila picha huchukua sekunde 10 hadi 60. "
                            "💡 Kwa sura za wahusika zinazofanana zaidi, tumia toleo la Colab.")
            with gr.Group():
                gr.Markdown("#### 👥 Hatua A: Wahusika")
                chora_w = gr.Button("🎨 Chora wahusika", variant="primary")
                gal_w = gr.Gallery(label="Wahusika", columns=4, height="auto", object_fit="contain")
                with gr.Row():
                    upya_w = gr.Dropdown(label="Hupendi mhusika? Mchague uchore upya", scale=3)
                    chora_upya_w = gr.Button("🔁 Chora upya", scale=1)
            with gr.Group():
                gr.Markdown("#### 🖼️ Hatua B: Matukio")
                chora_m = gr.Button("🎨 Chora matukio yote", variant="primary")
                gal_m = gr.Gallery(label="Matukio", columns=3, height="auto", object_fit="contain")
                with gr.Row():
                    upya_m = gr.Textbox(label="Namba za matukio ya kuchora upya (mfano: 2, 5)", scale=3)
                    chora_upya_m = gr.Button("🔁 Chora upya", scale=1)
            with gr.Group():
                gr.Markdown("#### 🎬 Hatua C: Video")
                with gr.Row():
                    kadi = gr.Checkbox(value=True, label="Weka kichwa cha hadithi mwanzoni")
                    manukuu = gr.Checkbox(value=True, label="Onyesha maneno (manukuu) kwenye video")
                gr.Markdown("🎥 Matukio uliyowekea **Mwendo wa AI** huchukua dakika 3 hadi 6 kila moja.")
                tengeneza = gr.Button("🎬 Tengeneza video", variant="primary", size="lg")
                video = gr.Video(label="Video yako")
                pakua = gr.File(label="⬇️ Pakua video")

        FOMU = [kichwa, mtindo, ukubwa, chagua_mhusika, jina, maelezo, sauti, kina, kasi,
                chagua_tukio, picha, wahusika_tukio, mwendo, mwendo_ai, mazungumzo, yaml_kamili]

        def onyesha(d, mh=None, tk=None):
            return (d, *prog.sehemu_za_fomu(d, mh, tk))

        def chaguo_za_upya_w(d):
            w = d.get("wahusika") or {}
            return gr.update(choices=[((v or {}).get("jina", k), k) for k, v in w.items()
                                      if (v or {}).get("maelezo")], value=None)

        # --- chat ---
        for tukio_la_kutuma in (tuma.click, ujumbe.submit):
            tukio_la_kutuma(prog.chat, [ujumbe, chatbot, data, api_key], [ujumbe, chatbot, data, *FOMU])
        anza_upya.click(lambda: [{"role": "assistant", "content": KARIBU}], None, chatbot)

        # --- msingi ---
        chagua_mtindo.change(lambda k: fomu.MITINDO.get(k, gr.update()), chagua_mtindo, mtindo)

        def hifadhi_msingi_fn(d, k, m, u):
            d = {**d, "kichwa": k.strip() or "Hadithi Yangu", "mtindo": m.strip(), "ukubwa": u}
            prog.hifadhi(d)
            gr.Info("Imehifadhiwa ✅")
            return onyesha(d)

        hifadhi_msingi.click(hifadhi_msingi_fn, [data, kichwa, mtindo, ukubwa], [data, *FOMU])

        # --- wahusika ---
        def chagua_mhusika_fn(d, mh, tk):
            return prog.sehemu_za_fomu(d, mh, tk)[3:9]

        chagua_mhusika.input(chagua_mhusika_fn, [data, chagua_mhusika, chagua_tukio], FOMU[3:9])

        def hifadhi_mhusika_fn(d, mh, j, ma, s, ki, ka, tk):
            if mh != MSIMULIZI and not j.strip():
                raise gr.Error("Andika jina la mhusika.")
            d, id_ = fomu.weka_mhusika(d, None if mh == MPYA else mh, j, ma, s, ki, ka)
            prog.hifadhi(d)
            gr.Info(f"{j or 'Msimulizi'} amehifadhiwa ✅")
            return onyesha(d, id_, tk)

        hifadhi_mhusika.click(hifadhi_mhusika_fn,
                              [data, chagua_mhusika, jina, maelezo, sauti, kina, kasi, chagua_tukio], [data, *FOMU])

        def futa_mhusika_fn(d, mh, tk):
            if mh in (MSIMULIZI, MPYA):
                raise gr.Error("Msimulizi hawezi kufutwa.")
            d = fomu.futa_mhusika(d, mh)
            prog.hifadhi(d)
            return onyesha(d, None, tk)

        futa_mhusika.click(futa_mhusika_fn, [data, chagua_mhusika, chagua_tukio], [data, *FOMU])

        def sikiliza_fn(j, s, ki, ka):
            maneno = f"Habari! Jina langu ni {j}. Karibu kwenye hadithi yetu." if j and j != "Msimulizi" \
                else "Hapo zamani za kale, palikuwa na kijiji kimoja kizuri."
            try:
                f = jaribu_sauti(maneno, s, f"{int(ka):+d}%", f"{int(ki):+d}Hz",
                                 str(prog.folda / "jaribio.mp3"), prog.injini_ya_sauti)
            except Exception as e:  # noqa: BLE001
                raise gr.Error(f"Sauti imeshindikana: {e}") from e
            return gr.update(value=f, visible=True)

        sikiliza.click(sikiliza_fn, [jina, sauti, kina, kasi], sauti_ya_jaribio)

        # --- matukio ---
        def chagua_tukio_fn(d, mh, tk):
            return prog.sehemu_za_fomu(d, mh, tk)[9:15]

        chagua_tukio.input(chagua_tukio_fn, [data, chagua_mhusika, chagua_tukio], FOMU[9:15])

        def hifadhi_tukio_fn(d, mh, tk, pi, wa, mw, mai, mz):
            if not pi.strip():
                raise gr.Error("Eleza picha ya tukio.")
            d, n = fomu.weka_tukio(d, tk or None, pi, wa, mw, mz, mwendo_ai=mai)
            prog.hifadhi(d)
            gr.Info(f"Tukio {n} limehifadhiwa ✅")
            return onyesha(d, mh, n)

        hifadhi_tukio.click(hifadhi_tukio_fn,
                            [data, chagua_mhusika, chagua_tukio, picha, wahusika_tukio, mwendo, mwendo_ai,
                             mazungumzo],
                            [data, *FOMU])

        def hamisha_fn(mwelekeo):
            def fn(d, mh, tk):
                d, n = fomu.hamisha_tukio(d, tk or 0, mwelekeo)
                prog.hifadhi(d)
                return onyesha(d, mh, n)
            return fn

        juu.click(hamisha_fn(-1), [data, chagua_mhusika, chagua_tukio], [data, *FOMU])
        chini.click(hamisha_fn(+1), [data, chagua_mhusika, chagua_tukio], [data, *FOMU])

        def futa_tukio_fn(d, mh, tk):
            if not tk:
                raise gr.Error("Chagua tukio la kufuta.")
            d = fomu.futa_tukio(d, tk)
            prog.hifadhi(d)
            return onyesha(d, mh, max(1, tk - 1))

        futa_tukio.click(futa_tukio_fn, [data, chagua_mhusika, chagua_tukio], [data, *FOMU])

        def tumia_yaml_fn(d, maandishi, mh, tk):
            try:
                mpya = fomu.kutoka_yaml(maandishi)
            except Exception as e:  # noqa: BLE001
                raise gr.Error(f"YAML ina kosa: {e}") from e
            kosa = _hakiki(mpya)
            if kosa:
                raise gr.Error(f"Hadithi ina kosa: {kosa}")
            prog.hifadhi(mpya)
            gr.Info("Imehifadhiwa ✅")
            return onyesha(mpya, mh, tk)

        tumia_yaml.click(tumia_yaml_fn, [data, yaml_kamili, chagua_mhusika, chagua_tukio], [data, *FOMU])

        def pakia_hadithi_fn(d, faili, mh, tk):
            try:
                maandishi = Path(faili if isinstance(faili, str) else faili.name).read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError) as e:
                raise gr.Error(f"Faili halisomeki: {e}") from e
            return tumia_yaml_fn(d, maandishi, mh, tk)

        pakia_hadithi.upload(pakia_hadithi_fn, [data, pakia_hadithi, chagua_mhusika, chagua_tukio], [data, *FOMU])

        # --- picha na video ---
        def kazi_nzito(fn):
            """Kazi za picha/video: moja kwa wakati, na kosa lionekane kwa lugha rahisi."""
            @functools.wraps(fn)
            def ndani(*a):
                with prog._kufuli:
                    try:
                        return fn(*a)
                    except gr.Error:
                        raise
                    except Exception as e:  # noqa: BLE001
                        traceback.print_exc()
                        raise gr.Error(f"Imeshindikana: {type(e).__name__}: {str(e)[:300]}") from e
            return ndani

        nzito = {"concurrency_id": "kazi_nzito", "concurrency_limit": 1}

        @kazi_nzito
        def chora_w_fn(d, upya=None):
            s = prog.studio(d)
            p = s.wahusika(chora_upya=(upya,) if upya else ())
            return prog.galeria_ya_wahusika(d, p), chaguo_za_upya_w(d)

        chora_w.click(chora_w_fn, data, [gal_w, upya_w], **nzito)
        chora_upya_w.click(lambda d, u: chora_w_fn(d, u) if u else (gr.update(), gr.update()),
                           [data, upya_w], [gal_w, upya_w], **nzito)

        @kazi_nzito
        def chora_m_fn(d, namba=""):
            s = prog.studio(d)
            p = s.matukio(chora_upya=_namba(namba))
            return prog.galeria_ya_wahusika(d, s.wahusika()), prog.galeria_ya_matukio(d, p)

        chora_m.click(chora_m_fn, data, [gal_w, gal_m], **nzito)
        chora_upya_m.click(chora_m_fn, [data, upya_m], [gal_w, gal_m], **nzito)

        @kazi_nzito
        def tengeneza_fn(d, k, mk):
            s = prog.studio(d)
            v = s.video(kadi_ya_kichwa=k, manukuu=mk)
            return (str(v), str(v), prog.galeria_ya_matukio(d, s.matukio()))

        tengeneza.click(tengeneza_fn, [data, kadi, manukuu], [video, pakua, gal_m], **nzito)

        app.load(lambda d: (*prog.sehemu_za_fomu(d), chaguo_za_upya_w(d)), data, [*FOMU, upya_w])
    return app


def _kiungo(url: str) -> None:
    """Onyesha kitufe kikubwa cha kufungua Studio (Colab/Jupyter), au andika link tu."""
    print(f"\n🎬 Hadithi Studio Pro: {url}\n")
    try:
        from IPython.display import HTML, display

        display(HTML(
            f'<a href="{url}" target="_blank" style="display:inline-block;padding:14px 22px;border-radius:12px;'
            'background:linear-gradient(135deg,#ff6a3d,#ffc14d);color:#1a0f05;font:700 17px sans-serif;'
            f'text-decoration:none">🎬 Fungua Hadithi Studio →</a><p style="font:14px sans-serif">{url}</p>'))
    except Exception:  # noqa: BLE001
        pass


def zindua(folda: str | Path = "matokeo", api_key: str | None = None, picha: str = "sdxl", sauti: str = "edge",
           share: bool = True, ukurasa: str = "studio", **kwargs):
    """Fungua ukurasa. Kwenye Colab, link ya umma (…gradio.live) itaonekana; ifungue hata kwenye simu.

    ukurasa="studio": ukurasa wa kitaalamu (/studio) wenye miradi mingi, storyboard na kuhariri picha.
    ukurasa="rahisi": ukurasa wa awali wa Gradio.
    """
    if ukurasa != "studio":
        prog = Programu(folda, api_key, picha, sauti)
        app = jenga(prog)
        app.queue(default_concurrency_limit=1)
        return app.launch(share=share, allowed_paths=[str(Path(folda).resolve())], **kwargs)

    from .seva import Kiini, weka_kwenye

    folda = Path(folda)
    kiini = Kiini(folda.parent, folda.name, api_key or os.environ.get("GEMINI_API_KEY", ""), picha, sauti)
    with gr.Blocks(title="Hadithi Studio", theme=gr.themes.Soft(primary_hue="orange"), css=CSS) as kizinduzi:
        gr.HTML('<div style="text-align:center;padding:60px 20px;font-family:sans-serif">'
                '<div style="font-size:48px">🎬</div><h1>Hadithi Studio</h1>'
                '<p>Ukurasa wa Studio uko hapa:</p>'
                '<a href="/studio" style="display:inline-block;padding:14px 26px;border-radius:12px;'
                'background:linear-gradient(135deg,#ff6a3d,#ffc14d);color:#1a0f05;font-weight:700;'
                'text-decoration:none;font-size:18px">Fungua Studio →</a></div>')
    kuzuia = kwargs.pop("debug", False) or kwargs.pop("block", False)
    kizinduzi.queue()
    _, local, umma = kizinduzi.launch(share=share, prevent_thread_lock=True,
                                      allowed_paths=[str(folda.parent.resolve())], **kwargs)
    weka_kwenye(kizinduzi.app, kiini)
    _kiungo(f"{(umma or local).rstrip('/')}/studio")
    if kuzuia:
        kizinduzi.block_thread()
    return kiini


def main() -> None:
    p = argparse.ArgumentParser(description="Fungua ukurasa wa Hadithi Studio.")
    p.add_argument("--folda", default="matokeo")
    p.add_argument("--picha", choices=["sdxl", "mtandao", "mfano"], default="sdxl")
    p.add_argument("--sauti", choices=["edge", "mms", "kimya"], default="edge")
    p.add_argument("--share", action="store_true", help="tengeneza link ya umma (gradio.live)")
    p.add_argument("--port", type=int, default=7860)
    p.add_argument("--ukurasa", choices=["studio", "rahisi"], default="studio")
    a = p.parse_args()
    zindua(a.folda, picha=a.picha, sauti=a.sauti, share=a.share, server_port=a.port, ukurasa=a.ukurasa, block=True)


if __name__ == "__main__":
    main()
