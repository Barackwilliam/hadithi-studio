"""Tumia kutoka terminal:  python -m hadithi mifano/siri_ya_kisima.yaml --nje matokeo"""
import argparse

from .pipeline import Studio


def main() -> None:
    p = argparse.ArgumentParser(prog="hadithi", description="Tengeneza video ya masimulizi kwa AI.")
    p.add_argument("hadithi", help="faili la hadithi (.yaml)")
    p.add_argument("--nje", default="matokeo", help="folda ya matokeo")
    p.add_argument("--picha", choices=["sdxl", "mtandao", "mfano"], default="sdxl",
                   help="sdxl = AI kwenye GPU (bora); mtandao = huduma ya bure bila GPU; mfano = majaribio")
    p.add_argument("--sauti", choices=["edge", "mms", "kimya"], default="edge",
                   help="edge = sauti nyingi za Kiswahili; mms = sauti ya Meta (bila huduma ya nje); kimya = majaribio")
    p.add_argument("--bila-kichwa", action="store_true", help="usiweke kadi ya kichwa mwanzoni")
    a = p.parse_args()
    Studio(a.hadithi, a.nje, a.picha, a.sauti).video(kadi_ya_kichwa=not a.bila_kichwa)


if __name__ == "__main__":
    main()
