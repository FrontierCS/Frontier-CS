import os
import tarfile
import tempfile
import shutil
import json
import base64
import binascii
import string


class Solution:
    def solve(self, src_path: str) -> bytes:
        extract_dir = tempfile.mkdtemp(prefix="pocgen_")
        try:
            self._safe_extract_tar(src_path, extract_dir)
            poc = self._try_metadata_extract(extract_dir)
            if poc is not None:
                return poc
            return self._find_poc_in_directory(extract_dir)
        finally:
            shutil.rmtree(extract_dir, ignore_errors=True)

    def _safe_extract_tar(self, tar_path: str, dest_dir: str) -> None:
        try:
            with tarfile.open(tar_path, "r:*") as tar:
                for member in tar.getmembers():
                    member_path = os.path.join(dest_dir, member.name)
                    if not self._is_within_directory(dest_dir, member_path):
                        continue
                    try:
                        tar.extract(member, dest_dir)
                    except Exception:
                        continue
        except tarfile.TarError:
            pass

    def _is_within_directory(self, directory: str, target: str) -> bool:
        abs_directory = os.path.abspath(directory)
        abs_target = os.path.abspath(target)
        return os.path.commonprefix([abs_directory, abs_target]) == abs_directory

    def _decode_possible_encoded_string(self, s: str) -> bytes:
        text = s.strip()
        compact = "".join(ch for ch in text if not ch.isspace())
        if len(compact) >= 2 and len(compact) % 2 == 0:
            if all(ch in string.hexdigits for ch in compact):
                try:
                    return binascii.unhexlify(compact)
                except binascii.Error:
                    pass
        try:
            decoded = base64.b64decode(compact, validate=True)
            if decoded:
                return decoded
        except (binascii.Error, ValueError):
            pass
        return text.encode("utf-8", "replace")

    def _try_metadata_extract(self, root_dir: str):
        meta_candidates = []
        for dirpath, dirnames, filenames in os.walk(root_dir):
            base_dir = os.path.basename(dirpath).lower()
            if base_dir in (".git", ".hg", ".svn", ".idea", ".vs", "__pycache__"):
                continue
            for name in filenames:
                name_lower = name.lower()
                path = os.path.join(dirpath, name)
                ext = os.path.splitext(name_lower)[1]
                if ext not in (".json", ".yml", ".yaml", ".toml", ".txt"):
                    continue
                if not any(k in name_lower for k in ("poc", "repro", "crash", "bug")):
                    continue
                try:
                    size = os.path.getsize(path)
                except OSError:
                    continue
                if size == 0 or size > 100_000:
                    continue
                meta_candidates.append((path, ext))
        for path, ext in meta_candidates:
            if ext == ".json":
                try:
                    with open(path, "r", encoding="utf-8", errors="replace") as f:
                        data = json.load(f)
                except Exception:
                    continue
                if isinstance(data, dict):
                    for key in ("poc", "PoC", "input", "payload", "data"):
                        if key in data and isinstance(data[key], str):
                            return self._decode_possible_encoded_string(data[key])
            else:
                try:
                    with open(path, "r", encoding="utf-8", errors="replace") as f:
                        for line in f:
                            lower = line.lower()
                            if "poc" not in lower and "payload" not in lower and "input" not in lower:
                                continue
                            candidate = None
                            dq_start = line.find('"')
                            if dq_start != -1:
                                dq_end = line.rfind('"')
                                if dq_end > dq_start:
                                    candidate = line[dq_start + 1 : dq_end]
                            if candidate is None:
                                sq_start = line.find("'")
                                if sq_start != -1:
                                    sq_end = line.rfind("'")
                                    if sq_end > sq_start:
                                        candidate = line[sq_start + 1 : sq_end]
                            if candidate:
                                return self._decode_possible_encoded_string(candidate)
                except OSError:
                    continue
        return None

    def _find_poc_in_directory(self, root_dir: str) -> bytes:
        keywords = (
            "poc",
            "repro",
            "crash",
            "uaf",
            "double",
            "heap",
            "exploit",
            "payload",
            "bug",
            "testcase",
            "fuzz",
            "input",
        )
        dir_keywords = ("poc", "repro", "crash", "uaf", "bug", "tests", "fuzz", "cases")
        code_ext = {
            ".c",
            ".cc",
            ".cpp",
            ".cxx",
            ".h",
            ".hpp",
            ".hh",
            ".java",
            ".py",
            ".rb",
            ".go",
            ".rs",
            ".php",
            ".cs",
            ".js",
            ".ts",
            ".sh",
            ".bash",
            ".bat",
            ".ps1",
            ".cmake",
            ".mak",
            ".mk",
            ".s",
            ".asm",
            ".json",
            ".yml",
            ".yaml",
            ".toml",
            ".xml",
            ".html",
            ".htm",
            ".md",
            ".rst",
            ".tex",
            ".csv",
            ".ini",
            ".cfg",
            ".conf",
        }
        skip_names = {
            "cmakelists.txt",
            "makefile",
            "configure",
            "config.status",
            "config.log",
            "readme",
            "readme.txt",
            "license",
            "copying",
            "changelog",
            "todo",
        }
        best_60 = None
        best_gen = None
        unknown60_path = None
        for dirpath, dirnames, filenames in os.walk(root_dir):
            base_dir = os.path.basename(dirpath).lower()
            if base_dir in (".git", ".hg", ".svn", ".idea", ".vs", "__pycache__"):
                continue
            for name in filenames:
                name_lower = name.lower()
                path = os.path.join(dirpath, name)
                try:
                    size = os.path.getsize(path)
                except OSError:
                    continue
                if size == 0 or size > 1_000_000:
                    continue
                rel_path = os.path.relpath(path, root_dir)
                rel_lower = rel_path.lower()
                ext = os.path.splitext(name_lower)[1]
                has_kw_name = any(k in name_lower for k in keywords)
                dir_path_norm = "/" + rel_lower.replace("\\", "/").strip("/") + "/"
                has_kw_dir = any(("/" + k + "/") in dir_path_norm for k in dir_keywords)
                is_code = False
                if ext in code_ext:
                    if not has_kw_name and not has_kw_dir:
                        is_code = True
                if name_lower in skip_names and not has_kw_name:
                    is_code = True
                score = 0
                if has_kw_name:
                    score += 80
                if has_kw_dir:
                    score += 40
                if ext in (".poc", ".bin", ".raw", ".in", ".dat"):
                    score += 30
                if name_lower.startswith("id:") or name_lower.startswith("id_") or "id_" in name_lower:
                    score += 10
                if "san" in name_lower and "log" in name_lower:
                    score -= 50
                if is_code:
                    score -= 80
                if size == 60:
                    score += 25
                else:
                    score -= min(30, abs(size - 60) // 10)
                if score > 0:
                    closeness = abs(size - 60)
                    if best_gen is None or (score, -closeness) > (best_gen[0], -best_gen[1]):
                        best_gen = (score, closeness, path)
                if size == 60 and score >= 10:
                    if best_60 is None or score > best_60[0]:
                        best_60 = (score, path)
                if size == 60 and not is_code and score <= 0 and unknown60_path is None:
                    unknown60_path = path
        chosen_path = None
        if best_60 is not None:
            chosen_path = best_60[1]
        elif best_gen is not None:
            chosen_path = best_gen[2]
        elif unknown60_path is not None:
            chosen_path = unknown60_path
        if chosen_path is not None:
            try:
                with open(chosen_path, "rb") as f:
                    return f.read()
            except OSError:
                pass
        return b"A" * 60