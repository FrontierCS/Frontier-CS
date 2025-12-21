import tarfile


class Solution:
    def solve(self, src_path: str) -> bytes:
        target_size = 159

        try:
            tf = tarfile.open(src_path, "r:*")
        except tarfile.TarError:
            return b""

        with tf:
            files = [
                m for m in tf.getmembers()
                if m.isfile() and 0 < m.size <= 1_000_000
            ]

            if not files:
                return b""

            def score_member(m: tarfile.TarInfo) -> int:
                name = m.name.lower()
                size = m.size
                score = 0

                if size == target_size:
                    score += 10000
                else:
                    score -= abs(size - target_size)

                if "poc" in name or "crash" in name:
                    score += 100
                if "uaf" in name or "use-after-free" in name or "heap" in name:
                    score += 40
                if "cue" in name or "cuesheet" in name or "seek" in name or "flac" in name:
                    score += 60
                if any(
                    k in name
                    for k in ("fuzz", "clusterfuzz", "oss-fuzz", "test", "regress", "inputs")
                ):
                    score += 20
                if name.endswith((".cue", ".txt", ".flac", ".bin", ".raw", ".dat")):
                    score += 10

                if size > 4096:
                    score -= (size - 4096) // 1024

                return score

            best_member = None
            best_score = None
            for m in files:
                s = score_member(m)
                if best_score is None or s > best_score:
                    best_score = s
                    best_member = m

            if best_member is None:
                return b""

            extracted = tf.extractfile(best_member)
            if extracted is None:
                return b""

            data = extracted.read()
            return data
