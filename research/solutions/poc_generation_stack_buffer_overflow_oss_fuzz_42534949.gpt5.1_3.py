import tarfile


class Solution:
    def solve(self, src_path: str) -> bytes:
        # Try to infer which infinity/NaN spellings the project uses
        candidate_bases = [
            "Infinity", "INFINITY",
            "inf", "Inf", "INF",
            ".inf", ".Inf", ".INF",
            "nan", "NaN", "NAN",
        ]

        found_bases = set()

        try:
            with tarfile.open(src_path, "r:*") as tar:
                checked_files = 0
                for member in tar.getmembers():
                    if not member.isfile():
                        continue
                    # Skip very large files to keep things fast
                    if member.size > 1024 * 1024:
                        continue
                    if checked_files >= 200:
                        break
                    checked_files += 1

                    f = tar.extractfile(member)
                    if not f:
                        continue
                    try:
                        data = f.read(102400)
                    finally:
                        f.close()

                    try:
                        text = data.decode("utf-8", "ignore")
                    except Exception:
                        continue

                    for base in candidate_bases:
                        if base in text:
                            found_bases.add(base)
        except Exception:
            found_bases = set()

        tokens_set = set()

        if found_bases:
            # Build tokens based on actual spellings seen in the source
            for base in found_bases:
                tokens_set.add("-" + base)
                if len(base) > 1:
                    tokens_set.add("-" + base[:-1])
                if len(base) > 2:
                    tokens_set.add("-" + base[:2])
        else:
            # Fallback: use a broad set of common infinity/NaN spellings
            for base in candidate_bases:
                tokens_set.add("-" + base)
                if len(base) > 1:
                    tokens_set.add("-" + base[:-1])

        # Ensure we always include some core infinity-style tokens with leading minus
        for base in ("Infinity", "inf", ".inf"):
            tokens_set.add("-" + base)
            if len(base) > 1:
                tokens_set.add("-" + base[:-1])

        tokens_list = sorted(tokens_set, key=len)
        payload_str = " ".join(tokens_list) + "\n"
        return payload_str.encode("ascii", "ignore")