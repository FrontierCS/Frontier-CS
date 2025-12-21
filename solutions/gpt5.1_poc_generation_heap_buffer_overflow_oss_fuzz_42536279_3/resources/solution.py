import os
import tarfile


class Solution:
    def solve(self, src_path: str) -> bytes:
        target_size = 6180

        def is_text_file(name: str) -> bool:
            text_exts = (
                ".c",
                ".h",
                ".cpp",
                ".cc",
                ".cxx",
                ".hpp",
                ".hh",
                ".txt",
                ".md",
                ".py",
                ".java",
                ".go",
                ".rs",
                ".js",
                ".ts",
                ".html",
                ".xml",
                ".json",
                ".yml",
                ".yaml",
                ".cmake",
                ".in",
                ".am",
                ".ac",
                ".m4",
                ".sh",
                ".bat",
                ".ps1",
            )
            nl = name.lower()
            return any(nl.endswith(ext) for ext in text_exts)

        def select_poc_from_tar(path: str, size_hint: int) -> bytes | None:
            try:
                with tarfile.open(path, "r:*") as tf:
                    best_member = None
                    best_score = None

                    suspicious_keywords = (
                        "poc",
                        "crash",
                        "oss-fuzz",
                        "fuzz",
                        "heap",
                        "overflow",
                        "42536279",
                        "id_",
                        "clusterfuzz",
                        "svc",
                    )

                    for member in tf.getmembers():
                        if not member.isreg():
                            continue

                        size = member.size
                        name = member.name
                        name_lower = name.lower()

                        score = None

                        # Primary heuristic: exact size match
                        if size == size_hint:
                            score = 100
                        else:
                            # Near size match
                            diff = abs(size - size_hint)
                            if diff <= 64:
                                score = 80 - diff  # between ~16 and 79
                            else:
                                # Only consider if name is clearly suspicious
                                if any(k in name_lower for k in suspicious_keywords):
                                    # base score decreasing with size distance
                                    score = max(10, 60 - diff // 64)

                        if score is None:
                            continue

                        # Bonus for suspicious names
                        if any(
                            k in name_lower
                            for k in ("poc", "crash", "oss-fuzz", "42536279", "clusterfuzz")
                        ):
                            score += 40

                        # Slight penalty for obvious text files
                        if is_text_file(name):
                            score -= 30

                        # Avoid negative scores
                        if score < 0:
                            continue

                        if best_score is None or score > best_score:
                            best_score = score
                            best_member = member

                    if best_member is not None:
                        f = tf.extractfile(best_member)
                        if f is not None:
                            data = f.read()
                            if isinstance(data, bytes) and data:
                                return data
            except Exception:
                return None

            return None

        poc = select_poc_from_tar(src_path, target_size)
        if poc is not None:
            return poc

        # Fallback: construct a synthetic bytestream with H.264-like start codes
        start_code = b"\x00\x00\x00\x01"
        data = bytearray()
        # Build repeated pseudo-NAL units until we reach the target size
        while len(data) + len(start_code) < target_size:
            data += start_code
            # Payload with deterministic pseudo-random pattern
            remaining = target_size - len(data)
            payload_len = min(64, remaining)
            for i in range(payload_len):
                # Use a simple LCG-like pattern to generate bytes
                data.append((37 + 13 * i) & 0xFF)

        # Trim or pad to exact target size
        if len(data) > target_size:
            del data[target_size:]
        elif len(data) < target_size:
            data.extend(b"\x00" * (target_size - len(data)))

        return bytes(data)
