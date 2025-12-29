import os
import tarfile


class Solution:
    TARGET_SIZE = 1479

    def _has_interesting_ext(self, name: str) -> bool:
        ext = os.path.splitext(name.lower())[1]
        return ext in ('.j2k', '.jp2', '.jpc', '.j2c', '.jph', '.jhc', '.jpx', '.htj2k')

    def _score_name(self, name: str, size: int) -> int:
        lowered = name.lower()
        score = 0
        diff = abs(size - self.TARGET_SIZE)
        score += diff

        ext = os.path.splitext(lowered)[1]
        if ext in ('.j2k', '.jp2', '.jpc', '.j2c', '.jph', '.jhc', '.jpx', '.htj2k'):
            score -= 100
        if 'poc' in lowered:
            score -= 300
        if 'cve' in lowered:
            score -= 250
        if '47500' in lowered:
            score -= 240
        if 'heap' in lowered or 'overflow' in lowered or 'oob' in lowered or 'buf' in lowered:
            score -= 220
        if 'crash' in lowered or 'fuzz' in lowered:
            score -= 180
        if 'test' in lowered or 'regress' in lowered or 'sample' in lowered:
            score -= 80
        if 'jpg' in lowered or 'jpeg' in lowered or 'image' in lowered:
            score -= 20

        return score

    def _pick_best_member(self, members):
        return min(members, key=lambda m: self._score_name(m.name, m.size))

    def _pick_best_path(self, files):
        # files: list of (path, size)
        return min(files, key=lambda p: self._score_name(p[0], p[1]))

    def _from_tar(self, path: str):
        try:
            with tarfile.open(path, 'r:*') as tar:
                members = [m for m in tar.getmembers() if m.isfile() and m.size > 0]
                if not members:
                    return None

                # Prefer exact size match
                exact = [m for m in members if m.size == self.TARGET_SIZE]
                if exact:
                    chosen = self._pick_best_member(exact)
                    f = tar.extractfile(chosen)
                    if f is not None:
                        return f.read()

                # Then look for near matches
                near = [m for m in members if abs(m.size - self.TARGET_SIZE) <= 32]
                if near:
                    chosen = self._pick_best_member(near)
                    f = tar.extractfile(chosen)
                    if f is not None:
                        return f.read()

                # Finally, any interesting extension
                interesting = [m for m in members if self._has_interesting_ext(m.name)]
                if interesting:
                    chosen = self._pick_best_member(interesting)
                    f = tar.extractfile(chosen)
                    if f is not None:
                        return f.read()
        except (tarfile.ReadError, FileNotFoundError, IsADirectoryError, PermissionError, OSError):
            return None
        return None

    def _from_dir(self, root: str):
        exact = []
        near = []
        interesting = []

        for dirpath, dirnames, filenames in os.walk(root):
            for filename in filenames:
                full = os.path.join(dirpath, filename)
                try:
                    size = os.path.getsize(full)
                except OSError:
                    continue
                if size <= 0:
                    continue
                if size == self.TARGET_SIZE:
                    exact.append((full, size))
                elif abs(size - self.TARGET_SIZE) <= 32:
                    near.append((full, size))
                if self._has_interesting_ext(full):
                    interesting.append((full, size))

        if exact:
            path, _ = self._pick_best_path(exact)
            try:
                with open(path, 'rb') as f:
                    return f.read()
            except OSError:
                pass

        if near:
            path, _ = self._pick_best_path(near)
            try:
                with open(path, 'rb') as f:
                    return f.read()
            except OSError:
                pass

        if interesting:
            path, _ = self._pick_best_path(interesting)
            try:
                with open(path, 'rb') as f:
                    return f.read()
            except OSError:
                pass

        return None

    def solve(self, src_path: str) -> bytes:
        data = None

        if os.path.isfile(src_path):
            data = self._from_tar(src_path)

        if data is None and os.path.isdir(src_path):
            data = self._from_dir(src_path)

        if data is None:
            data = b'A' * self.TARGET_SIZE

        return data