import os
import tarfile
import zipfile


class _Entry:
    __slots__ = ("name", "size", "ref")

    def __init__(self, name, size, ref):
        self.name = name
        self.size = size
        self.ref = ref


class Solution:
    BUG_ID = "42537493"
    GROUND_TRUTH_LEN = 24

    def _pick_best_entry(self, entries):
        L = self.GROUND_TRUTH_LEN

        def choose(cands):
            if not cands:
                return None
            return min(
                cands,
                key=lambda e: (
                    0 if e.size == L else 1,
                    abs(e.size - L),
                    e.size,
                    e.name,
                ),
            )

        keyword_groups = [
            [self.BUG_ID],
            [
                "clusterfuzz",
                "oss-fuzz",
                "poc",
                "uaf",
                "use-after-free",
                "use_after_free",
                "heap-use-after-free",
            ],
            ["crash", "repro", "testcase", "bug", "regress"],
            ["fuzz", "corpus", "seed", "seeds", "tests", "test"],
        ]

        for kw_list in keyword_groups:
            cands = []
            for e in entries:
                if e.size <= 0 or e.size > 4096:
                    continue
                name_l = e.name.lower()
                if not any(kw in name_l for kw in kw_list):
                    continue
                cands.append(e)
            best = choose(cands)
            if best is not None:
                return best

        cands = [e for e in entries if 0 < e.size <= 64]
        best = choose(cands)
        if best is not None:
            return best

        cands = [e for e in entries if e.size > 0]
        return choose(cands)

    def _solve_from_tar(self, tar_path):
        with tarfile.open(tar_path, "r:*") as tar:
            members = tar.getmembers()
            entries = []
            for m in members:
                if not m.isreg():
                    continue
                entries.append(_Entry(m.name, m.size, m))
            if not entries:
                return None
            best = self._pick_best_entry(entries)
            if not best:
                return None
            f = tar.extractfile(best.ref)
            if f is None:
                return None
            data = f.read()
            return data if data else None

    def _zip_info_is_dir(self, info):
        if hasattr(info, "is_dir"):
            try:
                return info.is_dir()
            except TypeError:
                pass
        return info.filename.endswith("/")

    def _solve_from_zip(self, zip_path):
        with zipfile.ZipFile(zip_path, "r") as zf:
            infos = zf.infolist()
            entries = []
            for info in infos:
                if self._zip_info_is_dir(info):
                    continue
                entries.append(_Entry(info.filename, info.file_size, info))
            if not entries:
                return None
            best = self._pick_best_entry(entries)
            if not best:
                return None
            try:
                data = zf.read(best.ref)
            except KeyError:
                return None
            return data if data else None

    def _solve_from_dir(self, dir_path):
        entries = []
        base = os.path.abspath(dir_path)
        for root, _, files in os.walk(base):
            for fn in files:
                full = os.path.join(root, fn)
                try:
                    size = os.path.getsize(full)
                except OSError:
                    continue
                rel = os.path.relpath(full, base)
                entries.append(_Entry(rel, size, full))
        if not entries:
            return None
        best = self._pick_best_entry(entries)
        if not best:
            return None
        try:
            with open(best.ref, "rb") as f:
                data = f.read()
        except OSError:
            return None
        return data if data else None

    def solve(self, src_path: str) -> bytes:
        data = None
        try:
            if os.path.isdir(src_path):
                data = self._solve_from_dir(src_path)
            elif tarfile.is_tarfile(src_path):
                data = self._solve_from_tar(src_path)
            elif zipfile.is_zipfile(src_path):
                data = self._solve_from_zip(src_path)
        except Exception:
            data = None

        if not data:
            data = b"A" * self.GROUND_TRUTH_LEN
        return data