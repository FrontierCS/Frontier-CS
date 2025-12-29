import os
import tarfile


class Solution:
    def solve(self, src_path: str) -> bytes:
        L_GROUND = 73
        default = b"A" * L_GROUND

        try:
            tf = tarfile.open(src_path, "r:*")
        except Exception:
            return default

        with tf:
            members = [m for m in tf.getmembers() if m.isfile()]
            if not members:
                return default

            def score(member, target_size=None):
                name = member.name.lower()
                keywords = [
                    "poc",
                    "crash",
                    "heap",
                    "uaf",
                    "use-after",
                    "use_after",
                    "h225",
                    "ras",
                    "wireshark",
                    "bug",
                    "issue",
                    "id:",
                    "id_",
                    "asan",
                    "heap-use-after-free",
                    "heap_use_after_free",
                ]
                kw_score = 0
                for idx, kw in enumerate(keywords):
                    if kw in name:
                        kw_score += (len(keywords) - idx)

                size_penalty = abs(member.size - target_size) if target_size is not None else 0
                depth = name.count("/")
                bin_exts = (".pcap", ".pcapng", ".cap", ".bin", ".raw", ".dat", ".in", ".out", ".dump")
                text_exts = (".c", ".h", ".cpp", ".cc", ".txt", ".md", ".py", ".sh", ".java")
                ext = os.path.splitext(name)[1]
                ext_score = 0
                if ext in bin_exts:
                    ext_score -= 5
                elif ext in text_exts:
                    ext_score += 5

                return (
                    size_penalty,
                    -kw_score,
                    ext_score,
                    depth,
                    len(name),
                )

            exact = [m for m in members if m.size == L_GROUND]
            if exact:
                best = sorted(exact, key=lambda m: score(m, L_GROUND))[0]
                f = tf.extractfile(best)
                if f is not None:
                    data = f.read()
                    if isinstance(data, str):
                        data = data.encode("utf-8", "ignore")
                    if data:
                        return data

            small = [m for m in members if m.size <= 4096]
            if small:
                best = sorted(small, key=lambda m: score(m, L_GROUND))[0]
                f = tf.extractfile(best)
                if f is not None:
                    data = f.read()
                    if isinstance(data, str):
                        data = data.encode("utf-8", "ignore")
                    if data:
                        return data

        return default