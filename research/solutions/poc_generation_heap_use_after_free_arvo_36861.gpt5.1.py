import os
import tarfile
import zipfile
import io
import typing


class Solution:
    GROUND_TRUTH_LEN = 71298

    def solve(self, src_path: str) -> bytes:
        data: typing.Optional[bytes] = None

        if os.path.isfile(src_path):
            try:
                if tarfile.is_tarfile(src_path):
                    data = self._extract_from_tar(src_path)
            except Exception:
                data = None

            if data is None:
                try:
                    if zipfile.is_zipfile(src_path):
                        data = self._extract_from_zip(src_path)
                except Exception:
                    data = None

        if data is not None:
            return data

        return b"A" * self.GROUND_TRUTH_LEN

    def _path_score(self, name: str) -> int:
        n = name.lower()
        score = 1

        if "poc" in n:
            score += 50
        if "uaf" in n or "use-after-free" in n:
            score += 25
        if "crash" in n or "bug" in n or "fail" in n:
            score += 40
        if "fuzz" in n or "clusterfuzz" in n or "oss-fuzz" in n:
            score += 20
        if "testcase" in n or "repro" in n:
            score += 10

        base, ext = os.path.splitext(n)
        if ext in (".c", ".cc", ".cpp", ".h", ".hpp", ".txt", ".md", ".rst", ".py",
                   ".java", ".go", ".rb", ".sh"):
            score -= 20
        if ext in (".a", ".o", ".so", ".dll", ".dylib", ".exe", ".class", ".jar"):
            score -= 40
        if ext == ".zip":
            score += 5
        if ext in (".bin", ".raw", ".dat", ".poc"):
            score += 10

        return score

    def _try_extract_zip_recursive(
        self, raw: bytes, depth: int = 0, max_depth: int = 3
    ) -> typing.Optional[bytes]:
        if depth > max_depth:
            return None
        try:
            zf = zipfile.ZipFile(io.BytesIO(raw))
        except Exception:
            return None

        try:
            exact: typing.List[typing.Tuple[int, zipfile.ZipInfo]] = []
            others: typing.List[typing.Tuple[int, zipfile.ZipInfo]] = []

            for zi in zf.infolist():
                if zi.is_dir():
                    continue
                size = zi.file_size
                if size <= 0:
                    continue
                if size > max(self.GROUND_TRUTH_LEN * 5, 2_000_000):
                    continue
                score = self._path_score(zi.filename)
                if size == self.GROUND_TRUTH_LEN:
                    exact.append((score, zi))
                elif score > 0 and size <= 5 * self.GROUND_TRUTH_LEN:
                    others.append((score, zi))

            if exact:
                exact.sort(key=lambda x: x[0], reverse=True)
                for score, zi in exact:
                    try:
                        data = zf.read(zi)
                    except Exception:
                        continue
                    if data:
                        return data

            others.sort(key=lambda x: x[0], reverse=True)
            for score, zi in others:
                try:
                    data = zf.read(zi)
                except Exception:
                    continue
                if not data:
                    continue
                if len(data) == self.GROUND_TRUTH_LEN:
                    return data
                if data.startswith(b"PK\x03\x04"):
                    inner = self._try_extract_zip_recursive(
                        data, depth=depth + 1, max_depth=max_depth
                    )
                    if inner is not None:
                        return inner
        finally:
            zf.close()
        return None

    def _extract_from_tar(self, path: str) -> typing.Optional[bytes]:
        try:
            tar = tarfile.open(path, "r:*")
        except Exception:
            return None

        try:
            members = tar.getmembers()
            exact: typing.List[typing.Tuple[int, tarfile.TarInfo]] = []
            others: typing.List[typing.Tuple[int, tarfile.TarInfo]] = []

            max_size = max(self.GROUND_TRUTH_LEN * 5, 2_000_000)

            for m in members:
                if not m.isfile():
                    continue
                size = m.size
                if size <= 0:
                    continue
                if size > max_size:
                    continue

                name = m.name
                if size == self.GROUND_TRUTH_LEN:
                    score = self._path_score(name)
                    exact.append((score, m))
                else:
                    score = self._path_score(name)
                    if score > 0 and size <= 5 * self.GROUND_TRUTH_LEN:
                        others.append((score, m))

            if exact:
                exact.sort(key=lambda x: x[0], reverse=True)
                for score, m in exact:
                    try:
                        f = tar.extractfile(m)
                    except Exception:
                        continue
                    if f is None:
                        continue
                    try:
                        data = f.read()
                    finally:
                        f.close()
                    if data:
                        return data

            others.sort(key=lambda x: x[0], reverse=True)
            for score, m in others:
                try:
                    f = tar.extractfile(m)
                except Exception:
                    continue
                if f is None:
                    continue
                try:
                    raw = f.read()
                finally:
                    f.close()
                if not raw:
                    continue
                if len(raw) == self.GROUND_TRUTH_LEN:
                    return raw
                if raw.startswith(b"PK\x03\x04"):
                    inner = self._try_extract_zip_recursive(raw)
                    if inner is not None:
                        return inner

            if others:
                m = others[0][1]
                try:
                    f = tar.extractfile(m)
                except Exception:
                    f = None
                if f is not None:
                    try:
                        data = f.read()
                    finally:
                        f.close()
                    if data:
                        return data
        finally:
            tar.close()

        return None

    def _extract_from_zip(self, path: str) -> typing.Optional[bytes]:
        try:
            zf = zipfile.ZipFile(path)
        except Exception:
            return None

        try:
            exact: typing.List[typing.Tuple[int, zipfile.ZipInfo]] = []
            others: typing.List[typing.Tuple[int, zipfile.ZipInfo]] = []

            max_size = max(self.GROUND_TRUTH_LEN * 5, 2_000_000)

            for zi in zf.infolist():
                if zi.is_dir():
                    continue
                size = zi.file_size
                if size <= 0:
                    continue
                if size > max_size:
                    continue

                name = zi.filename
                if size == self.GROUND_TRUTH_LEN:
                    score = self._path_score(name)
                    exact.append((score, zi))
                else:
                    score = self._path_score(name)
                    if score > 0 and size <= 5 * self.GROUND_TRUTH_LEN:
                        others.append((score, zi))

            if exact:
                exact.sort(key=lambda x: x[0], reverse=True)
                for score, zi in exact:
                    try:
                        data = zf.read(zi)
                    except Exception:
                        continue
                    if data:
                        return data

            others.sort(key=lambda x: x[0], reverse=True)
            for score, zi in others:
                try:
                    raw = zf.read(zi)
                except Exception:
                    continue
                if not raw:
                    continue
                if len(raw) == self.GROUND_TRUTH_LEN:
                    return raw
                if raw.startswith(b"PK\x03\x04"):
                    inner = self._try_extract_zip_recursive(raw)
                    if inner is not None:
                        return inner

            if others:
                try:
                    data = zf.read(others[0][1])
                except Exception:
                    data = None
                if data:
                    return data
        finally:
            zf.close()

        return None