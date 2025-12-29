import io
import os
import re
import tarfile
import struct
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Set


@dataclass(frozen=True)
class FieldDef:
    name: str
    num: int
    label: str  # "", "repeated", "optional", "required", "oneof"
    type_str: str


@dataclass
class MsgDef:
    full_name: str
    fields: List[FieldDef]


class ProtoIndex:
    _SCALAR_TYPES: Set[str] = {
        "double", "float",
        "int32", "int64", "uint32", "uint64",
        "sint32", "sint64",
        "fixed32", "fixed64",
        "sfixed32", "sfixed64",
        "bool", "string", "bytes",
    }

    def __init__(self):
        self.messages: Dict[str, MsgDef] = {}
        self.short_to_fulls: Dict[str, List[str]] = {}

    @staticmethod
    def _strip_comments(text: str) -> str:
        text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
        text = re.sub(r"//[^\n]*", "", text)
        return text

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        # Keep '.', identifiers, numbers, and punctuation useful for .proto parsing.
        # Note: this is not a full proto parser; it's sufficient for message/field extraction.
        token_re = re.compile(
            r"""
            [A-Za-z_][A-Za-z0-9_]* |
            [0-9]+ |
            \. |
            \{ | \} | \< | \> | \= | \; | \[ | \] | \( | \) | , |
            \"(?:\\.|[^"\\])*\" |
            \'(?:\\.|[^'\\])*\' 
            """,
            re.X,
        )
        return token_re.findall(text)

    def _register_message(self, full_name: str):
        if full_name not in self.messages:
            self.messages[full_name] = MsgDef(full_name=full_name, fields=[])
            short = full_name.split(".")[-1]
            self.short_to_fulls.setdefault(short, []).append(full_name)

    def parse_proto_text(self, text: str):
        text = self._strip_comments(text)
        tokens = self._tokenize(text)
        n = len(tokens)
        i = 0
        package = ""
        scope_stack: List[Tuple[str, str]] = []  # (kind, name) where kind is 'message' or 'oneof'
        current_message_full: Optional[str] = None

        def current_message_scope_names() -> List[str]:
            return [name for kind, name in scope_stack if kind == "message"]

        def set_current_message():
            nonlocal current_message_full
            msg_names = current_message_scope_names()
            if not msg_names:
                current_message_full = None
                return
            full = ".".join([p for p in [package] if p] + msg_names)
            current_message_full = full
            self._register_message(full)

        def skip_to_semicolon(pos: int) -> int:
            while pos < n and tokens[pos] != ";":
                pos += 1
            return min(pos + 1, n)

        def skip_block(pos: int) -> int:
            # assumes current token is '{' or points to token just after it
            depth = 0
            while pos < n:
                if tokens[pos] == "{":
                    depth += 1
                elif tokens[pos] == "}":
                    depth -= 1
                    if depth <= 0:
                        return pos + 1
                pos += 1
            return n

        def parse_qualified_name(pos: int) -> Tuple[str, int]:
            # Parses something like foo.bar.Baz from tokens (identifiers separated by '.')
            parts = []
            if pos < n and tokens[pos] == ".":
                parts.append(".")
                pos += 1
            if pos >= n or not re.match(r"^[A-Za-z_]", tokens[pos]):
                return "", pos
            parts.append(tokens[pos])
            pos += 1
            while pos + 1 < n and tokens[pos] == "." and re.match(r"^[A-Za-z_]", tokens[pos + 1]):
                parts.append(".")
                parts.append(tokens[pos + 1])
                pos += 2
            return "".join(parts), pos

        def parse_type(pos: int) -> Tuple[str, int]:
            # Handles map<...> and qualified names.
            if pos < n and tokens[pos] == "map":
                # consume map< K , V >
                start = pos
                while pos < n and tokens[pos] != ">":
                    pos += 1
                pos = min(pos + 1, n)
                return "".join(tokens[start:pos]), pos
            tname, pos2 = parse_qualified_name(pos)
            if tname:
                return tname, pos2
            return "", pos

        while i < n:
            tok = tokens[i]

            if tok == "package":
                name, j = parse_qualified_name(i + 1)
                package = name.lstrip(".")
                i = skip_to_semicolon(j)
                continue

            if tok == "message":
                if i + 1 < n and re.match(r"^[A-Za-z_]", tokens[i + 1]):
                    msg_name = tokens[i + 1]
                    scope_stack.append(("message", msg_name))
                    # Advance to '{'
                    i += 2
                    while i < n and tokens[i] != "{":
                        i += 1
                    if i < n and tokens[i] == "{":
                        i += 1
                    set_current_message()
                    continue

            if tok == "oneof":
                if i + 1 < n and re.match(r"^[A-Za-z_]", tokens[i + 1]):
                    oneof_name = tokens[i + 1]
                    scope_stack.append(("oneof", oneof_name))
                    i += 2
                    while i < n and tokens[i] != "{":
                        i += 1
                    if i < n and tokens[i] == "{":
                        i += 1
                    set_current_message()
                    continue

            if tok == "enum":
                # skip enum block
                i += 1
                while i < n and tokens[i] != "{":
                    i += 1
                if i < n and tokens[i] == "{":
                    i = skip_block(i)
                continue

            if tok in {"option", "import", "syntax", "reserved", "extensions", "extend"}:
                # 'extend' has a block; others usually end with ';'
                if tok == "extend":
                    i += 1
                    while i < n and tokens[i] != "{":
                        i += 1
                    if i < n and tokens[i] == "{":
                        i = skip_block(i)
                else:
                    i = skip_to_semicolon(i + 1)
                continue

            if tok == "}":
                # pop one scope (message or oneof)
                if scope_stack:
                    scope_stack.pop()
                i += 1
                set_current_message()
                continue

            # Attempt to parse a field in the current message scope.
            if current_message_full is not None:
                label = ""
                pos = i
                if tokens[pos] in {"repeated", "optional", "required"}:
                    label = tokens[pos]
                    pos += 1

                # parse type
                type_str, pos = parse_type(pos)
                if not type_str:
                    i += 1
                    continue

                # field name
                if pos < n and re.match(r"^[A-Za-z_]", tokens[pos]):
                    fname = tokens[pos]
                    pos += 1
                else:
                    i += 1
                    continue

                # '=' number
                if pos < n and tokens[pos] == "=" and pos + 1 < n and tokens[pos + 1].isdigit():
                    fnum = int(tokens[pos + 1])
                    pos += 2
                else:
                    i += 1
                    continue

                # skip field options until ';'
                pos = skip_to_semicolon(pos)

                # if inside oneof, mark label as oneof (unless repeated etc)
                in_oneof = any(kind == "oneof" for kind, _ in scope_stack)
                if in_oneof and label == "":
                    label = "oneof"

                self.messages[current_message_full].fields.append(
                    FieldDef(name=fname, num=fnum, label=label, type_str=type_str)
                )
                i = pos
                continue

            i += 1

    def _short_name(self, full_name: str) -> str:
        return full_name.split(".")[-1]

    def is_scalar_type(self, type_str: str) -> bool:
        if not type_str:
            return True
        if type_str.startswith("map<"):
            return True
        t = type_str.lstrip(".")
        if t in self._SCALAR_TYPES:
            return True
        # Heuristic: treat unknown as scalar unless it matches a message we know.
        if t in self.messages:
            return False
        if self._short_name(t) in self.short_to_fulls:
            return False
        return False if t in self.short_to_fulls else True

    def resolve_message_type_candidates(self, type_str: str, context_msg_full: str) -> List[str]:
        if not type_str:
            return []
        if type_str.startswith("map<"):
            return []
        t = type_str
        if t.startswith("."):
            full = t[1:]
            if full in self.messages:
                return [full]
            # if full includes leading package but differs, try suffix match
            short = full.split(".")[-1]
            return self.short_to_fulls.get(short, [])[:]
        # unqualified name: could be nested in context or same package, or global
        short = t.split(".")[-1]
        candidates = self.short_to_fulls.get(short, [])
        if not candidates:
            return []
        # Prefer same package prefix
        pkg = context_msg_full.rsplit(".", 1)[0] if "." in context_msg_full else ""
        preferred = [c for c in candidates if pkg and c.startswith(pkg + ".")]
        if preferred:
            return preferred
        return candidates[:]

    def find_messages_ending_with(self, suffix: str) -> List[str]:
        return [k for k in self.messages.keys() if k.endswith(suffix)]

    def build_adjacency(self) -> Dict[str, List[Tuple[int, str, str]]]:
        # msg -> list of (field_num, field_name, child_msg_full)
        adj: Dict[str, List[Tuple[int, str, str]]] = {}
        for mname, mdef in self.messages.items():
            edges: List[Tuple[int, str, str]] = []
            for f in mdef.fields:
                cands = self.resolve_message_type_candidates(f.type_str, mname)
                for c in cands:
                    edges.append((f.num, f.name, c))
            adj[mname] = edges
        return adj


def _encode_varint(x: int) -> bytes:
    if x < 0:
        x &= (1 << 64) - 1
    out = bytearray()
    while True:
        b = x & 0x7F
        x >>= 7
        if x:
            out.append(b | 0x80)
        else:
            out.append(b)
            break
    return bytes(out)


def _encode_key(field_num: int, wire_type: int) -> bytes:
    return _encode_varint((field_num << 3) | wire_type)


def _encode_uint(field_num: int, value: int) -> bytes:
    return _encode_key(field_num, 0) + _encode_varint(value)


def _encode_fixed32(field_num: int, value: int) -> bytes:
    return _encode_key(field_num, 5) + struct.pack("<I", value & 0xFFFFFFFF)


def _encode_fixed64(field_num: int, value: int) -> bytes:
    return _encode_key(field_num, 1) + struct.pack("<Q", value & 0xFFFFFFFFFFFFFFFF)


def _encode_bytes(field_num: int, payload: bytes) -> bytes:
    return _encode_key(field_num, 2) + _encode_varint(len(payload)) + payload


def _encode_string(field_num: int, s: str) -> bytes:
    return _encode_bytes(field_num, s.encode("utf-8", errors="ignore"))


def _varint_type(t: str) -> bool:
    t = t.lstrip(".")
    return t in {"int32", "int64", "uint32", "uint64", "sint32", "sint64", "bool"} or t == "enum"


def _fixed32_type(t: str) -> bool:
    t = t.lstrip(".")
    return t in {"fixed32", "sfixed32", "float"}


def _fixed64_type(t: str) -> bool:
    t = t.lstrip(".")
    return t in {"fixed64", "sfixed64", "double"}


def _string_type(t: str) -> bool:
    t = t.lstrip(".")
    return t == "string"


def _bytes_type(t: str) -> bool:
    t = t.lstrip(".")
    return t == "bytes"


def _encode_scalar_field(f: FieldDef, value: int) -> bytes:
    t = f.type_str
    if _varint_type(t):
        return _encode_uint(f.num, value)
    if _fixed32_type(t):
        return _encode_fixed32(f.num, value)
    if _fixed64_type(t):
        return _encode_fixed64(f.num, value)
    if _string_type(t):
        return _encode_string(f.num, str(value))
    if _bytes_type(t):
        return _encode_bytes(f.num, _encode_varint(value))
    return b""


def _read_tar_members(src_path: str, max_file_size: int = 2_500_000) -> Dict[str, bytes]:
    out: Dict[str, bytes] = {}
    with tarfile.open(src_path, "r:*") as tf:
        for m in tf.getmembers():
            if not m.isfile():
                continue
            if m.size <= 0 or m.size > max_file_size:
                continue
            name = m.name
            try:
                f = tf.extractfile(m)
                if not f:
                    continue
                data = f.read()
            except Exception:
                continue
            out[name] = data
    return out


def _decode_text(b: bytes) -> str:
    return b.decode("utf-8", errors="ignore")


def _extract_hints_from_cpp(cpp_texts: Dict[str, str]) -> List[str]:
    hints: List[str] = []
    decoder_pat = re.compile(r"pbzero::([A-Za-z_][A-Za-z0-9_]*)::Decoder")
    decoder_pat2 = re.compile(r"protos::(?:pbzero::)?([A-Za-z_][A-Za-z0-9_]*)::Decoder")
    for path, txt in cpp_texts.items():
        if "node_id_map" not in txt:
            continue
        # Gather decoder types near node_id_map occurrences
        for m in re.finditer(r"node_id_map", txt):
            lo = max(0, m.start() - 1200)
            hi = min(len(txt), m.end() + 1200)
            window = txt[lo:hi]
            for pat in (decoder_pat, decoder_pat2):
                for dm in pat.finditer(window):
                    hints.append(dm.group(1))
        # Also global hints in file
        for dm in decoder_pat.finditer(txt):
            hints.append(dm.group(1))
    # Normalize and score by frequency
    freq: Dict[str, int] = {}
    for h in hints:
        if h in {"Decoder", "ProtoDecoder"}:
            continue
        freq[h] = freq.get(h, 0) + 1
    ordered = sorted(freq.items(), key=lambda kv: (-kv[1], kv[0]))
    return [k for k, _ in ordered]


def _detect_top_level(cpp_texts: Dict[str, str]) -> str:
    # Returns one of: "Trace", "TracePacket", "Unknown"
    for _, txt in cpp_texts.items():
        if "LLVMFuzzerTestOneInput" not in txt:
            continue
        t = txt
        if "TraceProcessor" in t or "trace_processor" in t or ".Parse(" in t and "TracePacket::Decoder" not in t:
            return "Trace"
        if "TracePacket::Decoder" in t or "pbzero::TracePacket::Decoder" in t:
            return "TracePacket"
    # Common harness: trace_processor parses Trace-encoded stream.
    return "Trace"


def _score_graph_like_message(pidx: ProtoIndex, msg_full: str) -> int:
    mdef = pidx.messages.get(msg_full)
    if not mdef:
        return -10**9
    name = msg_full.split(".")[-1]
    score = 0
    if "Graph" in name or "Snapshot" in name or "Dump" in name:
        score += 5
    rep_msg_fields = [f for f in mdef.fields if f.label == "repeated" and not pidx.is_scalar_type(f.type_str)]
    score += min(10, len(rep_msg_fields))
    # Extra points if looks like nodes/edges container
    for f in rep_msg_fields:
        fn = f.name.lower()
        if "node" in fn or "object" in fn:
            score += 10
        if "edge" in fn or "reference" in fn or "link" in fn:
            score += 10
    return score


def _pick_trace_and_packet_messages(pidx: ProtoIndex) -> Tuple[Optional[str], Optional[str], Optional[int]]:
    # Find TracePacket
    tracepacket_candidates = pidx.find_messages_ending_with(".TracePacket") + ([k for k in pidx.messages if k == "TracePacket"])
    tracepacket_candidates = list(dict.fromkeys(tracepacket_candidates))
    tracepacket = tracepacket_candidates[0] if tracepacket_candidates else None

    # Find Trace with a repeated field pointing to TracePacket.
    trace_candidates = pidx.find_messages_ending_with(".Trace") + ([k for k in pidx.messages if k == "Trace"])
    trace_candidates = list(dict.fromkeys(trace_candidates))
    best_trace = None
    best_packet_field_num = None
    best_score = -1
    for tname in trace_candidates:
        tdef = pidx.messages.get(tname)
        if not tdef:
            continue
        for f in tdef.fields:
            if f.label != "repeated":
                continue
            cands = pidx.resolve_message_type_candidates(f.type_str, tname)
            if not cands:
                continue
            if tracepacket and tracepacket in cands:
                s = 10
            else:
                # If we don't know tracepacket, any repeated message field named packet is likely it
                s = 0
            if f.name.lower() == "packet":
                s += 50
            if f.num == 1:
                s += 5
            if s > best_score:
                best_score = s
                best_trace = tname
                best_packet_field_num = f.num
                if tracepacket is None and cands:
                    tracepacket = cands[0]
    return best_trace, tracepacket, best_packet_field_num


def _bfs_path(pidx: ProtoIndex, start: str, target: str) -> Optional[List[Tuple[str, int, str]]]:
    if start == target:
        return []
    adj = pidx.build_adjacency()
    q: List[str] = [start]
    prev: Dict[str, Tuple[str, int, str]] = {}  # child -> (parent, field_num, child)
    seen: Set[str] = {start}

    while q:
        cur = q.pop(0)
        for fnum, _, child in adj.get(cur, []):
            if child in seen:
                continue
            seen.add(child)
            prev[child] = (cur, fnum, child)
            if child == target:
                # reconstruct
                path: List[Tuple[str, int, str]] = []
                node = child
                while node != start:
                    parent, fn, ch = prev[node]
                    path.append((parent, fn, ch))
                    node = parent
                path.reverse()
                return path
            q.append(child)
    return None


def _find_id_field(pidx: ProtoIndex, msg_full: str) -> Optional[FieldDef]:
    mdef = pidx.messages.get(msg_full)
    if not mdef:
        return None
    candidates: List[Tuple[int, FieldDef]] = []
    for f in mdef.fields:
        if f.label == "repeated":
            continue
        fn = f.name.lower()
        if not (_varint_type(f.type_str) or f.type_str.lstrip(".") in {"uint64", "uint32", "int64", "int32", "sint64", "sint32"}):
            continue
        if fn == "id":
            return f
        score = 0
        if fn.endswith("_id"):
            score += 5
        if "node" in fn or "object" in fn:
            score += 3
        if "id" in fn:
            score += 1
        if score > 0:
            candidates.append((score, f))
    if not candidates:
        # fallback: first varint field
        for f in mdef.fields:
            if f.label != "repeated" and _varint_type(f.type_str):
                return f
        return None
    candidates.sort(key=lambda x: (-x[0], x[1].num))
    return candidates[0][1]


def _find_edge_id_fields(pidx: ProtoIndex, edge_msg_full: str) -> Tuple[Optional[FieldDef], Optional[FieldDef]]:
    mdef = pidx.messages.get(edge_msg_full)
    if not mdef:
        return None, None
    id_fields = [f for f in mdef.fields if f.label != "repeated" and _varint_type(f.type_str) and "id" in f.name.lower()]
    if not id_fields:
        # fallback: any varint fields
        id_fields = [f for f in mdef.fields if f.label != "repeated" and _varint_type(f.type_str)]
    if not id_fields:
        return None, None

    def role_score(f: FieldDef, role: str) -> int:
        n = f.name.lower()
        s = 0
        if role == "from":
            if "from" in n or "src" in n or "source" in n or "owner" in n or "parent" in n:
                s += 10
        if role == "to":
            if "to" in n or "dst" in n or "target" in n or "owned" in n or "child" in n:
                s += 10
        if n.endswith("_id"):
            s += 2
        if "node" in n or "object" in n:
            s += 1
        return s

    best_from = None
    best_to = None
    best_from_s = -1
    best_to_s = -1
    for f in id_fields:
        sf = role_score(f, "from")
        st = role_score(f, "to")
        if sf > best_from_s:
            best_from_s = sf
            best_from = f
        if st > best_to_s:
            best_to_s = st
            best_to = f

    # If best_from and best_to are the same and we have >=2 id fields, pick second as to.
    if best_from and best_to and best_from.num == best_to.num:
        if len(id_fields) >= 2:
            id_fields_sorted = sorted(id_fields, key=lambda f: f.num)
            best_from = id_fields_sorted[0]
            best_to = id_fields_sorted[1]
    return best_from, best_to


def _choose_node_edge_fields(pidx: ProtoIndex, target_msg_full: str) -> Tuple[Optional[FieldDef], Optional[str], Optional[FieldDef], Optional[str]]:
    tdef = pidx.messages.get(target_msg_full)
    if not tdef:
        return None, None, None, None

    rep_msg_fields = [f for f in tdef.fields if f.label == "repeated" and not pidx.is_scalar_type(f.type_str)]
    if not rep_msg_fields:
        return None, None, None, None

    # For each repeated message field, resolve its message type(s), and score based on whether it has an id field.
    node_candidates: List[Tuple[int, FieldDef, str]] = []
    edge_candidates: List[Tuple[int, FieldDef, str]] = []

    for f in rep_msg_fields:
        cands = pidx.resolve_message_type_candidates(f.type_str, target_msg_full)
        for c in cands[:3]:
            cdef = pidx.messages.get(c)
            if not cdef:
                continue
            idf = _find_id_field(pidx, c)
            base = 0
            fn = f.name.lower()
            mn = c.split(".")[-1].lower()
            if "node" in fn or "node" in mn or "object" in fn or "object" in mn:
                base += 10
            if "edge" in fn or "edge" in mn or "reference" in fn or "reference" in mn or "link" in fn or "ref" in fn:
                base += 10
            if idf is not None:
                base += 10
            # Edge scoring: needs at least two id-ish fields
            idish = [ff for ff in cdef.fields if ff.label != "repeated" and _varint_type(ff.type_str) and "id" in ff.name.lower()]
            if len(idish) >= 2:
                edge_bonus = 15
            elif len(idish) == 1:
                edge_bonus = 5
            else:
                edge_bonus = 0

            node_score = base
            edge_score = base + edge_bonus

            if "node" in fn or "object" in fn:
                node_candidates.append((node_score, f, c))
            if "edge" in fn or "reference" in fn or "link" in fn or "ref" in fn:
                edge_candidates.append((edge_score, f, c))

            # If names aren't explicit, still consider as possible node/edge based on message structure
            if "node" not in fn and "edge" not in fn and "reference" not in fn and "link" not in fn and "ref" not in fn:
                if idf is not None:
                    node_candidates.append((node_score - 3, f, c))
                if edge_bonus > 0:
                    edge_candidates.append((edge_score - 3, f, c))

    if not node_candidates or not edge_candidates:
        # fallback: pick any two repeated message fields with id and with >=2 idish
        for f in rep_msg_fields:
            cands = pidx.resolve_message_type_candidates(f.type_str, target_msg_full)
            for c in cands[:2]:
                idf = _find_id_field(pidx, c)
                if idf is not None:
                    node_candidates.append((1, f, c))
                cdef = pidx.messages.get(c)
                if cdef:
                    idish = [ff for ff in cdef.fields if ff.label != "repeated" and _varint_type(ff.type_str) and "id" in ff.name.lower()]
                    if len(idish) >= 2:
                        edge_candidates.append((1, f, c))

    if not node_candidates or not edge_candidates:
        return None, None, None, None

    node_candidates.sort(key=lambda x: (-x[0], x[1].num))
    edge_candidates.sort(key=lambda x: (-x[0], x[1].num))
    node_field, node_type = node_candidates[0][1], node_candidates[0][2]
    edge_field, edge_type = edge_candidates[0][1], edge_candidates[0][2]
    return node_field, node_type, edge_field, edge_type


def _build_graph_message_bytes(pidx: ProtoIndex, target_msg_full: str) -> Optional[bytes]:
    node_field, node_type, edge_field, edge_type = _choose_node_edge_fields(pidx, target_msg_full)
    if not node_field or not node_type or not edge_field or not edge_type:
        return None

    node_id_field = _find_id_field(pidx, node_type)
    if not node_id_field:
        return None

    from_f, to_f = _find_edge_id_fields(pidx, edge_type)
    if not from_f and not to_f:
        return None
    if not from_f:
        from_f = to_f
    if not to_f:
        to_f = from_f

    node_bytes = _encode_uint(node_id_field.num, 1)
    edge_bytes = b""
    if from_f:
        edge_bytes += _encode_uint(from_f.num, 1)
    if to_f:
        edge_bytes += _encode_uint(to_f.num, 2)

    # Ensure nodes appear before edges (in serialized order)
    out = bytearray()
    out += _encode_bytes(node_field.num, node_bytes)
    out += _encode_bytes(edge_field.num, edge_bytes)
    return bytes(out)


def _add_min_scalars(pidx: ProtoIndex, msg_full: str, msg_payload: bytes) -> bytes:
    mdef = pidx.messages.get(msg_full)
    if not mdef:
        return msg_payload
    extras = bytearray()
    # Add a few common gating fields if present.
    preferred_names = [
        ("trusted_packet_sequence_id", 1),
        ("packet_sequence_id", 1),
        ("sequence_id", 1),
        ("timestamp", 1),
        ("ts", 1),
        ("pid", 1),
        ("process_id", 1),
        ("tgid", 1),
        ("upid", 1),
        ("utid", 1),
    ]
    found = set()
    for f in mdef.fields:
        fn = f.name.lower()
        if f.label == "repeated":
            continue
        if not _varint_type(f.type_str):
            continue
        for pname, val in preferred_names:
            if pname == fn or (pname in {"ts"} and fn in {"ts", "time_ns", "time", "event_timestamp"}) or (pname in fn):
                if f.num not in found:
                    extras += _encode_scalar_field(f, val)
                    found.add(f.num)
                break
        if len(found) >= 3:
            break
    if extras:
        return bytes(extras) + msg_payload
    return msg_payload


def _generate_trace_packet_for_target(pidx: ProtoIndex, tracepacket_full: str, target_msg_full: str) -> Optional[bytes]:
    target_payload = _build_graph_message_bytes(pidx, target_msg_full)
    if target_payload is None:
        return None

    path = _bfs_path(pidx, tracepacket_full, target_msg_full)
    if path is None:
        if tracepacket_full == target_msg_full:
            pkt_payload = _add_min_scalars(pidx, tracepacket_full, target_payload)
            return pkt_payload
        return None

    # Build from inner to outer: start with target payload
    cur_payload = target_payload
    # Reverse traverse path: last edge points to target
    for parent, field_num, child in reversed(path):
        wrapped = _encode_bytes(field_num, cur_payload)
        wrapped = _add_min_scalars(pidx, parent, wrapped)
        cur_payload = wrapped

    # cur_payload is now TracePacket payload (not length-delimited; caller will wrap if needed)
    cur_payload = _add_min_scalars(pidx, tracepacket_full, cur_payload)
    return cur_payload


class Solution:
    def solve(self, src_path: str) -> bytes:
        files = _read_tar_members(src_path)
        proto_texts: Dict[str, str] = {}
        cpp_texts: Dict[str, str] = {}

        for name, data in files.items():
            ln = name.lower()
            if ln.endswith(".proto"):
                proto_texts[name] = _decode_text(data)
            elif ln.endswith((".cc", ".cpp", ".c", ".cxx", ".h", ".hpp", ".hh", ".hxx")):
                cpp_texts[name] = _decode_text(data)

        pidx = ProtoIndex()
        for _, txt in proto_texts.items():
            try:
                pidx.parse_proto_text(txt)
            except Exception:
                continue

        top_level = _detect_top_level(cpp_texts)

        trace_full, tracepacket_full, trace_packet_field_num = _pick_trace_and_packet_messages(pidx)

        # If we can't find protos, return a minimal non-empty input.
        if not pidx.messages:
            return b"\x00"

        # Determine likely targets
        hints = _extract_hints_from_cpp(cpp_texts)
        candidate_targets: List[str] = []

        # Add hint-based candidates
        for h in hints[:12]:
            for full in pidx.short_to_fulls.get(h, []):
                candidate_targets.append(full)

        # Add heuristic candidates
        all_msgs = list(pidx.messages.keys())
        scored = sorted((( _score_graph_like_message(pidx, m), m) for m in all_msgs), key=lambda x: -x[0])
        for s, m in scored[:60]:
            if s <= 0:
                break
            candidate_targets.append(m)

        # Deduplicate, keep order
        seen = set()
        uniq_targets: List[str] = []
        for m in candidate_targets:
            if m in seen:
                continue
            seen.add(m)
            uniq_targets.append(m)

        # Decide start message
        if top_level == "TracePacket":
            start_msg = tracepacket_full
        else:
            start_msg = tracepacket_full

        if start_msg is None:
            # No TracePacket message found; try to craft payload directly from best graph-like message.
            for _, m in scored[:50]:
                b = _build_graph_message_bytes(pidx, m)
                if b:
                    return b
            return b"\x00"

        # Build up to a few packets for robustness
        packets: List[bytes] = []
        for tgt in uniq_targets:
            pkt = _generate_trace_packet_for_target(pidx, start_msg, tgt)
            if pkt:
                packets.append(pkt)
            if len(packets) >= 3:
                break

        if not packets:
            # Fallback: try direct graph message bytes for best candidates
            for _, m in scored[:80]:
                b = _build_graph_message_bytes(pidx, m)
                if b:
                    return b
            return b"\x00"

        if top_level == "TracePacket" or trace_full is None or trace_packet_field_num is None:
            # Return the first packet directly.
            return packets[0]

        # Wrap in Trace as repeated packet field(s). Note: this is also the on-disk perfetto trace encoding.
        out = bytearray()
        for pkt in packets:
            out += _encode_bytes(trace_packet_field_num, pkt)

        # Keep output reasonably small
        if len(out) > 4096:
            out = out[:4096]
        return bytes(out)