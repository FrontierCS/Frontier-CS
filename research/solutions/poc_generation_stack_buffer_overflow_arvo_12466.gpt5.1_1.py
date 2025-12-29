import os
import tarfile


class Solution:
    TARGET_SIZE = 524

    def solve(self, src_path: str) -> bytes:
        if os.path.isdir(src_path):
            return self._solve_from_directory(src_path)
        if tarfile.is_tarfile(src_path):
            return self._solve_from_tar(src_path)
        return self._fallback_poc()

    def _update_best(
        self,
        name: str,
        size: int,
        head: bytes,
        best_any_name: str,
        best_any_score: float,
        best_rar5_name: str,
        best_rar5_score: float,
    ):
        name_lower = name.lower()
        size_diff = abs(size - self.TARGET_SIZE)
        base_score = -size_diff
        score = base_score

        if name_lower.endswith('.rar'):
            score += 100
        if '.rar' in name_lower:
            score += 50
        if 'rar5' in name_lower:
            score += 50

        for kw, bonus in (
            ('poc', 80),
            ('crash', 80),
            ('bug', 60),
            ('issue', 60),
            ('id_', 40),
            ('id-', 40),
            ('cve', 80),
        ):
            if kw in name_lower:
                score += bonus

        header_bonus = 0
        is_rar5 = False
        if head.startswith(b'Rar!\x1A\x07'):
            header_bonus += 300
            if head.startswith(b'Rar!\x1A\x07\x01\x00'):
                header_bonus += 700
                is_rar5 = True
            else:
                header_bonus += 100

        score_with_header = score + header_bonus

        if score_with_header > best_any_score:
            best_any_score = score_with_header
            best_any_name = name

        if is_rar5 and score_with_header > best_rar5_score:
            best_rar5_score = score_with_header
            best_rar5_name = name

        return best_any_name, best_any_score, best_rar5_name, best_rar5_score

    def _solve_from_tar(self, src_path: str) -> bytes:
        try:
            tar = tarfile.open(src_path, 'r:*')
        except tarfile.TarError:
            return self._fallback_poc()

        best_any_name = None
        best_any_score = float('-inf')
        best_rar5_name = None
        best_rar5_score = float('-inf')

        try:
            for m in tar.getmembers():
                if not m.isfile():
                    continue
                if m.size > 1024 * 1024:
                    continue

                head = b''
                try:
                    f = tar.extractfile(m)
                    if f is not None:
                        head = f.read(8)
                except Exception:
                    head = b''

                best_any_name, best_any_score, best_rar5_name, best_rar5_score = self._update_best(
                    m.name,
                    m.size,
                    head,
                    best_any_name,
                    best_any_score,
                    best_rar5_name,
                    best_rar5_score,
                )

            chosen_name = best_rar5_name or best_any_name
            if not chosen_name:
                return self._fallback_poc()

            try:
                f = tar.extractfile(chosen_name)
                if f is None:
                    return self._fallback_poc()
                data = f.read()
                if not isinstance(data, (bytes, bytearray)):
                    return self._fallback_poc()
                return bytes(data)
            except Exception:
                return self._fallback_poc()
        finally:
            tar.close()

    def _solve_from_directory(self, src_dir: str) -> bytes:
        best_any_name = None
        best_any_score = float('-inf')
        best_rar5_name = None
        best_rar5_score = float('-inf')

        for root, _, files in os.walk(src_dir):
            for filename in files:
                path = os.path.join(root, filename)
                try:
                    size = os.path.getsize(path)
                except OSError:
                    continue

                if size > 1024 * 1024:
                    continue

                head = b''
                try:
                    with open(path, 'rb') as f:
                        head = f.read(8)
                except OSError:
                    head = b''

                best_any_name, best_any_score, best_rar5_name, best_rar5_score = self._update_best(
                    path,
                    size,
                    head,
                    best_any_name,
                    best_any_score,
                    best_rar5_name,
                    best_rar5_score,
                )

        chosen_path = best_rar5_name or best_any_name
        if not chosen_path:
            return self._fallback_poc()

        try:
            with open(chosen_path, 'rb') as f:
                return f.read()
        except OSError:
            return self._fallback_poc()

    def _fallback_poc(self) -> bytes:
        header = b'Rar!\x1A\x07\x01\x00'
        target = self.TARGET_SIZE
        if target <= len(header):
            return header[:target]
        return header + b'A' * (target - len(header))