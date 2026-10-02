"""Hatua zote kwa mpangilio: wahusika → matukio → sauti → video."""
from __future__ import annotations

from pathlib import Path

from .images import Mchoraji, tengeneza_matukio, tengeneza_wahusika
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
    def mchoraji(self) -> Mchoraji | None:
        if self.injini_ya_picha == "mfano":
            return None
        if self._mchoraji is None:
            self._mchoraji = Mchoraji(self.hadithi)
        self._mchoraji.hadithi = self.hadithi
        return self._mchoraji

    def wahusika(self) -> dict[str, Path]:
        print("👥 Picha za wahusika...")
        return tengeneza_wahusika(self.hadithi, self.folda / "wahusika", self.injini_ya_picha, self.mchoraji)

    def matukio(self) -> dict[int, Path]:
        wahusika = self.wahusika()
        print("🖼️  Picha za matukio...")
        return tengeneza_matukio(self.hadithi, self.folda / "matukio", wahusika, self.injini_ya_picha,
                                 self.mchoraji)

    def chora_upya(self, *namba: int) -> None:
        """Futa picha za matukio haya ili zichorwe upya (badilisha 'mbegu' au maelezo kwanza)."""
        for n in namba:
            (self.folda / "matukio" / f"tukio{n:03d}.png").unlink(missing_ok=True)

    def video(self, kadi_ya_kichwa: bool = True) -> Path:
        picha = self.matukio()
        print("🎙️  Sauti za wahusika...")
        sauti = tengeneza_sauti(self.hadithi, self.folda / "sauti", self.injini_ya_sauti)
        print("🎬 Inaunganisha video...")
        return tengeneza_video(self.hadithi, self.folda, picha, sauti, kadi_ya_kichwa)
