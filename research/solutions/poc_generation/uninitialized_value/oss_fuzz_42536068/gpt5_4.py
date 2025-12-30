import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        header = '<?xml version="1.0"?>\n<!-- PoC: trigger invalid attribute conversion paths -->\n<root>\n'
        footer = '</root>\n'
        invalid_vals = [
            "", " ", "x", "nan", "NaN", "inf", "-inf", "+inf",
            "++", "--", "+-", "-+", "0x", "0xZZ", "1e9999", "1e-9999",
            ".", "..", "1.2.3", "00x10", "+-1", "-+1", "TrueFalse", "maybe",
            "1_", "_1", "9nine", "eight8", "NaN(123)", "Infinity", "infinity",
            "1#2", "0b2", "0o9", "1,234", "  \t\n", "±1", "1/0", "0/0",
            "notanumber", "1d", "1l", "1f", "0..1", "--5", "++7"
        ]

        # Build multiple elements each with many attributes that are invalid numbers/booleans.
        # This increases the chance that the fuzzer harness will invoke attribute conversion APIs.
        lines = [header]
        for i in range(13):
            attrs = []
            # Include commonly queried attribute names as well as generic ones.
            common_names = [
                "id", "value", "count", "index", "size", "num", "int",
                "uint", "int64", "uint64", "double", "float", "bool"
            ]
            # Mix in the invalid values across these names.
            for j, name in enumerate(common_names):
                v = invalid_vals[(i + j) % len(invalid_vals)]
                attrs.append(f'{name}="{v}"')
            # Add a bunch of generic attributes to expand coverage.
            for j in range(20):
                v = invalid_vals[(i * 7 + j) % len(invalid_vals)]
                attrs.append(f'a{j}="{v}"')
            # Construct element with self-closing tag.
            lines.append(f'  <e{i} ' + ' '.join(attrs) + ' />\n')

        # Add a nested structure with attributes as well.
        lines.append('  <container a="++" b="--" c="0xGG" d="1e9999" e="NaN">\n')
        for k in range(5):
            vals = [invalid_vals[(k * 3 + t) % len(invalid_vals)] for t in range(8)]
            lines.append(
                f'    <child{k} foo="{vals[0]}" bar="{vals[1]}" baz="{vals[2]}" '
                f'alpha="{vals[3]}" beta="{vals[4]}" gamma="{vals[5]}" '
                f'delta="{vals[6]}" epsilon="{vals[7]}" />\n'
            )
        lines.append('  </container>\n')
        lines.append(footer)
        data = ''.join(lines)
        return data.encode('utf-8')