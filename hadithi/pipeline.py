"""Hatua zote kwa mpangilio: wahusika → matukio → sauti → video."""
from __future__ import annotations

import random
from pathlib import Path

from .images import Mchoraji, MchorajiWaMtandao, tengeneza_matukio, tengeneza_wahusika
from .story import Hadithi, soma
from .video import tengeneza_video
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
        self.hadithi: Hadithi = soma(self.faili)
        print(f"📖 '{self.hadithi.kichwa}': matukio {len(self.hadithi.matukio)}, "
              f"wahusika {len(self.hadithi.wahusika)}")

    def pakia_upya(self) -> Hadithi:
        """Soma tena faili la hadithi baada ya kulibadilisha."""
        self.hadithi = soma(self.faili)
        return self.hadithi

    @property
    def mchoraji(self) -> Mchoraji | MchorajiWaMtandao | None:
        if self.injini_ya_picha == "mfano":
            return None
        if self._mchoraji is None:
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

    def video(self, kadi_ya_kichwa: bool = True) -> Path:
        picha = self.matukio()
        print("🎙️  Sauti za wahusika...")
        sauti = tengeneza_sauti(self.hadithi, self.folda / "sauti", self.injini_ya_sauti)
        print("🎬 Inaunganisha video...")
        return tengeneza_video(self.hadithi, self.folda, picha, sauti, kadi_ya_kichwa)
