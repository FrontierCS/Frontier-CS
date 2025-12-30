import tarfile


class Solution:
    def solve(self, src_path: str) -> bytes:
        use_http = False
        try:
            with tarfile.open(src_path, "r:*") as tar:
                for member in tar.getmembers():
                    if not member.isfile() or member.size == 0:
                        continue
                    name_lower = member.name.lower()
                    if not any(
                        name_lower.endswith(ext)
                        for ext in (".c", ".h", ".cpp", ".cc", ".cxx", ".hpp", ".hh", ".ipp", ".inc", ".txt", ".md")
                    ):
                        continue
                    f = tar.extractfile(member)
                    if not f:
                        continue
                    chunk = f.read(512 * 1024)
                    if b"http://" in chunk or b"https://" in chunk:
                        use_http = True
                        break
        except Exception:
            pass

        if use_http:
            return b"http://aa"
        else:
            return b"A" * 9