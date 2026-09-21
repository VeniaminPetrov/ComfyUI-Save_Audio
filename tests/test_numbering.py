"""Standalone verification for Save Audio With Path (Numbered).

Runs WITHOUT a full ComfyUI install: it stubs `folder_paths`, loads the node file
directly, and drives `save_audio()` with synthetic audio. Requires numpy + scipy;
torch is optional (a minimal shim is used if absent).

Usage:  python tests/test_numbering.py        (or <ComfyUI>/python_embeded/python.exe ...)
"""
import importlib.util
import os
import sys
import tempfile
import types
import wave

import numpy as np


# ---- stub the ComfyUI-only `folder_paths` module BEFORE importing the node ----
def _install_stub_folder_paths():
    if "folder_paths" in sys.modules:
        return  # real one present (running inside ComfyUI) -> keep it
    fp = types.ModuleType("folder_paths")

    def get_output_directory():
        return os.path.join(tempfile.gettempdir(), "comfyui_stub_out")

    fp.get_output_directory = get_output_directory
    sys.modules["folder_paths"] = fp


_install_stub_folder_paths()

# ---- optional torch (real if available, otherwise a tiny shim) -----------------
try:  # pragma: no cover - depends on environment
    import torch as _torch
except Exception:  # noqa: BLE001
    _torch = None


def _mk_waveform(arr):
    """arr shape (B,C,T). Return something the node can [0].cpu().numpy() off."""
    if _torch is not None:
        return _torch.from_numpy(np.ascontiguousarray(arr.astype("float32")))

    class _Leaf:
        def __init__(self, a):
            self.a = a

        def cpu(self):
            return self

        def numpy(self):
            return self.a

    class _Root:
        def __init__(self, a):
            self.a = a

        def nelement(self):
            return int(a.size)

        def __getitem__(self, i):
            assert isinstance(i, int), "only int index supported in shim"
            return _Leaf(np.ascontiguousarray(self.a[i]))

    return _Root(arr.astype("float32"))


def make_audio(sr=44100, seconds=1.0, freq=440.0, peak=1.0, channels=1):
    t = np.arange(int(sr * seconds)) / sr
    sig = peak * np.sin(2 * np.pi * freq * t)
    arr = np.repeat(sig.reshape(1, -1), channels, axis=0).T  # (channels, T)
    arr = arr.reshape(1, channels, -1)                       # (B, C, T)
    return {"waveform": _mk_waveform(arr), "sample_rate": sr}


def load_node():
    here = os.path.dirname(os.path.abspath(__file__))
    node_file = os.path.join(here, "..", "py", "Save_Audio_With_Path_Numbered.py")
    spec = importlib.util.spec_from_file_location("save_audio_numbered", node_file)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def saved_names(d, prefix):
    return sorted(f for f in os.listdir(d) if f.startswith(prefix))


def main():
    mod = load_node()
    node = mod.SaveAudioWithPathNumbered()
    results = []

    def check(name, cond, detail=""):
        ok = bool(cond)
        results.append(ok)
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f"  -> {detail}" if detail and not ok else ""))

    # ---- Test 1: zero-padded sequential _001.._005 ------------------------------
    d = tempfile.mkdtemp(prefix="num1_")
    for i in range(5):
        node.save_audio(make_audio(freq=300 + i * 10), d, "", "output", "", "zero-padded", 3, "44100", "24-bit PCM", True)
    names = saved_names(d, "output")
    check("sequential zero-padded produces _001.._005",
          names == [f"output_{n:03d}.wav" for n in range(1, 6)], str(names))

    # ---- Test 2: max+1 rule (pre-existing output_007 -> next is _008) ----------
    d = tempfile.mkdtemp(prefix="num2_")
    with open(os.path.join(d, "output_007.wav"), "wb"):
        pass  # empty placeholder file
    before = os.path.getsize(os.path.join(d, "output_007.wav"))
    node.save_audio(make_audio(freq=500), d, "", "output", "", "zero-padded", 3, "44100", "24-bit PCM", True)
    check("continues after highest existing index (next = _008)",
          os.path.isfile(os.path.join(d, "output_008.wav")), saved_names(d, "output"))
    check("pre-existing file untouched", os.path.getsize(os.path.join(d, "output_007.wav")) == before)

    # ---- Test 3: plain numbering (x_1,x_2 -> x_3) ------------------------------
    d = tempfile.mkdtemp(prefix="num3_")
    for n in (1, 2):
        with open(os.path.join(d, f"x_{n}.wav"), "wb"):
            pass
    node.save_audio(make_audio(freq=600), d, "", "x", "", "plain", 3, "44100", "24-bit PCM", True)
    check("plain numbering continues x_1,x_2 -> x_3", os.path.isfile(os.path.join(d, "x_3.wav")), saved_names(d, "x"))

    # ---- Test 4: 'off' overwrites (single y.wav after two saves) ---------------
    d = tempfile.mkdtemp(prefix="num4_")
    node.save_audio(make_audio(freq=200), d, "", "y", "", "off", 3, "44100", "24-bit PCM", True)
    node.save_audio(make_audio(freq=900), d, "", "y", "", "off", 3, "44100", "24-bit PCM", True)
    names = [f for f in os.listdir(d) if f.startswith("y")]
    check("'off' mode overwrites -> exactly y.wav", names == ["y.wav"], str(names))

    # ---- Test 5: subfolder + suffix (a/b/out_v2_001.wav) -----------------------
    d = tempfile.mkdtemp(prefix="num5_")
    node.save_audio(make_audio(freq=700), d, "a\\b", "out", "_v2", "zero-padded", 3, "44100", "24-bit PCM", True)
    target = os.path.join(d, "a", "b", "out_v2_001.wav")
    check("subfolder + suffix -> a/b/out_v2_001.wav", os.path.isfile(target), str(sorted(os.listdir(d))))

    # ---- Test 6: saved WAV is valid & correct sample rate ----------------------
    d = tempfile.mkdtemp(prefix="num6_")
    node.save_audio(make_audio(sr=48000, freq=350), d, "", "out", "", "zero-padded", 3, "48000", "24-bit PCM", True)
    p = os.path.join(d, "out_001.wav")
    with wave.open(p, "rb") as w:
        ch, sw, fr, nf = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()
    check("wav is valid (mono 24-bit @48k, has frames)", ch == 1 and sw == 3 and fr == 48000 and nf > 0, f"{ch},{sw},{fr},{nf}")

    # ---- Test 7: peak normalization of clipping audio --------------------------
    d = tempfile.mkdtemp(prefix="num7_")
    node.save_audio(make_audio(peak=5.0), d, "", "out", "", "zero-padded", 3, "44100", "24-bit PCM", True)
    p = os.path.join(d, "out_001.wav")
    # Decode the raw 24-bit frames ourselves via the wave module (authoritative),
    # so the peak check is not affected by scipy's int32 packing quirks.
    with wave.open(p, "rb") as w:
        assert w.getsampwidth() == 3 and w.getnchannels() == 1
        raw = np.frombuffer(w.readframes(w.getnframes()), dtype=np.uint8)
    u = (raw[0::3].astype(np.int64)
         + (raw[1::3].astype(np.int64) << 8)
         + (raw[2::3].astype(np.int64) << 16))
    u = np.where(u >= (1 << 23), u - (1 << 24), u).astype(np.int32)  # sign-extend 24-bit
    peak_fs = float(np.max(np.abs(u))) / 8388607.0
    # Input peak was 5.0; after normalization the output peak must be ~full scale (1.0).
    check("clipping audio (peak 5.0) normalized to ~full scale", 0.9 < peak_fs <= 1.0 + 1e-4, f"{peak_fs:.5f}")

    # ---- Test 8: 32-bit float bit depth ----------------------------------------
    d = tempfile.mkdtemp(prefix="num8_")
    node.save_audio(make_audio(peak=1.5), d, "", "out", "", "zero-padded", 3, "44100", "32-bit float", False)
    p = os.path.join(d, "out_001.wav")
    # The stdlib wave module cannot READ IEEE-float (format 3) files, so verify
    # the fmt chunk manually: audio format must be 3 and sample width 4 bytes.
    import struct
    with open(p, "rb") as f:
        hdr = f.read(12)
        assert hdr[:4] == b"RIFF" and hdr[8:12] == b"WAVE", "not a RIFF/WAVE file"
        fmt_id = f.read(4); assert fmt_id == b"fmt ", "missing fmt chunk"
        (fmt_len,) = struct.unpack("<I", f.read(4))
        (audio_format, nch, sr_fmt, byte_rate, block_align, bits) = struct.unpack("<HHIIHH", f.read(16))
    assert audio_format == 3 and bits == 32 and nch == 1, \
        f"expected IEEE-float 32-bit mono, got fmt={audio_format} bits={bits} ch={nch}"
    from scipy.io.wavfile import read as _rd
    sr_read, data = _rd(p)
    check("32-bit float mode writes a readable float wav", np.issubdtype(data.dtype, np.floating), str(data.dtype))

    passed = sum(results)
    print(f"\n{passed}/{len(results)} checks passed.")
    if passed != len(results):
        sys.exit(1)


if __name__ == "__main__":
    main()
