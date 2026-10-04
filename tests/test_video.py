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


def test_hali_ya_filamu_na_kuendelea(tmp_path):
    d = yaml.safe_load(open("mifano/siri_ya_kisima.yaml", encoding="utf-8"))
    d["matukio"] = d["matukio"][:2]
    d["matukio"][1]["shots"] = [{"kitendo": "they run, camera tracking"},
                                {"kitendo": "she laughs", "picha": "close-up of a laughing girl", "wahusika": ["neema"]}]
    d["mipangilio"] = {"filamu": True, "ubora": "kawaida"}
    (tmp_path / "h.yaml").write_text(yaml.safe_dump(d, allow_unicode=True), encoding="utf-8")
    s = Studio(tmp_path / "h.yaml", tmp_path / "out", "mfano", "kimya")
    v = s.video(kadi_ya_kichwa=False)
    klipu = sorted(p.name for p in (tmp_path / "out" / "filamu").glob("*.mp4"))
    assert any("tukio002_shot1" in k for k in klipu)  # shot yenye picha yake
    assert any("_e1_" in k for k in klipu)  # mwendelezo wa kujaza muda wa sauti
    assert (tmp_path / "out" / "shots" / "tukio002_shot1.png").exists()
    mtime = {k: (tmp_path / "out" / "filamu" / k).stat().st_mtime_ns for k in klipu}
    s.video(kadi_ya_kichwa=False)  # mara ya pili: hakuna klipu mpya
    assert {k: (tmp_path / "out" / "filamu" / k).stat().st_mtime_ns for k in klipu} == mtime
    assert v.exists()
