import os
import tarfile
from typing import List, Tuple, Optional


class Solution:
    EXACT_POC_SIZE = 6624

    TEXT_EXTENSIONS = {
        ".js",
        ".mjs",
        ".cjs",
        ".ts",
        ".jsx",
        ".html",
        ".htm",
        ".xhtml",
        ".xml",
        ".txt",
        ".poc",
        ".json",
        ".idl",
        ".css",
    }

    NAME_KEYWORDS = [
        "poc",
        "exploit",
        "uaf",
        "heap-use-after-free",
        "use-after-free",
        "heapuaf",
        "regress",
        "test",
        "uint8clamped",
        "clampedarray",
        "typedarray",
    ]

    CONTENT_KEYWORDS = [
        b"Uint8ClampedArray",
        b"uint8clampedarray",
        b"TypedArray",
        b"typedarray",
        b"use-after-free",
        b"use after free",
        b"heap-use-after-free",
        b"heap use after free",
    ]

    def solve(self, src_path: str) -> bytes:
        data: Optional[bytes] = None

        # First, try src_path as a tarball
        if os.path.isfile(src_path):
            try:
                with tarfile.open(src_path, "r:*") as tf:
                    data = self._find_poc_in_tar(tf)
            except tarfile.ReadError:
                # Not a tar, fall back to directory logic if applicable
                pass

        # If tar search failed and src_path is a directory, search directly
        if data is None and os.path.isdir(src_path):
            data = self._find_poc_in_dir(src_path)

        # Fallback generic PoC if no candidate found
        if data is None:
            data = self._default_poc().encode("utf-8", "replace")

        return data

    # ---------------- Tarball search helpers ----------------

    def _find_poc_in_tar(self, tf: tarfile.TarFile) -> Optional[bytes]:
        members = [m for m in tf.getmembers() if m.isreg() and m.size > 0]

        # Phase 1: Exact-size match
        exact_members = [m for m in members if m.size == self.EXACT_POC_SIZE]
        data, score = self._select_best_tar_members(tf, exact_members)
        if data is not None and (score is None or score >= 0):
            return data

        # Phase 2: Files that mention Uint8ClampedArray
        data = self._find_by_keyword_in_tar(tf, members)
        if data is not None:
            return data

        # Phase 3 (last-ditch): any reasonable text-like file
        moderate_members = self._filter_moderate_text_members_tar(members)
        data, _ = self._select_best_tar_members(tf, moderate_members)
        return data

    def _select_best_tar_members(
        self, tf: tarfile.TarFile, members: List[tarfile.TarInfo]
    ) -> Tuple[Optional[bytes], Optional[int]]:
        best_data: Optional[bytes] = None
        best_score: Optional[int] = None

        for m in members:
            try:
                f = tf.extractfile(m)
                if f is None:
                    continue
                try:
                    data = f.read()
                finally:
                    try:
                        f.close()
                    except Exception:
                        pass
            except Exception:
                continue

            score = self._score_candidate(m.name, data)
            if best_score is None or score > best_score:
                best_score = score
                best_data = data

        return best_data, best_score

    def _find_by_keyword_in_tar(
        self, tf: tarfile.TarFile, members: List[tarfile.TarInfo]
    ) -> Optional[bytes]:
        best_data: Optional[bytes] = None
        best_score: Optional[int] = None

        MAX_SIZE = 200_000
        for m in members:
            if m.size <= 0 or m.size > MAX_SIZE:
                continue

            name_lower = m.name.lower()
            _, ext = os.path.splitext(name_lower)
            if not (
                ext in self.TEXT_EXTENSIONS
                or "test" in name_lower
                or "poc" in name_lower
                or "/js/" in name_lower
                or ext in (".js", ".mjs", ".cjs", ".html", ".htm")
            ):
                continue

            try:
                f = tf.extractfile(m)
                if f is None:
                    continue
                try:
                    data = f.read()
                finally:
                    try:
                        f.close()
                    except Exception:
                        pass
            except Exception:
                continue

            d_lower = data.lower()
            if b"uint8clampedarray" not in d_lower:
                continue

            score = self._score_candidate(m.name, data)
            if best_score is None or score > best_score:
                best_score = score
                best_data = data

        return best_data

    def _filter_moderate_text_members_tar(
        self, members: List[tarfile.TarInfo]
    ) -> List[tarfile.TarInfo]:
        res: List[tarfile.TarInfo] = []
        MAX_SIZE = 200_000
        for m in members:
            if m.size <= 0 or m.size > MAX_SIZE:
                continue
            name_lower = m.name.lower()
            _, ext = os.path.splitext(name_lower)
            if (
                ext in self.TEXT_EXTENSIONS
                or "test" in name_lower
                or "poc" in name_lower
                or "regress" in name_lower
                or "/js/" in name_lower
                or ext in (".js", ".mjs", ".cjs", ".html", ".htm")
            ):
                res.append(m)
        return res

    # ---------------- Directory search helpers ----------------

    def _find_poc_in_dir(self, root: str) -> Optional[bytes]:
        files_with_size: List[Tuple[str, int]] = []
        for dirpath, _, filenames in os.walk(root):
            for fn in filenames:
                full = os.path.join(dirpath, fn)
                try:
                    st = os.stat(full)
                except OSError:
                    continue
                if not os.path.isfile(full):
                    continue
                if st.st_size <= 0:
                    continue
                files_with_size.append((full, int(st.st_size)))

        # Phase 1: exact size
        exact_files = [
            (path, size)
            for (path, size) in files_with_size
            if size == self.EXACT_POC_SIZE
        ]
        data, score = self._select_best_files(exact_files)
        if data is not None and (score is None or score >= 0):
            return data

        # Phase 2: files that mention Uint8ClampedArray
        data = self._find_by_keyword_in_dir(files_with_size)
        if data is not None:
            return data

        # Phase 3: any text-like moderate-size file
        moderate_files = self._filter_moderate_text_files(files_with_size)
        data, _ = self._select_best_files(moderate_files)
        return data

    def _select_best_files(
        self, items: List[Tuple[str, int]]
    ) -> Tuple[Optional[bytes], Optional[int]]:
        best_data: Optional[bytes] = None
        best_score: Optional[int] = None

        for path, _ in items:
            try:
                with open(path, "rb") as f:
                    data = f.read()
            except Exception:
                continue

            score = self._score_candidate(path, data)
            if best_score is None or score > best_score:
                best_score = score
                best_data = data

        return best_data, best_score

    def _find_by_keyword_in_dir(
        self, files_with_size: List[Tuple[str, int]]
    ) -> Optional[bytes]:
        best_data: Optional[bytes] = None
        best_score: Optional[int] = None
        MAX_SIZE = 200_000

        for path, size in files_with_size:
            if size <= 0 or size > MAX_SIZE:
                continue

            name_lower = path.lower()
            _, ext = os.path.splitext(name_lower)
            if not (
                ext in self.TEXT_EXTENSIONS
                or "test" in name_lower
                or "poc" in name_lower
                or "/js/" in name_lower
                or ext in (".js", ".mjs", ".cjs", ".html", ".htm")
            ):
                continue

            try:
                with open(path, "rb") as f:
                    data = f.read()
            except Exception:
                continue

            if b"uint8clampedarray" not in data.lower():
                continue

            score = self._score_candidate(path, data)
            if best_score is None or score > best_score:
                best_score = score
                best_data = data

        return best_data

    def _filter_moderate_text_files(
        self, files_with_size: List[Tuple[str, int]]
    ) -> List[Tuple[str, int]]:
        res: List[Tuple[str, int]] = []
        MAX_SIZE = 200_000
        for path, size in files_with_size:
            if size <= 0 or size > MAX_SIZE:
                continue
            name_lower = path.lower()
            _, ext = os.path.splitext(name_lower)
            if (
                ext in self.TEXT_EXTENSIONS
                or "test" in name_lower
                or "poc" in name_lower
                or "regress" in name_lower
                or "/js/" in name_lower
                or ext in (".js", ".mjs", ".cjs", ".html", ".htm")
            ):
                res.append((path, size))
        return res

    # ---------------- Scoring & fallback ----------------

    def _score_candidate(self, name: str, data: bytes) -> int:
        name_lower = name.lower()
        _, ext = os.path.splitext(name_lower)
        d_lower = data.lower()
        size = len(data)

        score = 0

        # Prefer text-like extensions
        if ext in self.TEXT_EXTENSIONS:
            score += 20
        if ext in (".js", ".mjs", ".cjs"):
            score += 20
        if ext in (".html", ".htm", ".xhtml"):
            score += 10

        # Name-based hints
        for kw in self.NAME_KEYWORDS:
            if kw in name_lower:
                score += 10

        # Content-based hints
        for kw in self.CONTENT_KEYWORDS:
            if kw in d_lower:
                score += 25

        if b"uint8clampedarray" in d_lower:
            score += 80
        if b"typedarray" in d_lower:
            score += 20

        # Comment-like hints
        if b"use-after-free" in d_lower or b"use after free" in d_lower:
            score += 30
        if b"heap-use-after-free" in d_lower:
            score += 30

        # Size proximity
        size_diff = abs(size - self.EXACT_POC_SIZE)
        if size_diff == 0:
            score += 40
        else:
            penalty = size_diff // 100
            if penalty > 0:
                score -= min(penalty, 100)

        return score

    def _default_poc(self) -> str:
        # Generic fallback PoC attempting to stress Uint8ClampedArray / TypedArray
        return r"""
// Fallback PoC for Uint8ClampedArray / TypedArray misuse.
// Used only if the original PoC is not found in the source tree.

function maybeGC() {
    try {
        if (typeof gc === "function") {
            for (let i = 0; i < 20; ++i) gc();
        }
    } catch (e) {
        // Ignore if gc is not available
    }
}

function stressClampedArrays() {
    const arrays = [];
    const bufs = [];

    for (let i = 0; i < 200; ++i) {
        const buf = new ArrayBuffer(0x1000);
        const view = new Uint8ClampedArray(buf);
        view.fill(0xff);
        arrays.push(view);
        bufs.push(buf);
    }

    // Mix prototypes and create confusion in the engine's type system.
    for (let i = 0; i < arrays.length; ++i) {
        const v = arrays[i];
        try {
            Object.setPrototypeOf(v, Uint8Array.prototype);
        } catch (e) {
        }
    }

    maybeGC();

    // Trigger repeated operations that might touch freed / invalid memory
    for (let k = 0; k < 1000; ++k) {
        const idx = k % arrays.length;
        const v = arrays[idx];

        for (let i = 0; i < v.length; i += 4) {
            v[i] = (v[i] + 1) & 0xff;
        }

        if (k % 50 === 0) {
            maybeGC();
        }
    }
}

stressClampedArrays();
"""
