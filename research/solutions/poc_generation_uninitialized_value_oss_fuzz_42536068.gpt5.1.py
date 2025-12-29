import os
import tarfile
import tempfile
import shutil
import re


class Solution:
    def solve(self, src_path: str) -> bytes:
        extract_root = tempfile.mkdtemp(prefix="poc_gen_")
        try:
            try:
                with tarfile.open(src_path, "r:*") as tar:
                    def is_within_directory(directory: str, target: str) -> bool:
                        abs_directory = os.path.abspath(directory)
                        abs_target = os.path.abspath(target)
                        return os.path.commonpath([abs_directory, abs_target]) == abs_directory

                    safe_members = []
                    for m in tar.getmembers():
                        member_path = os.path.join(extract_root, m.name)
                        if is_within_directory(extract_root, member_path):
                            safe_members.append(m)
                    tar.extractall(extract_root, members=safe_members)
            except (tarfile.TarError, FileNotFoundError, IsADirectoryError):
                # If extraction fails for any reason, just ignore and fall back later.
                pass

            if self._contains_pugixml(extract_root):
                poc = self._generate_pugixml_poc(extract_root)
            else:
                poc = self._generic_xml_poc()
        finally:
            try:
                shutil.rmtree(extract_root)
            except Exception:
                pass

        return poc

    def _contains_pugixml(self, root: str) -> bool:
        for dirpath, dirnames, filenames in os.walk(root):
            for fname in filenames:
                low = fname.lower()
                if low in ("pugixml.hpp", "pugixml.cpp", "pugiconfig.hpp"):
                    return True
        return False

    def _analyze_pugixml_harness(self, root: str):
        attr_paths = []
        doc_attrs = []
        generic_attribute_uses = False

        attr_pattern = re.compile(r'\.attribute\s*\(\s*"([^"]+)"')
        as_pattern = re.compile(r'\.as_([a-zA-Z0-9_]+)\s*\(')
        child_pattern = re.compile(r'child\s*\(\s*"([^"]+)"')

        for dirpath, dirnames, filenames in os.walk(root):
            for fname in filenames:
                if not fname.endswith((".cpp", ".cc", ".cxx", ".hpp", ".h")):
                    continue
                path = os.path.join(dirpath, fname)
                try:
                    with open(path, "r", encoding="utf-8", errors="ignore") as f:
                        text = f.read()
                except OSError:
                    continue

                if "LLVMFuzzerTestOneInput" not in text:
                    continue

                for line in text.splitlines():
                    if ".attribute" not in line or ".as_" not in line:
                        continue
                    if ".as_string" in line:
                        continue

                    am = attr_pattern.search(line)
                    sm = as_pattern.search(line)
                    if not am or not sm:
                        continue

                    attr_name = am.group(1)
                    conv_name = sm.group(1)
                    prefix = line[: am.start()]

                    if "document_element" in prefix:
                        doc_attrs.append((attr_name, conv_name))
                    else:
                        child_names = child_pattern.findall(prefix)
                        if child_names:
                            attr_paths.append((child_names, attr_name, conv_name))
                        else:
                            generic_attribute_uses = True

        return {
            "paths": attr_paths,
            "doc_attrs": doc_attrs,
            "generic": generic_attribute_uses,
        }

    def _generate_pugixml_poc(self, root: str) -> bytes:
        info = self._analyze_pugixml_harness(root)
        invalid_value = "invalid123abcXYZ"
        xml_lines = ['<?xml version="1.0" encoding="UTF-8"?>']

        if info["doc_attrs"]:
            attrs = []
            for attr_name, conv in info["doc_attrs"]:
                attrs.append(f'{attr_name}="{invalid_value}"')
            if not attrs:
                attrs.append(f'badAttr="{invalid_value}"')
            attr_str = " ".join(attrs)
            xml_lines.append(f"<root {attr_str}></root>")

        elif info["paths"]:
            path_nodes, attr_name, conv = info["paths"][0]

            if not path_nodes:
                root_name = "root"
                xml_lines.append(
                    f'<{root_name} {attr_name}="{invalid_value}"></{root_name}>'
                )
            else:
                root_name = path_nodes[0]
                if len(path_nodes) == 1:
                    xml_lines.append(
                        f'<{root_name} {attr_name}="{invalid_value}"></{root_name}>'
                    )
                else:
                    xml = f"<{root_name}>"
                    for i, name in enumerate(path_nodes[1:], start=1):
                        if i == len(path_nodes) - 1:
                            xml += f'<{name} {attr_name}="{invalid_value}" />'
                        else:
                            xml += f"<{name}>"
                    for name in reversed(path_nodes[1:-1]):
                        xml += f"</{name}>"
                    xml += f"</{root_name}>"
                    xml_lines.append(xml)

        else:
            invalid_values = [
                "not_a_number",
                "+-1.2.3e++--",
                "NaNXYZ",
                "",
                "   ",
                "trueish",
                "false-ish",
            ]
            attr_names = [
                "a",
                "b",
                "c",
                "intAttr",
                "uintAttr",
                "doubleAttr",
                "floatAttr",
                "boolAttr",
            ]
            attrs = []
            for i, name in enumerate(attr_names):
                val = invalid_values[i % len(invalid_values)]
                if val == "":
                    val = " "
                attrs.append(f'{name}="{val}"')
            attr_str = " ".join(attrs)
            xml_lines.append(f"<root {attr_str}>")

            child_names = ["child1", "child2", "item", "node", "element"]
            for idx, cname in enumerate(child_names):
                val = invalid_values[(idx + 3) % len(invalid_values)]
                if val == "":
                    val = "X"
                xml_lines.append(
                    f'  <{cname} badInt="{val}" badDouble="{val}" badBool="{val}"></{cname}>'
                )

            xml_lines.append("</root>")

        xml_text = "\n".join(xml_lines)
        return xml_text.encode("utf-8")

    def _generic_xml_poc(self) -> bytes:
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<root intAttr="not_a_number" doubleAttr="1.2.3" boolAttr="maybe">
  <child name="node1" value="++--invalid">
    <subchild flag="trueish" count="NaNXYZ"></subchild>
  </child>
</root>
"""
        return xml.encode("utf-8")