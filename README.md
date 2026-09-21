# ComfyUI-Save_Audio_Numbered

A ComfyUI custom node that saves audio as an uncompressed **WAV** file to a folder of your
choice — with automatic sequential numbering in the style of ComfyUI's built-in
*Save Image* node: `output_001.wav`, `output_002.wav`, `output_003.wav` …

It is a fork/extension of **`Save Audio With Path (CRT)`** from [crt-nodes](https://github.com/plugcrypt/crt-nodes)
(MIT, by plugcrypt), which always overwrote the same filename. This version adds proper
file numbering so repeated runs never clobber previous output.

## Features

- **Three numbering modes**
  - `zero-padded` (default): `output_001.wav`, `output_002.wav`, … (configurable digit width)
  - `plain`: `output_1.wav`, `output_2.wav`, …
  - `off`: legacy CRT behaviour — overwrites the same filename
- **Configurable number of digits** for zero-padded mode (`_001` vs `_1`)
- Optional **subfolder** and **filename suffix** (applied before the number)
- Accepts a full *file* path in `folder_path` — its parent directory is used automatically
- Empty filename → auto-generated unique name, so a save never blocks
- Keeps all original CRT behaviour: 24-bit PCM / 32-bit float WAV, sample-rate passthrough,
  optional peak-normalization of clipping audio

## Inputs

| Name | Type | Notes |
|------|------|-------|
| `audio` | AUDIO | Any ComfyUI audio tensor (`{"waveform": [B,C,T], "sample_rate": int}`) |
| `folder_path` | STRING | Base folder, or a full file path (parent dir is used). Defaults to ComfyUI output. |
| `subfolder_name` | STRING | Subfolder inside the base folder. Empty = save directly into the base folder. |
| `filename` | STRING | File name without extension. Number is appended when numbering is on. |
| `suffix` | STRING | Optional suffix appended to the filename (before the number), e.g. `_v2`. |
| `numbering` | Enum | `zero-padded` / `plain` / `off`. Default `zero-padded`. |
| `digits` | INT (1–9) | Digit width for zero-padded mode. Ignored in `plain`. Default 3. |
| `sample_rate` | Enum | Fallback sample rate if the audio data carries none. |
| `bit_depth` | Enum | `24-bit PCM` / `32-bit float`. |
| `normalize_clipping` | BOOL | Peak-normalize clipped audio (default on). |

## Installation

**Method 1 — ComfyUI Manager:** paste the repo URL in *Custom Nodes Manager → Install from Git*.

**Method 2 — manual:**

```bash
cd <ComfyUI>/custom_nodes
git clone https://github.com/VeniaminPetrov/ComfyUI-Save_Audio.git ComfyUI-Save_Audio_Numbered
# (or: git clone <your fork URL> ComfyUI-Save_Audio_Numbered)
```

Then restart ComfyUI. The node appears under **CRT → Save** as **“Save Audio With Path (Numbered)”**.

## How numbering works

The counter uses the same rule as the core *Save Image* node: it scans the target folder for
files named `<filename><suffix>_<N>.wav` (any digit padding), takes the highest index and writes
the next one. A final existence check guarantees an existing file is never overwritten, even if it
does not follow the naming scheme. Deleting a few files does **not** cause re-use of their numbers —
numbering only ever moves forward within whatever remains in the folder.

## Verification without a full workflow

`tests/test_numbering.py` exercises the real node code (numbering logic + WAV writing) with a stubbed
`folder_paths`. Run it from any Python that has `numpy`, `scipy` and optionally `torch`:

```bash
python tests/test_numbering.py
# e.g. inside ComfyUI:  <ComfyUI>/python_embeded/python.exe tests/test_numbering.py
```

It creates a temp folder, saves the same file 5 times (expect `_001.._005`), pre-creates `output_007.wav`
(expect next = `_008`, max+1 rule), checks plain mode (`x_3` after `x_1`,`x_2`), overwrite mode, and
subfolder/suffix handling. All assertions must pass.

## License & attribution

MIT — see [LICENSE](LICENSE). This project is derived from *Save Audio With Path (CRT)* by
**plugcrypt** ([crt-nodes](https://github.com/plugcrypt/crt-nodes), MIT); the original copyright
notice is preserved in the LICENSE file.
