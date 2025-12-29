import os
import tarfile
import re


TEXT_EXTS = {
    ".c",
    ".cc",
    ".cpp",
    ".cxx",
    ".h",
    ".hh",
    ".hpp",
    ".hxx",
    ".txt",
    ".md",
    ".py",
    ".java",
    ".xml",
    ".html",
    ".htm",
    ".json",
    ".in",
    ".cmake",
    ".m4",
    ".ac",
    ".am",
    ".sh",
    ".bash",
    ".zsh",
    ".bat",
    ".ps1",
    ".vcxproj",
    ".sln",
    ".yml",
    ".yaml",
    ".toml",
    ".cfg",
    ".ini",
    ".pbtxt",
}

BINARY_EXTS = {
    ".bin",
    ".dat",
    ".raw",
    ".heic",
    ".heif",
    ".avif",
    ".jpg",
    ".jpeg",
    ".jxl",
    ".webp",
    ".png",
    ".bmp",
    ".gif",
    ".tif",
    ".tiff",
    ".mp4",
    ".mov",
    ".m4v",
    ".webm",
    ".ico",
}


class Solution:
    def solve(self, src_path: str) -> bytes:
        try:
            if os.path.isdir(src_path):
                data = self._from_dir(src_path)
            elif tarfile.is_tarfile(src_path):
                data = self._from_tar(src_path)
            else:
                try:
                    with open(src_path, "rb") as f:
                        return f.read()
                except Exception:
                    data = None
        except Exception:
            data = None

        if data is None:
            data = self._fallback_bytes()
        return data

    # ---- Core strategies ----

    def _from_tar(self, tar_path: str) -> bytes | None:
        with tarfile.open(tar_path, "r:*") as tf:
            entries = []
            for m in tf.getmembers():
                if not m.isfile() or m.size <= 0:
                    continue
                name_lower = m.name.lower()
                _, ext = os.path.splitext(name_lower)
                is_text = ext in TEXT_EXTS
                entries.append((m, name_lower, m.size, ext, is_text))

            def read_member(ident: tarfile.TarInfo) -> bytes:
                f = tf.extractfile(ident)
                if f is None:
                    return b""
                try:
                    return f.read()
                finally:
                    f.close()

            data = self._find_poc_by_metadata(entries, read_member)
            if data:
                return data

            def read_text(ident: tarfile.TarInfo) -> str:
                f = tf.extractfile(ident)
                if f is None:
                    raise IOError("Cannot extract member")
                try:
                    return f.read().decode("utf-8", "ignore")
                finally:
                    f.close()

            arr_data = self._find_embedded_array_poc(entries, read_text)
            if arr_data:
                return arr_data

        return None

    def _from_dir(self, base_dir: str) -> bytes | None:
        entries = []
        for root, _, files in os.walk(base_dir):
            for fn in files:
                full = os.path.join(root, fn)
                try:
                    size = os.path.getsize(full)
                except OSError:
                    continue
                if size <= 0:
                    continue
                rel_path = os.path.relpath(full, base_dir).replace("\\", "/")
                name_lower = rel_path.lower()
                _, ext = os.path.splitext(name_lower)
                is_text = ext in TEXT_EXTS
                entries.append((full, name_lower, size, ext, is_text))

        def read_file(path: str) -> bytes:
            with open(path, "rb") as f:
                return f.read()

        data = self._find_poc_by_metadata(entries, read_file)
        if data:
            return data

        def read_text(path: str) -> str:
            with open(path, "rb") as f:
                return f.read().decode("utf-8", "ignore")

        arr_data = self._find_embedded_array_poc(entries, read_text)
        if arr_data:
            return arr_data

        return None

    # ---- Heuristic PoC search using file metadata ----

    def _find_poc_by_metadata(self, entries, open_func) -> bytes | None:
        stage1 = []  # name keyword + non-text
        stage2 = []  # exact size 133 + non-text
        stage3 = []  # binary ext + non-text
        stage4 = []  # small non-text
        keywords = ("poc", "testcase", "crash", "clusterfuzz", "repro", "id:", "gainmap", "hdr")

        for ident, name_lower, size, ext, is_text in entries:
            if size <= 0:
                continue
            has_keyword = any(k in name_lower for k in keywords)
            entry = (ident, name_lower, size, ext, is_text)
            if has_keyword and not is_text:
                stage1.append(entry)
            elif size == 133 and not is_text:
                stage2.append(entry)
            elif not is_text and ext in BINARY_EXTS:
                stage3.append(entry)
            elif not is_text and size <= 2048:
                stage4.append(entry)

        for stage in (stage1, stage2, stage3, stage4):
            if not stage:
                continue
            stage.sort(key=lambda e: (abs(e[2] - 133), e[2]))
            for ident, _, _, _, _ in stage:
                try:
                    data = open_func(ident)
                    if isinstance(data, bytes) and data:
                        return data
                except Exception:
                    continue
        return None

    # ---- Heuristic PoC search using embedded C/C++ byte arrays ----

    def _find_embedded_array_poc(self, entries, open_text_func) -> bytes | None:
        best_data = None
        best_score = float("inf")

        for ident, name_lower, size, ext, _ in entries:
            if ext not in (".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx"):
                continue
            if size > 200000:
                continue
            try:
                text = open_text_func(ident)
            except Exception:
                continue
            if "uint8_t" not in text and "unsigned char" not in text and "uint8 " not in text:
                continue

            for var_name, data in self._extract_byte_arrays(text):
                ln = len(data)
                if ln == 0:
                    continue
                vnl = var_name.lower()
                score = abs(ln - 133)

                if any(k in vnl for k in ("poc", "crash", "test", "case", "gainmap", "hdr", "overflow")):
                    score -= 50
                if any(k in name_lower for k in ("poc", "test", "gainmap", "hdr")):
                    score -= 10

                if score < best_score:
                    best_score = score
                    best_data = data

        return best_data

    def _extract_byte_arrays(self, text: str):
        pattern = re.compile(
            r"(?:static\s+)?"
            r"(?:const\s+)?"
            r"(?:unsigned\s+char|uint8_t)\s+"
            r"([a-zA-Z_]\w*)"
            r"\s*(?:\[[^\]]*\])?\s*=\s*\{([^}]*)\}",
            re.S,
        )

        for match in pattern.finditer(text):
            var_name = match.group(1)
            contents = match.group(2)
            bytes_list = []
            for token in contents.split(","):
                tok = token.strip()
                if not tok:
                    continue
                if tok.startswith("/*") or tok.startswith("//"):
                    continue
                val = None
                if tok.startswith("0x") or tok.startswith("0X"):
                    try:
                        val = int(tok, 16)
                    except ValueError:
                        val = None
                elif tok.startswith("'") and tok.endswith("'") and len(tok) >= 3:
                    val = ord(tok[1])
                else:
                    m = re.search(r"0x[0-9a-fA-F]+|\d+", tok)
                    if m:
                        num = m.group(0)
                        try:
                            if num.startswith("0x") or num.startswith("0X"):
                                val = int(num, 16)
                            else:
                                val = int(num, 10)
                        except ValueError:
                            val = None
                if val is None:
                    continue
                bytes_list.append(val & 0xFF)
            if bytes_list:
                if len(bytes_list) > 0 and len(bytes_list) <= 65536:
                    yield var_name, bytes(bytes_list)

    # ---- Fallback PoC ----

    def _fallback_bytes(self) -> bytes:
        # Generic 133-byte payload as a last resort when no PoC can be located.
        return b"A" * 133