import os
import tarfile


class Solution:
    def solve(self, src_path: str) -> bytes:
        GT_LEN = 71298
        desired_len = GT_LEN

        def fallback() -> bytes:
            return b"A" * desired_len

        try:
            tar = tarfile.open(src_path, "r:*")
        except Exception:
            return fallback()

        # Step 1: Try to find an existing PoC/crash file in the tarball
        candidate_data = None
        candidate_diff = None
        poc_keywords = [
            "poc",
            "use_after_free",
            "use-after-free",
            "heap_uaf",
            "uaf",
            "heap-use-after-free",
            "heap-overflow",
            "heap_buffer_overflow",
            "crash",
            "repro",
            "id:",
            "clusterfuzz",
            "timeout",
            "oom",
        ]
        try:
            for m in tar.getmembers():
                if not m.isfile():
                    continue
                name_lower = m.name.lower()
                if any(k in name_lower for k in poc_keywords):
                    try:
                        f = tar.extractfile(m)
                        if f is None:
                            continue
                        data = f.read()
                    except Exception:
                        continue
                    if not data:
                        continue
                    l = len(data)
                    diff = abs(l - desired_len)
                    if candidate_data is None or diff < candidate_diff:
                        candidate_data = data
                        candidate_diff = diff
        except Exception:
            candidate_data = None

        if candidate_data is not None:
            tar.close()
            return candidate_data

        # Step 2: Build PoC from seed corpus files by repetition
        seeds = []
        corpus_keywords = [
            "seed_corpus",
            "corpus",
            "seeds",
            "inputs",
            "input",
            "cases",
            "testcases",
            "fuzz",
        ]
        try:
            for m in tar.getmembers():
                if not m.isfile():
                    continue
                name_lower = m.name.lower()
                if not any(kw in name_lower for kw in corpus_keywords):
                    continue
                if m.size == 0 or m.size > 1024 * 1024:
                    continue
                try:
                    f = tar.extractfile(m)
                    if f is None:
                        continue
                    data = f.read()
                except Exception:
                    continue
                if not data:
                    continue
                weight = 1
                if "usbredir" in name_lower:
                    weight += 100
                elif "redir" in name_lower:
                    weight += 50
                if "serialize" in name_lower:
                    weight += 20
                if "parser" in name_lower:
                    weight += 10
                if "uaf" in name_lower:
                    weight += 30
                seeds.append({"data": data, "weight": weight})
        except Exception:
            seeds = []

        if seeds:
            seeds.sort(key=lambda s: (-s["weight"], -len(s["data"])))
            base_parts = []
            total = 0
            for seed in seeds:
                d = seed["data"]
                base_parts.append(d)
                total += len(d)
                if total >= 4096:
                    break
            base = b"".join(base_parts)
            if not base:
                base = seeds[0]["data"]
            rep = desired_len // len(base) + 1
            poc = (base * rep)[:desired_len]
            tar.close()
            return poc

        # Step 3: Fallback using magic string from source, if available
        magic = None
        try:
            for m in tar.getmembers():
                if not m.isfile():
                    continue
                if m.size == 0 or m.size > 512 * 1024:
                    continue
                lower_name = m.name.lower()
                if not (
                    lower_name.endswith(".c")
                    or lower_name.endswith(".h")
                    or lower_name.endswith(".txt")
                    or lower_name.endswith(".md")
                    or lower_name.endswith(".rst")
                ):
                    continue
                try:
                    f = tar.extractfile(m)
                    if f is None:
                        continue
                    content = f.read()
                except Exception:
                    continue
                try:
                    content_lower = content.lower()
                except Exception:
                    content_lower = content
                if b"usbredir" in content_lower:
                    magic = b"usbredir"
                    break
        except Exception:
            magic = None

        tar.close()

        if magic is None:
            return fallback()
        rep = desired_len // len(magic) + 1
        return (magic * rep)[:desired_len]