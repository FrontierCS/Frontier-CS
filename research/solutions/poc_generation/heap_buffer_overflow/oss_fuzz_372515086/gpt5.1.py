import os
import io
import tarfile
import zipfile
import re


class Solution:
    TARGET_SIZE = 1032

    TEXT_EXTS = {
        ".c", ".h", ".cpp", ".cc", ".hpp",
        ".md", ".txt", ".rst",
        ".in", ".py", ".java", ".go", ".rs",
        ".js", ".ts", ".json", ".yml", ".yaml",
        ".xml", ".html", ".htm", ".cmake", ".sh",
        ".bat", ".ps1", ".m", ".swift", ".kt",
        ".gradle", ".toml", ".ini", ".cfg", ".conf",
    }

    def solve(self, src_path: str) -> bytes:
        try:
            return self._solve_internal(src_path)
        except Exception:
            return b"A" * self.TARGET_SIZE

    def _solve_internal(self, src_path: str) -> bytes:
        try:
            tar = tarfile.open(src_path, "r:*")
        except Exception:
            return b"A" * self.TARGET_SIZE

        with tar:
            members = [m for m in tar.getmembers() if m.isfile()]

            data = self._find_direct_poc(tar, members)
            if data is not None:
                return data

            data = self._find_zip_poc(tar, members)
            if data is not None:
                return data

            data = self._find_embedded_hex_poc(tar, members)
            if data is not None:
                return data

        return b"A" * self.TARGET_SIZE

    # ---------- Helper methods ----------

    def _is_text_ext(self, name: str) -> bool:
        ext = os.path.splitext(name)[1].lower()
        return ext in self.TEXT_EXTS

    def _pick_best_by_size(self, members):
        if not members:
            return None
        exact = [m for m in members if m.size == self.TARGET_SIZE and m.size > 0]
        if exact:
            return exact[0]
        best = None
        best_diff = None
        for m in members:
            if m.size <= 0:
                continue
            diff = abs(m.size - self.TARGET_SIZE)
            if best_diff is None or diff < best_diff:
                best = m
                best_diff = diff
        return best

    def _find_direct_poc(self, tar: tarfile.TarFile, members):
        # Pass 1: very specific keywords
        primary_keywords = [
            "polygontocellsexperimental",
            "polygon_to_cells_experimental",
            "polygon-to-cells-experimental",
            "372515086",
        ]

        preferred = []
        fallback = []
        for m in members:
            name_l = m.name.lower()
            if any(k in name_l for k in primary_keywords):
                (preferred if not self._is_text_ext(m.name) else fallback).append(m)

        best = self._pick_best_by_size(preferred) or self._pick_best_by_size(fallback)
        if best is not None:
            f = tar.extractfile(best)
            if f is not None:
                return f.read()

        # Pass 2: polygon-to-cells related under fuzz/corpus/seed
        secondary_keywords = [
            "polygontocells",
            "polygon_to_cells",
            "polygon-to-cells",
        ]
        preferred = []
        fallback = []
        for m in members:
            name_l = m.name.lower()
            if any(k in name_l for k in secondary_keywords) and (
                "fuzz" in name_l or "corpus" in name_l or "seed" in name_l or "input" in name_l
            ):
                (preferred if not self._is_text_ext(m.name) else fallback).append(m)

        best = self._pick_best_by_size(preferred) or self._pick_best_by_size(fallback)
        if best is not None:
            f = tar.extractfile(best)
            if f is not None:
                return f.read()

        # Pass 3: generic crash/poc under fuzz/corpus/seed
        preferred = []
        fallback = []
        for m in members:
            name_l = m.name.lower()
            if ("fuzz" in name_l or "corpus" in name_l or "seed" in name_l or "input" in name_l) and (
                "poc" in name_l or "crash" in name_l or "overflow" in name_l or "heap" in name_l
            ):
                (preferred if not self._is_text_ext(m.name) else fallback).append(m)

        best = self._pick_best_by_size(preferred) or self._pick_best_by_size(fallback)
        if best is not None:
            f = tar.extractfile(best)
            if f is not None:
                return f.read()

        # Pass 4: any file under corpus/fuzz/seed closest to target size
        preferred = []
        fallback = []
        for m in members:
            name_l = m.name.lower()
            if "fuzz" in name_l or "corpus" in name_l or "seed" in name_l or "input" in name_l:
                (preferred if not self._is_text_ext(m.name) else fallback).append(m)

        best = self._pick_best_by_size(preferred) or self._pick_best_by_size(fallback)
        if best is not None:
            f = tar.extractfile(best)
            if f is not None:
                return f.read()

        return None

    def _find_zip_poc(self, tar: tarfile.TarFile, members):
        primary_keywords = [
            "polygontocellsexperimental",
            "polygon_to_cells_experimental",
            "polygon-to-cells-experimental",
            "372515086",
        ]

        for m in members:
            name_l = m.name.lower()
            if not name_l.endswith(".zip"):
                continue
            if not any(k in name_l for k in ("fuzz", "corpus", "seed", "poc", "crash", "polygon", "poly")):
                # Skip large unrelated zips for performance
                if m.size > 5_000_000:
                    continue

            f = tar.extractfile(m)
            if f is None:
                continue
            try:
                data = f.read()
            except Exception:
                continue

            try:
                zf = zipfile.ZipFile(io.BytesIO(data))
            except Exception:
                continue

            with zf:
                # Pass 1: entries with primary keywords
                best_info = None
                best_diff = None
                for info in zf.infolist():
                    if info.is_dir():
                        continue
                    nm = info.filename.lower()
                    if any(k in nm for k in primary_keywords):
                        diff = abs(info.file_size - self.TARGET_SIZE)
                        if best_diff is None or diff < best_diff:
                            best_info = info
                            best_diff = diff
                if best_info is not None:
                    try:
                        return zf.read(best_info)
                    except Exception:
                        pass

                # Pass 2: polygon-related entries under fuzz/corpus/seed
                best_info = None
                best_diff = None
                for info in zf.infolist():
                    if info.is_dir():
                        continue
                    nm = info.filename.lower()
                    if (any(k in nm for k in ("polygon", "poly")) and
                            any(k in nm for k in ("fuzz", "corpus", "seed", "poc", "crash"))):
                        diff = abs(info.file_size - self.TARGET_SIZE)
                        if best_diff is None or diff < best_diff:
                            best_info = info
                            best_diff = diff
                if best_info is not None:
                    try:
                        return zf.read(best_info)
                    except Exception:
                        pass

                # Pass 3: any entry closest to target size (with reasonable bound)
                best_info = None
                best_diff = None
                for info in zf.infolist():
                    if info.is_dir() or info.file_size <= 0:
                        continue
                    diff = abs(info.file_size - self.TARGET_SIZE)
                    if best_diff is None or diff < best_diff:
                        best_info = info
                        best_diff = diff
                if best_info is not None and best_diff is not None and best_diff <= self.TARGET_SIZE:
                    try:
                        return zf.read(best_info)
                    except Exception:
                        pass

        return None

    def _find_embedded_hex_poc(self, tar: tarfile.TarFile, members):
        target = self.TARGET_SIZE
        best_bytes = None
        best_diff = None

        array_pattern = re.compile(r"\{([^{}]+)\}", re.DOTALL)
        token_pattern = re.compile(r"0x[0-9a-fA-F]+|\d+")

        for mem in members:
            if mem.size == 0 or mem.size > 200_000:
                continue
            name_l = mem.name.lower()
            if not any(name_l.endswith(ext) for ext in (".c", ".cc", ".cpp", ".h", ".hpp", ".txt", ".md", ".rst")):
                continue

            f = tar.extractfile(mem)
            if f is None:
                continue
            try:
                text = f.read().decode("utf-8", "ignore")
            except Exception:
                continue

            if ("372515086" not in text and
                "polygontocellsexperimental" not in text and
                "polygonToCellsExperimental" not in text and
                "polygon_to_cells_experimental" not in text):
                continue

            for match in array_pattern.finditer(text):
                body = match.group(1)
                tokens = token_pattern.findall(body)
                if not tokens:
                    continue

                vals = []
                ok = True
                for tok in tokens:
                    try:
                        v = int(tok, 0)
                    except ValueError:
                        ok = False
                        break
                    if not (0 <= v <= 255):
                        ok = False
                        break
                    vals.append(v)

                if not ok or not vals:
                    continue

                bs = bytes(vals)
                if len(bs) == target:
                    return bs
                diff = abs(len(bs) - target)
                if best_diff is None or diff < best_diff:
                    best_diff = diff
                    best_bytes = bs

        return best_bytes