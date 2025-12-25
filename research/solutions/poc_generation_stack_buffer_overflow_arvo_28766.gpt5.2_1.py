import io
import os
import re
import tarfile
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Set


SCALAR_TYPES = {
    "double",
    "float",
    "int32",
    "int64",
    "uint32",
    "uint64",
    "sint32",
    "sint64",
    "fixed32",
    "fixed64",
    "sfixed32",
    "sfixed64",
    "bool",
    "string",
    "bytes",
}


def _varint(n: int) -> bytes:
    if n < 0:
        n &= (1 << 64) - 1
    out = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        if n:
            out.append(b | 0x80)
        else:
            out.append(b)
            break
    return bytes(out)


def _key(field_number: int, wire_type: int) -> bytes:
    return _varint((field_number << 3) | wire_type)


def _enc_varint(field_number: int, value: int) -> bytes:
    return _key(field_number, 0) + _varint(value)


def _enc_len(field_number: int, payload: bytes) -> bytes:
    return _key(field_number, 2) + _varint(len(payload)) + payload


def _strip_proto_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    text = re.sub(r"//[^\n\r]*", "", text)
    return text


def _find_matching_brace(text: str, open_idx: int) -> int:
    depth = 1
    i = open_idx + 1
    n = len(text)
    while i < n:
        c = text[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1


def _remove_nested_message_enum_blocks(body: str) -> str:
    # Remove nested "message X { ... }" and "enum X { ... }" blocks,
    # but keep "oneof" blocks (fields inside are part of parent).
    i = 0
    n = len(body)
    out = []
    while i < n:
        m = re.search(r"\b(message|enum)\b", body[i:])
        if not m:
            out.append(body[i:])
            break
        start = i + m.start()
        out.append(body[i:start])
        brace = body.find("{", start)
        if brace == -1:
            i = start + len(m.group(1))
            continue
        end = _find_matching_brace(body, brace)
        if end == -1:
            i = brace + 1
            continue
        i = end + 1
    return "".join(out)


@dataclass
class FieldDef:
    label: str  # 'repeated', 'optional', 'required', ''
    type: str
    name: str
    number: int


@dataclass
class MessageDef:
    full_name: str
    package: str
    fields: List[FieldDef]


class ProtoIndex:
    def __init__(self) -> None:
        self.messages: Dict[str, MessageDef] = {}
        self.simple_index: Dict[str, List[str]] = {}

    def add(self, msg: MessageDef) -> None:
        self.messages[msg.full_name] = msg
        simple = msg.full_name.split(".")[-1]
        self.simple_index.setdefault(simple, []).append(msg.full_name)

    def resolve_message(self, type_str: str, context_pkg: str = "") -> Optional[str]:
        t = type_str.strip()
        if not t:
            return None
        if t.startswith("map<"):
            return None
        t = t.lstrip(".")
        if t in SCALAR_TYPES:
            return None
        if t in self.messages:
            return t

        # Try context package qualification for unqualified names.
        if "." not in t and context_pkg:
            cand = f"{context_pkg}.{t}"
            if cand in self.messages:
                return cand

        # Try unique simple name match.
        simple = t.split(".")[-1]
        cands = self.simple_index.get(simple, [])
        if len(cands) == 1:
            return cands[0]

        # Try suffix match (qualified name may include package).
        suffix = "." + simple
        suffix_cands = [c for c in cands if c.endswith(suffix)]
        if len(suffix_cands) == 1:
            return suffix_cands[0]

        if len(cands) == 1:
            return cands[0]
        return None


def _parse_proto_messages(proto_text: str, package: str) -> List[MessageDef]:
    text = _strip_proto_comments(proto_text)
    res: List[MessageDef] = []

    def parse_block(block_text: str, parent_full: str, pkg: str) -> None:
        i = 0
        while True:
            m = re.search(r"\bmessage\s+([A-Za-z_]\w*)\s*\{", block_text[i:])
            if not m:
                return
            name = m.group(1)
            start = i + m.start()
            brace = i + m.end() - 1
            end = _find_matching_brace(block_text, brace)
            if end == -1:
                return
            body = block_text[brace + 1 : end]
            full = f"{parent_full}.{name}" if parent_full else (f"{pkg}.{name}" if pkg else name)

            body_for_fields = _remove_nested_message_enum_blocks(body)

            fields: List[FieldDef] = []
            for raw_line in body_for_fields.splitlines():
                line = raw_line.strip()
                if not line:
                    continue
                if line.startswith(("option ", "extensions ", "reserved ")):
                    continue
                if line.startswith("oneof "):
                    continue
                if line in ("{", "}", "};"):
                    continue
                line = line.split("[", 1)[0].strip()
                if not line.endswith(";"):
                    continue
                line = line[:-1].strip()

                fm = re.match(
                    r"^(?:(repeated|required|optional)\s+)?([A-Za-z_][\w.<> ,]*)\s+([A-Za-z_]\w*)\s*=\s*(\d+)\s*$",
                    line,
                )
                if not fm:
                    continue
                label = fm.group(1) or ""
                ftype = fm.group(2).strip()
                fname = fm.group(3)
                fnum = int(fm.group(4))
                fields.append(FieldDef(label=label, type=ftype, name=fname, number=fnum))

            res.append(MessageDef(full_name=full, package=pkg, fields=fields))
            parse_block(body, full, pkg)
            i = end + 1

    parse_block(text, "", package)
    return res


def _scan_tar_text_files(tar_path: str, exts: Tuple[str, ...], limit_bytes: int = 2_000_000) -> List[Tuple[str, str]]:
    out: List[Tuple[str, str]] = []
    with tarfile.open(tar_path, "r:*") as tf:
        for m in tf.getmembers():
            if not m.isfile():
                continue
            name = m.name
            if not any(name.endswith(e) for e in exts):
                continue
            if m.size > limit_bytes:
                continue
            f = tf.extractfile(m)
            if f is None:
                continue
            data = f.read()
            try:
                txt = data.decode("utf-8", errors="ignore")
            except Exception:
                continue
            out.append((name, txt))
    return out


def _extract_hints_from_cpp(tar_path: str) -> Tuple[Set[str], Set[str]]:
    # Returns (capital_identifiers, lower_snake_tokens) near node_id_map usage
    cap: Set[str] = set()
    low: Set[str] = set()
    cpp_files = _scan_tar_text_files(tar_path, (".cc", ".cpp", ".c", ".h", ".hpp", ".hh"), limit_bytes=3_000_000)
    for _, txt in cpp_files:
        if "node_id_map" not in txt:
            continue
        for line in txt.splitlines():
            if "node_id_map" not in line:
                continue
            for token in re.findall(r"\b[A-Z][A-Za-z0-9_]*\b", line):
                if 3 <= len(token) <= 64:
                    cap.add(token)
            for token in re.findall(r"\b[a-z][a-z0-9_]{2,64}\b", line):
                low.add(token)
            for token in re.findall(r"\.([a-z][a-z0-9_]*)\s*\(", line):
                low.add(token)
    return cap, low


def _select_container(idx: ProtoIndex, hint_caps: Set[str], hint_lows: Set[str]) -> Optional[str]:
    best = None
    best_score = -1

    for full, msg in idx.messages.items():
        node_fields = []
        edge_fields = []
        for f in msg.fields:
            if f.label != "repeated":
                continue
            lname = f.name.lower()
            if "node" in lname and "edge" not in lname:
                node_fields.append(f)
            if "edge" in lname:
                edge_fields.append(f)

        if not node_fields or not edge_fields:
            continue

        score = 0
        simple = full.split(".")[-1]
        lsimple = simple.lower()
        if any(simple == hc or simple.endswith(hc) for hc in hint_caps):
            score += 30
        if "heap" in lsimple:
            score += 12
        if "graph" in lsimple:
            score += 10
        if "snapshot" in lsimple:
            score += 6

        for f in node_fields:
            if f.name.lower() == "nodes":
                score += 15
            if f.name in hint_lows or f.name.lower() in hint_lows:
                score += 5
        for f in edge_fields:
            if f.name.lower() == "edges":
                score += 15
            if f.name in hint_lows or f.name.lower() in hint_lows:
                score += 5

        node_t = idx.resolve_message(node_fields[0].type, msg.package)
        edge_t = idx.resolve_message(edge_fields[0].type, msg.package)
        if node_t:
            score += 5
            if "node" in node_t.split(".")[-1].lower():
                score += 3
        if edge_t:
            score += 5
            if "edge" in edge_t.split(".")[-1].lower():
                score += 3

        if score > best_score:
            best_score = score
            best = full

    return best


def _pick_node_edge_fields(idx: ProtoIndex, container_full: str) -> Optional[Tuple[FieldDef, FieldDef, str, str]]:
    container = idx.messages.get(container_full)
    if not container:
        return None

    node_candidates: List[FieldDef] = []
    edge_candidates: List[FieldDef] = []

    for f in container.fields:
        if f.label != "repeated":
            continue
        t = idx.resolve_message(f.type, container.package)
        if not t:
            continue
        lname = f.name.lower()
        if "edge" in lname:
            edge_candidates.append(f)
        elif "node" in lname:
            node_candidates.append(f)

    def best_by_name(cands: List[FieldDef], exact: str) -> Optional[FieldDef]:
        for f in cands:
            if f.name.lower() == exact:
                return f
        return cands[0] if cands else None

    node_field = best_by_name(node_candidates, "nodes")
    edge_field = best_by_name(edge_candidates, "edges")
    if not node_field or not edge_field:
        return None

    node_type = idx.resolve_message(node_field.type, container.package)
    edge_type = idx.resolve_message(edge_field.type, container.package)
    if not node_type or not edge_type:
        return None
    return node_field, edge_field, node_type, edge_type


def _find_id_field(idx: ProtoIndex, node_full: str) -> Optional[FieldDef]:
    node = idx.messages.get(node_full)
    if not node:
        return None
    preferred = ["id", "node_id", "object_id", "uid"]
    fields = node.fields
    for pname in preferred:
        for f in fields:
            if f.name == pname and f.type.strip().lstrip(".") in ("uint64", "uint32", "int64", "int32"):
                return f
    for f in fields:
        if f.name.endswith("_id") and f.type.strip().lstrip(".") in ("uint64", "uint32", "int64", "int32"):
            return f
    for f in fields:
        if f.type.strip().lstrip(".") in ("uint64", "uint32", "int64", "int32"):
            return f
    return None


def _find_edge_from_to_fields(idx: ProtoIndex, edge_full: str) -> Optional[Tuple[FieldDef, FieldDef]]:
    edge = idx.messages.get(edge_full)
    if not edge:
        return None
    fields = edge.fields

    def find_by_names(names: List[str]) -> Optional[FieldDef]:
        for n in names:
            for f in fields:
                if f.name == n and f.type.strip().lstrip(".") in ("uint64", "uint32", "int64", "int32"):
                    return f
        return None

    from_field = find_by_names(["from_node_id", "source_node_id", "src_node_id", "from_id", "source_id"])
    to_field = find_by_names(["to_node_id", "target_node_id", "dst_node_id", "to_id", "target_id"])

    if from_field and to_field:
        return from_field, to_field

    # Fallback: fuzzy match
    def best_fuzzy(is_from: bool) -> Optional[FieldDef]:
        best = None
        best_score = -1
        for f in fields:
            if f.type.strip().lstrip(".") not in ("uint64", "uint32", "int64", "int32"):
                continue
            lname = f.name.lower()
            score = 0
            if "node" in lname:
                score += 3
            if "id" in lname:
                score += 3
            if is_from and ("from" in lname or "src" in lname or "source" in lname):
                score += 5
            if (not is_from) and ("to" in lname or "dst" in lname or "target" in lname):
                score += 5
            if score > best_score:
                best_score = score
                best = f
        return best

    from_f = best_fuzzy(True)
    to_f = best_fuzzy(False)
    if from_f and to_f and from_f.number != to_f.number:
        return from_f, to_f
    return None


def _select_tracepacket(idx: ProtoIndex, container_full: str) -> Optional[str]:
    # Prefer message ending with TracePacket, then those with a path to container.
    candidates = idx.simple_index.get("TracePacket", [])
    if not candidates:
        candidates = [k for k in idx.messages.keys() if k.split(".")[-1].endswith("TracePacket")]

    def has_path(start: str) -> bool:
        return _find_path(idx, start, container_full) is not None

    for c in candidates:
        if has_path(c):
            return c

    if candidates:
        return candidates[0]

    # Fallback: find any message with a direct field to container.
    for full, msg in idx.messages.items():
        for f in msg.fields:
            t = idx.resolve_message(f.type, msg.package)
            if t == container_full:
                return full
    return None


def _find_trace_wrapper(idx: ProtoIndex, packet_full: str) -> Optional[Tuple[str, FieldDef]]:
    # Find message named Trace (or ending Trace) that has repeated field of TracePacket type.
    trace_candidates = idx.simple_index.get("Trace", [])
    if not trace_candidates:
        trace_candidates = [k for k in idx.messages.keys() if k.split(".")[-1] == "Trace" or k.split(".")[-1].endswith(".Trace")]

    best = None
    best_field = None
    best_score = -1
    for full in trace_candidates:
        msg = idx.messages[full]
        for f in msg.fields:
            if f.label != "repeated":
                continue
            t = idx.resolve_message(f.type, msg.package)
            if t != packet_full:
                continue
            score = 0
            if full.split(".")[-1] == "Trace":
                score += 20
            if f.name.lower() == "packet":
                score += 20
            if f.number == 1:
                score += 10
            if score > best_score:
                best_score = score
                best = full
                best_field = f
    if best and best_field:
        return best, best_field
    return None


def _find_path(idx: ProtoIndex, start_full: str, target_full: str, max_depth: int = 6) -> Optional[List[Tuple[str, FieldDef, str]]]:
    if start_full == target_full:
        return []

    q: List[Tuple[str, List[Tuple[str, FieldDef, str]]]] = [(start_full, [])]
    visited: Set[str] = {start_full}
    while q:
        cur, path = q.pop(0)
        if len(path) >= max_depth:
            continue
        msg = idx.messages.get(cur)
        if not msg:
            continue
        for f in msg.fields:
            t = idx.resolve_message(f.type, msg.package)
            if not t:
                continue
            new_path = path + [(cur, f, t)]
            if t == target_full:
                return new_path
            if t not in visited:
                visited.add(t)
                q.append((t, new_path))
    return None


def _build_node_message(idx: ProtoIndex, node_full: str) -> bytes:
    node = idx.messages.get(node_full)
    if not node:
        return b""
    id_field = _find_id_field(idx, node_full)
    if not id_field:
        return b""
    b = bytearray()
    b += _enc_varint(id_field.number, 1)

    # Add a couple of common harmless fields (set to 1) if present, to reduce chance of being ignored.
    for fname in ("self_size", "size", "type_id", "name_id", "class_name_id", "root_type", "flags"):
        for f in node.fields:
            if f.name == fname and f.type.strip().lstrip(".") in ("uint64", "uint32", "int64", "int32", "bool"):
                val = 1
                b += _enc_varint(f.number, val)
                break
    return bytes(b)


def _build_edge_message(idx: ProtoIndex, edge_full: str) -> bytes:
    edge = idx.messages.get(edge_full)
    if not edge:
        return b""
    ft = _find_edge_from_to_fields(idx, edge_full)
    if not ft:
        return b""
    from_f, to_f = ft
    b = bytearray()
    b += _enc_varint(from_f.number, 1)
    b += _enc_varint(to_f.number, 2)

    # Optional: edge type/name id if present
    for fname in ("type", "edge_type", "name_id", "label_id", "priority"):
        for f in edge.fields:
            if f.name == fname and f.type.strip().lstrip(".") in ("uint64", "uint32", "int64", "int32", "bool"):
                b += _enc_varint(f.number, 0 if f.name in ("type", "edge_type") else 1)
                break
    return bytes(b)


def _build_container_message(idx: ProtoIndex, container_full: str, node_field: FieldDef, edge_field: FieldDef, node_full: str, edge_full: str) -> bytes:
    container = idx.messages.get(container_full)
    if not container:
        return b""
    node_msg = _build_node_message(idx, node_full)
    edge_msg = _build_edge_message(idx, edge_full)
    if not node_msg or not edge_msg:
        return b""

    b = bytearray()

    # Common metadata fields
    for fname in ("pid", "process_id", "timestamp", "ts", "uproducer_id", "upid"):
        for f in container.fields:
            if f.name == fname and f.type.strip().lstrip(".") in ("uint64", "uint32", "int64", "int32"):
                b += _enc_varint(f.number, 1)
                break

    # Ensure nodes first, then edges (helps if parser builds map while reading)
    b += _enc_len(node_field.number, node_msg)
    b += _enc_len(edge_field.number, edge_msg)
    return bytes(b)


def _build_packet_with_path(idx: ProtoIndex, tracepacket_full: str, container_full: str, container_payload: bytes) -> bytes:
    path = _find_path(idx, tracepacket_full, container_full)
    if path is None:
        # Try direct container field in TracePacket
        msg = idx.messages.get(tracepacket_full)
        if msg:
            for f in msg.fields:
                t = idx.resolve_message(f.type, msg.package)
                if t == container_full:
                    path = [(tracepacket_full, f, container_full)]
                    break
    if path is None:
        return b""

    inner = container_payload
    # wrap from container up to TracePacket
    for _, f, _ in reversed(path):
        inner = _enc_len(f.number, inner)

    # Add timestamp if available (prepend)
    tp = idx.messages.get(tracepacket_full)
    if tp:
        for f in tp.fields:
            if f.name == "timestamp" and f.type.strip().lstrip(".") in ("uint64", "uint32", "int64", "int32"):
                inner = _enc_varint(f.number, 1) + inner
                break
    return inner


class Solution:
    def solve(self, src_path: str) -> bytes:
        proto_files = _scan_tar_text_files(src_path, (".proto",), limit_bytes=3_000_000)
        hint_caps, hint_lows = _extract_hints_from_cpp(src_path)

        idx = ProtoIndex()
        if proto_files:
            for _, txt in proto_files:
                pkg = ""
                pm = re.search(r"\bpackage\s+([A-Za-z0-9_.]+)\s*;", txt)
                if pm:
                    pkg = pm.group(1).strip()
                for msg in _parse_proto_messages(txt, pkg):
                    idx.add(msg)

        container_full = _select_container(idx, hint_caps, hint_lows) if idx.messages else None
        if not container_full:
            # Minimal fallback: output something unlikely to crash fixed version
            return b"\n\x00"

        picked = _pick_node_edge_fields(idx, container_full)
        if not picked:
            return b"\n\x00"
        node_field, edge_field, node_full, edge_full = picked

        container_payload = _build_container_message(idx, container_full, node_field, edge_field, node_full, edge_full)
        if not container_payload:
            return b"\n\x00"

        tracepacket_full = _select_tracepacket(idx, container_full)
        if not tracepacket_full:
            return b"\n\x00"

        packet_payload = _build_packet_with_path(idx, tracepacket_full, container_full, container_payload)
        if not packet_payload:
            return b"\n\x00"

        wrapper = _find_trace_wrapper(idx, tracepacket_full)
        if wrapper:
            _, packet_field = wrapper
            # Encode as Trace message containing one repeated packet.
            return _enc_len(packet_field.number, packet_payload)

        # If no wrapper, assume raw packet is acceptable.
        return packet_payload