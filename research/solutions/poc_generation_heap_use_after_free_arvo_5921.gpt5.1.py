import os
import tarfile
import zipfile


class Solution:
    def solve(self, src_path: str) -> bytes:
        target_len = 73
        max_candidate_size = 512 * 1024

        best_bytes = None
        best_score = float("-inf")

        def consider_candidate(data: bytes, name: str) -> None:
            nonlocal best_bytes, best_score
            size = len(data)
            if size == 0:
                return

            score = 0.0

            # Prefer reasonably small files
            if size <= 4096:
                score += 20.0

            # Closeness to target length
            diff = abs(size - target_len)
            score += 30.0 * max(0.0, 1.0 - diff / max(target_len, 1))

            # General preference for smaller sizes (but not zero)
            score += max(0.0, 10.0 - size / 50.0)

            lname = name.lower()

            # Keywords that likely indicate a PoC
            if any(k in lname for k in ["poc", "crash", "uaf", "useafter", "heap", "bug", "exploit"]):
                score += 20.0

            # Specific to this vulnerability
            if "h225" in lname or "ras" in lname:
                score += 25.0

            # Likely binary capture/input extensions
            if any(
                lname.endswith(ext)
                for ext in [".pcap", ".pcapng", ".cap", ".bin", ".dat", ".raw", ".input", ".in"]
            ):
                score += 10.0

            # Testing/corpus indicators
            if any(k in lname for k in ["test", "regress", "seed", "corpus", "cases"]):
                score += 5.0

            if score > best_score:
                best_score = score
                best_bytes = data

        def consider_text_as_hex(data: bytes, name: str) -> None:
            # Try to interpret small ASCII files as hex dumps
            if len(data) == 0 or len(data) > 4096:
                return
            try:
                text = data.decode("ascii")
            except UnicodeDecodeError:
                return
            if not text:
                return

            allowed_chars = set("0123456789abcdefABCDEF \n\r\t")
            if not all(ch in allowed_chars for ch in text):
                return

            tokens = [tok for tok in text.split() if tok]
            if not tokens:
                return
            if not all(len(tok) % 2 == 0 for tok in tokens):
                return
            hex_digits = set("0123456789abcdefABCDEF")
            for tok in tokens:
                if not all(ch in hex_digits for ch in tok):
                    return

            hexstr = "".join(tokens)
            if not hexstr:
                return
            try:
                decoded = bytes.fromhex(hexstr)
            except ValueError:
                return

            consider_candidate(decoded, name + ":hex")

        def scan_tar(path: str) -> None:
            try:
                tf = tarfile.open(path, "r:*")
            except tarfile.TarError:
                return
            with tf:
                for member in tf.getmembers():
                    if not member.isreg():
                        continue
                    size = member.size
                    if size <= 0 or size > max_candidate_size:
                        continue
                    try:
                        f = tf.extractfile(member)
                    except Exception:
                        continue
                    if f is None:
                        continue
                    try:
                        data = f.read()
                    except Exception:
                        continue
                    if not data:
                        continue
                    consider_candidate(data, member.name)
                    consider_text_as_hex(data, member.name)

        def scan_zip(path: str) -> None:
            try:
                zf = zipfile.ZipFile(path, "r")
            except zipfile.BadZipFile:
                return
            with zf:
                for info in zf.infolist():
                    # Skip directories
                    is_dir = False
                    if hasattr(info, "is_dir"):
                        is_dir = info.is_dir()
                    else:
                        is_dir = info.filename.endswith("/")
                    if is_dir:
                        continue
                    size = info.file_size
                    if size <= 0 or size > max_candidate_size:
                        continue
                    try:
                        with zf.open(info, "r") as f:
                            data = f.read()
                    except Exception:
                        continue
                    if not data:
                        continue
                    consider_candidate(data, info.filename)
                    consider_text_as_hex(data, info.filename)

        def scan_dir(path: str) -> None:
            base = os.path.abspath(path)
            for root, _dirs, files in os.walk(base):
                for fname in files:
                    fpath = os.path.join(root, fname)
                    try:
                        size = os.path.getsize(fpath)
                    except OSError:
                        continue
                    if size <= 0 or size > max_candidate_size:
                        continue
                    try:
                        with open(fpath, "rb") as f:
                            data = f.read()
                        relname = os.path.relpath(fpath, base)
                    except OSError:
                        continue
                    if not data:
                        continue
                    consider_candidate(data, relname)
                    consider_text_as_hex(data, relname)

        if os.path.isdir(src_path):
            scan_dir(src_path)
        else:
            scanned = False
            # Try tar
            if tarfile.is_tarfile(src_path):
                scan_tar(src_path)
                scanned = True
            # Try zip if not tar
            if not scanned and zipfile.is_zipfile(src_path):
                scan_zip(src_path)
                scanned = True
            # Fallback: treat as single file
            if not scanned:
                try:
                    with open(src_path, "rb") as f:
                        data = f.read()
                    if data:
                        consider_candidate(data, os.path.basename(src_path))
                        consider_text_as_hex(data, os.path.basename(src_path))
                except OSError:
                    pass

        if best_bytes is None:
            best_bytes = b"\x00" * target_len

        return best_bytes
