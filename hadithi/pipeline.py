"""Hatua zote kwa mpangilio: wahusika → matukio → sauti → video."""
from __future__ import annotations

import gc
import random
from pathlib import Path

from .images import Mchoraji, MchorajiWaMtandao, tengeneza_matukio, tengeneza_picha_za_shots, tengeneza_wahusika
from .mwendo import MwendoWaAI, alama_ya_klipu, klipu_ya_mfano
from .story import Hadithi, soma
from .video import muda_wa_tukio, tengeneza_video
from .voices import tengeneza_sauti


class Studio:
    """Mfano:

        studio = Studio("hadithi_yangu.yaml", "matokeo")
        studio.wahusika()   # angalia picha za wahusika; badilisha ukipenda
        studio.matukio()    # angalia picha za matukio
        studio.video()      # sauti + video ya mwisho
    """

    def __init__(self, faili_la_hadithi: str | Path, folda: str | Path = "matokeo",
                 picha: str = "sdxl", sauti: str = "edge"):
        self.faili = Path(faili_la_hadithi)
        self.folda = Path(folda)
        self.injini_ya_picha = picha
        self.injini_ya_sauti = sauti
        self._mchoraji: Mchoraji | None = None
        self._mpiga = None  # modeli ya filamu (LTX/Wan), hupakiwa ikihitajika tu
        self.hadithi: Hadithi = soma(self.faili)
        print(f"📖 '{self.hadithi.kichwa}': matukio {len(self.hadithi.matukio)}, "
              f"wahusika {len(self.hadithi.wahusika)}")

    def badilisha_mradi(self, faili_la_hadithi: str | Path, folda: str | Path) -> Hadithi:
        """Hamia hadithi nyingine bila kupakia modeli upya (modeli hubaki kwenye GPU)."""
        self.faili, self.folda = Path(faili_la_hadithi), Path(folda)
        return self.pakia_upya()

    def pakia_upya(self) -> Hadithi:
        """Soma tena faili la hadithi baada ya kulibadilisha."""
        self.hadithi = soma(self.faili)
        return self.hadithi

    @property
    def mchoraji(self) -> Mchoraji | MchorajiWaMtandao | None:
        if self.injini_ya_picha == "mfano":
            return None
        if self._mchoraji is None:
            self.funga_filamu()  # GPU moja: modeli ya filamu itoke kwanza
            aina = MchorajiWaMtandao if self.injini_ya_picha == "mtandao" else Mchoraji
            self._mchoraji = aina(self.hadithi)
        self._mchoraji.hadithi = self.hadithi
        return self._mchoraji

    def wahusika(self, chora_upya: tuple[str, ...] = ()) -> dict[str, Path]:
        """Picha za wahusika. `chora_upya`: majina (id) ya wahusika wa kuchorwa upya kwa mbegu mpya."""
        print("👥 Picha za wahusika...")
        mpya = {w: random.randint(1, 10**6) for w in chora_upya}
        return tengeneza_wahusika(self.hadithi, self.folda / "wahusika", self.injini_ya_picha, self.mchoraji, mpya)

    def matukio(self, chora_upya: tuple[int, ...] = ()) -> dict[int, Path]:
        """Picha za matukio. `chora_upya`: namba za matukio ya kuchorwa upya kwa mbegu mpya."""
        wahusika = self.wahusika()
        print("🖼️  Picha za matukio...")
        mpya = {n: random.randint(1, 10**6) for n in chora_upya}
        return tengeneza_matukio(self.hadithi, self.folda / "matukio", wahusika, self.injini_ya_picha,
                                 self.mchoraji, mpya)

    def chora_upya(self, *namba: int) -> dict[int, Path]:
        """Chora upya matukio haya kwa mbegu mpya (picha tofauti)."""
        return self.matukio(chora_upya=namba)

    def funga_mchoraji(self) -> None:
        """Ondoa modeli ya picha kwenye GPU ili modeli ya mwendo ipate nafasi."""
        if isinstance(self._mchoraji, Mchoraji):
            torch = self._mchoraji.torch
            del self._mchoraji.pipe
            self._mchoraji = None
            gc.collect()
            torch.cuda.empty_cache()

    def funga_filamu(self) -> None:
        if self._mpiga is not None:
            self._mpiga.funga()
            self._mpiga = None

    def picha_za_shots(self, picha: dict[int, Path]) -> dict[tuple[int, int], Path]:
        wahusika = self.wahusika()
        print("🎞️  Picha za kuanzia za shots...")
        return tengeneza_picha_za_shots(self.hadithi, self.folda / "shots", wahusika, picha, self.injini_ya_picha,
                                        self.mchoraji if any(sh.picha for t in self.hadithi.matukio for sh in t.shots)
                                        else self._mchoraji)

    def klipu_za_filamu(self, picha: dict[int, Path], sauti) -> dict[int, list[Path]]:
        """Hali ya Filamu: video halisi kwa kila shot ya kila tukio (huhifadhiwa; huendelea kesho)."""
        from .filamu import MpigaPicha, mpango, tengeneza_klipu

        h = self.hadithi
        injini = "mfano" if self.injini_ya_picha == "mfano" else h.mipangilio.injini_ya_filamu
        if injini != "mfano":
            try:
                import torch

                gpu = torch.cuda.is_available()
            except ImportError:
                gpu = False
            if not gpu:
                print("  ⚠️  Hali ya Filamu inahitaji GPU; natumia mwendo wa kawaida badala yake.")
                return {}
        kf = self.picha_za_shots(picha)
        mida = {t.namba: muda_wa_tukio(t, sauti) for t in h.matukio}
        orodha = mpango(h, kf, mida, self.folda / "filamu", injini if injini != "mfano" else "ltx")
        jumla = sum(len(v) for v in orodha.values())
        mpya = sum(1 for v in orodha.values() for k in v if not k.faili.exists())
        print(f"🎬 Hali ya Filamu: klipu {jumla} ({mpya} mpya) kwa {h.mipangilio.injini_ya_filamu}")
        if mpya and injini != "mfano":
            self.funga_mchoraji()
            if self._mpiga is None or self._mpiga.injini != injini:
                self.funga_filamu()
                self._mpiga = MpigaPicha(injini)
        return tengeneza_klipu(h, orodha, injini, self._mpiga)

    def klipu_za_ai(self, picha: dict[int, Path]) -> dict[int, Path]:
        """Mwendo wa AI kwa matukio yenye `mwendo_ai: true`. Klipu huhifadhiwa; hutengenezwa upya
        tu picha au mipangilio ikibadilika. Bila GPU, matukio hayo hupata mwendo wa kina badala yake."""
        matukio = [t for t in self.hadithi.matukio if t.mwendo_ai and t.namba in picha]
        if not matukio:
            return {}
        mp = self.hadithi.mipangilio
        upana, urefu = self.hadithi.video_size
        folda = self.folda / "mwendo"
        folda.mkdir(parents=True, exist_ok=True)
        matokeo, kazi = {}, []
        for t in matukio:
            alama = alama_ya_klipu(picha[t.namba], mp.nguvu_ya_mwendo, mp.modeli_ya_mwendo, self.hadithi.ukubwa,
                                   self.hadithi.ubora["svd_hatua"], self.injini_ya_picha)
            f = folda / f"tukio{t.namba:03d}_{alama}.mp4"
            if f.exists():
                matokeo[t.namba] = f
            else:
                kazi.append((t, f))
        if not kazi:
            return matokeo

        if self.injini_ya_picha == "mfano":
            for t, f in kazi:
                klipu_ya_mfano(picha[t.namba], f, upana, urefu)
                matokeo[t.namba] = f
            return matokeo

        try:
            import torch

            gpu = torch.cuda.is_available()
        except ImportError:
            gpu = False
        if not gpu:
            print("  ⚠️  Mwendo wa AI unahitaji GPU; matukio hayo yatapata mwendo wa kina (2.5D) badala yake.")
            return matokeo

        self.funga_mchoraji()
        mwendo = MwendoWaAI(mp.modeli_ya_mwendo)
        try:
            for i, (t, f) in enumerate(kazi, 1):
                print(f"  🎥 Mwendo wa AI {i}/{len(kazi)}: tukio {t.namba} (dakika 3-6)...")
                try:
                    mwendo.tengeneza(picha[t.namba], f, upana, urefu, mp.mbegu + t.namba, mp.nguvu_ya_mwendo,
                                     self.hadithi.ubora["svd_hatua"])
                    matokeo[t.namba] = f
                except Exception as e:  # noqa: BLE001
                    f.unlink(missing_ok=True)
                    print(f"  ⚠️  Tukio {t.namba}: mwendo wa AI umeshindwa ({type(e).__name__}: {str(e)[:150]}); "
                          "natumia mwendo wa kina.")
        finally:
            mwendo.funga()
        return matokeo

    def video(self, kadi_ya_kichwa: bool = True, manukuu: bool | None = None) -> Path:
        picha = self.matukio()
        print("🎙️  Sauti za wahusika...")
        sauti = tengeneza_sauti(self.hadithi, self.folda / "sauti", self.injini_ya_sauti)
        filamu = self.klipu_za_filamu(picha, sauti) if self.hadithi.mipangilio.filamu else {}
        ai = {} if filamu else self.klipu_za_ai(picha)
        print("🎬 Inaunganisha video...")
        return tengeneza_video(self.hadithi, self.folda, picha, sauti, kadi_ya_kichwa, klipu_za_ai=ai,
                               injini_ya_kina="mfano" if self.injini_ya_picha == "mfano" else "ai",
                               manukuu_yaonekane=manukuu, klipu_za_filamu=filamu)
