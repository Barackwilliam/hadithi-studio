import shutil
import subprocess

import pytest
import yaml

from hadithi import Studio

pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg haipo")


def test_video_yenye_mwendo_wa_ai_na_kina(tmp_path):
    d = yaml.safe_load(open("mifano/siri_ya_kisima.yaml", encoding="utf-8"))
    d["matukio"] = d["matukio"][:2]
    d["matukio"][1]["mwendo_ai"] = True
    (tmp_path / "h.yaml").write_text(yaml.safe_dump(d, allow_unicode=True), encoding="utf-8")
    s = Studio(tmp_path / "h.yaml", tmp_path / "out", "mfano", "kimya")
    v = s.video(kadi_ya_kichwa=False, manukuu=False)
    assert v.exists()
    assert list((tmp_path / "out" / "mwendo").glob("tukio002_*.mp4"))  # klipu ya AI (ya mfano) imehifadhiwa
    muda = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                 str(v)], capture_output=True, text=True).stdout)
    assert muda > 8
