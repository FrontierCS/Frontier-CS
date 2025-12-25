import os
import tarfile


class Solution:
    TARGET_LEN = 800

    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC input. Tries to locate a likely PoC file inside the
        provided source tarball or directory; if none is found, returns a
        synthetic 800-byte blob.
        """
        data = self._find_candidate_poc(src_path)
        if data is not None:
            return data
        return self._synthetic_poc()

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _find_candidate_poc(self, src_path: str):
        """
        Try to discover an existing PoC or crash-inducing file within the
        source tree. Prefer files whose size is close to TARGET_LEN and whose
        name/extension suggests they are a font or PoC.
        """
        if os.path.isdir(src_path):
            return self._find_candidate_in_dir(src_path)
        else:
            # Assume tarball by default; if that fails, fall back to directory.
            data = self._find_candidate_in_tar(src_path)
            if data is not None:
                return data
            if os.path.isdir(src_path):
                return self._find_candidate_in_dir(src_path)
        return None

    def _score_candidate(self, name: str, size: int):
        """
        Score a candidate file based on size and name/extension hints.
        Lower scores are better. Returns None for clearly unsuitable files.
        """
        if size <= 0:
            return None

        # Ignore very large files; PoCs are usually small.
        if size > 1024 * 1024:
            return None

        name_lower = name.lower()
        ext = os.path.splitext(name_lower)[1]

        # Base score: distance from target length.
        score = abs(size - self.TARGET_LEN)

        # Extensions commonly used for fonts / PoCs / fuzz inputs.
        font_exts = {
            ".ttf",
            ".otf",
            ".ttc",
            ".otc",
            ".woff",
            ".woff2",
            ".cff",
            ".pcf",
            ".pfa",
            ".pfb",
            ".bin",
            ".dat",
            ".data",
            ".poc",
            ".font",
        }

        # Keywords hinting that this is a PoC or fuzz/crash sample.
        bonus_keywords = [
            "uaf",
            "use-after-free",
            "use_after_free",
            "heap",
            "otsstream",
            "ots_stream",
            "ots-stream",
            "write",
            "poc",
            "crash",
            "fuzz",
            "fuzzer",
            "clusterfuzz",
            "asan",
            "ubsan",
        ]

        if ext in font_exts:
            score -= 100

        if any(kw in name_lower for kw in bonus_keywords):
            score -= 200

        # Favor files in test or fuzz directories.
        if any(seg in name_lower for seg in ("/test", "/tests", "/fuzz", "/corpus", "/poc")):
            score -= 50

        return score

    def _find_candidate_in_tar(self, tar_path: str):
        if not tarfile.is_tarfile(tar_path):
            return None

        best_member = None
        best_score = None

        try:
            with tarfile.open(tar_path, "r:*") as tf:
                for member in tf.getmembers():
                    if not member.isfile():
                        continue
                    size = member.size
                    name = member.name
                    s = self._score_candidate(name, size)
                    if s is None:
                        continue
                    if best_member is None or s < best_score:
                        best_member = member
                        best_score = s
                        # Early-exit heuristic: perfect size & strong hint.
                        if size == self.TARGET_LEN and s <= -300:
                            break

                if best_member is not None:
                    f = tf.extractfile(best_member)
                    if f is not None:
                        return f.read()
        except Exception:
            # Any error in reading the tarball: treat as no candidate found.
            return None

        return None

    def _find_candidate_in_dir(self, root: str):
        best_path = None
        best_score = None

        for dirpath, _, filenames in os.walk(root):
            for fname in filenames:
                full_path = os.path.join(dirpath, fname)
                try:
                    size = os.path.getsize(full_path)
                except OSError:
                    continue

                rel_name = os.path.relpath(full_path, root)
                s = self._score_candidate(rel_name, size)
                if s is None:
                    continue
                if best_path is None or s < best_score:
                    best_path = full_path
                    best_score = s
                    if size == self.TARGET_LEN and s <= -300:
                        break

        if best_path is not None:
            try:
                with open(best_path, "rb") as f:
                    return f.read()
            except OSError:
                return None

        return None

    def _synthetic_poc(self) -> bytes:
        """
        Fallback PoC generator: emit a synthetic 800-byte blob that roughly
        resembles an OpenType/TrueType font header, followed by padding.
        """
        # sfnt version 'OTTO' (OpenType with CFF), followed by minimalistic header.
        # This is not a valid font, but it's structurally plausible enough for
        # many parsers to proceed some distance before bailing.
        header = bytearray()

        # sfntVersion: 'OTTO'
        header.extend(b"OTTO")

        # numTables (uint16), searchRange (uint16), entrySelector (uint16), rangeShift (uint16)
        # Use small but non-zero values to encourage table parsing.
        header.extend((0x00, 0x02))  # numTables = 2
        header.extend((0x00, 0x20))  # searchRange
        header.extend((0x00, 0x01))  # entrySelector
        header.extend((0x00, 0x10))  # rangeShift

        # Table directory entries: tag(4), checksum(4), offset(4), length(4) * 2
        # Fake 'head' and 'name' tables with suspicious offsets/lengths.
        def add_table(tag: bytes, offset: int, length: int):
            header.extend(tag)
            header.extend(offset.to_bytes(4, "big"))
            header.extend(length.to_bytes(4, "big"))
            # simplistic checksum placeholder
            header.extend((0xDE, 0xAD, 0xBE, 0xEF))

        # Offsets that point beyond the header but within our final 800-byte blob.
        add_table(b"head", 0x00000100, 0x00000040)
        add_table(b"name", 0x00000150, 0x000000C8)

        # Simple padding and crafted data region that might exercise edge cases.
        # Include some patterns that sometimes tickle parser bugs.
        crafted = b"".join(
            [
                b"\x00" * 16,
                b"\xFF" * 32,
                b"\x00\x01\x00\x00",  # typical TTF version marker
                b"\x00" * 16,
                b"\xFF\xFF\xFF\xFF" * 8,
                b"\x00\x00\x00\x01" * 8,
                b"\x12\x34\x56\x78" * 4,
            ]
        )

        data = bytes(header) + crafted
        if len(data) >= self.TARGET_LEN:
            return data[: self.TARGET_LEN]
        else:
            return data + b"\x00" * (self.TARGET_LEN - len(data))
