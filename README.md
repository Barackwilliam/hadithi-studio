# 🎬 Hadithi Studio

**Tengeneza video za masimulizi, tamthiliya na katuni kwa AI, bure kabisa.**

[![Fungua kwenye Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Barackwilliam/hadithi-studio/blob/main/Hadithi_Studio.ipynb)

Unaandika hadithi yako (wahusika, matukio na mazungumzo), na Hadithi Studio itafanya yafuatayo:

1. 👥 **Kuchora wahusika** mara moja, ili sura zao zifanane kwenye kila tukio
2. 🖼️ **Kuchora kila tukio** kwa mtindo unaoutaka (katuni 2D, 3D kama Pixar, anime...)
3. 🎙️ **Kuwapa wahusika sauti za Kiswahili**: sauti 4 (wanawake 2, wanaume 2), ambazo unaweza kubadilisha ziwe za mtoto au za mzee
4. 🎥 **Kuweka mwendo wa kamera** (zoom, pan) na mfifio kati ya matukio
5. 💬 **Kuweka manukuu (subtitles)** na **muziki wa nyuma**
6. ✅ **Kutoa video ya MP4** tayari kwa YouTube, TikTok au Instagram

Yote hufanyika kwenye **Google Colab** (GPU ya bure ya Google). Haihitaji kompyuta yenye nguvu.

---

## 🚀 Jinsi ya kutumia (hatua 3)

1. Bonyeza kitufe cha **Open in Colab** hapo juu.
2. Washa GPU: **Runtime → Change runtime type → T4 GPU → Save**
3. Bonyeza ▶️ kwenye kila sehemu kwa mpangilio. Andika hadithi yako kwenye **Hatua ya 3**.

Ukichagua kuhifadhi kwenye Google Drive, kazi yako itakaa salama kwenye folda `HadithiStudio`, na unaweza kuendelea siku nyingine.

---

## ✍️ Muundo wa hadithi

```yaml
kichwa: "Siri ya Kisima"
mtindo: "colorful 2D cartoon illustration, African village, storybook style"
ukubwa: "16:9"          # 16:9 YouTube | 9:16 TikTok/Reels | 1:1 Instagram

wahusika:
  msimulizi:
    sauti: daudi
  neema:
    jina: Neema
    maelezo: "a 9 year old Tanzanian girl, braided hair, yellow dress"
    sauti: rehema
    kina: "+20Hz"       # sauti nyembamba ya mtoto

matukio:
  - picha: "a girl looking into an old stone well, magical blue glow"
    wahusika: [neema]
    mwendo: karibia     # karibia | mbali | kulia | kushoto | tuli
    mazungumzo:
      - "Hapo zamani za kale..."          # msimulizi
      - neema: "Mungu wangu! Ni nini hiki?"
```

Mfano kamili uko kwenye [`mifano/siri_ya_kisima.yaml`](mifano/siri_ya_kisima.yaml).

### Sauti zilizopo
| Jina | Aina |
|---|---|
| `rehema` | Mwanamke (Tanzania) |
| `zuri` | Mwanamke (Kenya) |
| `daudi` | Mwanamume (Tanzania) |
| `rafiki` | Mwanamume (Kenya) |

- `kina: "+25Hz"` hufanya sauti iwe nyembamba (mtoto), na `kina: "-15Hz"` huifanya iwe nzito (mzee au jitu).
- `kasi: "-10%"` hupunguza kasi ya kuongea, na `kasi: "+10%"` huiongeza.

### Mipangilio ya ziada (si lazima)
```yaml
mipangilio:
  mbegu: 42                # badilisha ili upate picha tofauti
  nguvu_ya_mhusika: 0.5    # 0.3-0.7: juu zaidi = sura zinafanana zaidi
  onyesha_jina: false      # true = "Neema: ..." kwenye manukuu
  muziki: muziki.mp3       # muziki wa nyuma (weka faili kwenye folda ya mradi)
  sauti_ya_muziki: 0.12    # ukubwa wa sauti ya muziki
  modeli: stabilityai/stable-diffusion-xl-base-1.0   # modeli yoyote ya SDXL kutoka HuggingFace
```

Je, una picha yako mwenyewe ya tukio? Andika `picha_faili: picha_yangu.jpg` kwenye tukio hilo, na AI haitachora picha ya tukio hilo.

---

## 🤖 Mwombe ChatGPT, Gemini au Claude akuandikie hadithi (bure)

Nakili maelekezo haya, badilisha wazo la hadithi, kisha bandika jibu kwenye Hatua ya 3:

```text
Niandikie hadithi fupi ya Kiswahili kwa ajili ya video ya katuni yenye matukio 8.
Wazo: [mfano: mtoto anayemsaidia jirani yake mzee na kupata zawadi ya ajabu]

Jibu kwa muundo huu wa YAML tu, bila maelezo mengine:
- kichwa, mtindo (kwa Kiingereza), ukubwa: "16:9"
- wahusika: kila mmoja na jina, maelezo ya sura kwa Kiingereza (umri, nywele, nguo),
  sauti (rehema/zuri kwa wanawake, daudi/rafiki kwa wanaume), na kina ("+25Hz" kwa watoto)
- matukio: kila tukio lina "picha" (maelezo ya picha kwa Kiingereza), "wahusika" (orodha),
  na "mazungumzo" (mistari ya Kiswahili; mstari usio na jina ni wa msimulizi,
  au "- jina_la_mhusika: maneno")
Kila tukio liwe na mistari 2 hadi 3 mifupi.
```

---

## 🛠️ Kwa wataalamu: kutumia kutoka terminal

```bash
pip install -r requirements-colab.txt   # kwenye mashine yenye GPU
python -m hadithi mifano/siri_ya_kisima.yaml --nje matokeo

# majaribio bila GPU (picha za mfano):
pip install -r requirements.txt
python -m hadithi mifano/siri_ya_kisima.yaml --picha mfano
```

| Chaguo | Maana |
|---|---|
| `--picha sdxl` | Picha za AI (SDXL + Lightning + IP-Adapter). Inahitaji GPU yenye VRAM ya 12GB au zaidi |
| `--picha mfano` | Picha za majaribio (bila GPU) |
| `--sauti edge` | Sauti 4 za Kiswahili (Microsoft Edge TTS). Hii ndiyo chaguo-msingi |
| `--sauti mms` | Sauti ya Meta MMS ya Kiswahili, inayotumika ikiwa Edge haipatikani |

**Teknolojia zinazotumika (zote ni za bure):** Stable Diffusion XL, SDXL-Lightning (ByteDance), IP-Adapter, Edge TTS, Meta MMS-TTS, FFmpeg.
