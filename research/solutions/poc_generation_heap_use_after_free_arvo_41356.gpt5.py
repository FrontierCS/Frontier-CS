import tarfile

class Solution:
    def solve(self, src_path: str) -> bytes:
        try:
            text = ""
            with tarfile.open(src_path, "r:*") as tf:
                for m in tf.getmembers():
                    if not m.isfile():
                        continue
                    name = m.name.lower()
                    if not any(name.endswith(ext) for ext in (".cpp", ".cc", ".cxx", ".hpp", ".hh", ".h", ".ipp", ".hxx", ".c")):
                        continue
                    f = tf.extractfile(m)
                    if not f:
                        continue
                    try:
                        data = f.read(512 * 1024)
                    except Exception:
                        continue
                    try:
                        text += data.decode("utf-8", "ignore").lower()
                    except Exception:
                        continue
        except Exception:
            text = ""

        if "yaml" in text or "yml" in text:
            return b"a: 1\na: 2\n"
        if "toml" in text:
            return b"a = 1\na = 2\n"
        if "ini" in text or "[section]" in text:
            return b"a=1\na=2\n"
        return b'{"a":1,"a":2}\n'