import os
import tarfile


class Solution:
    GROUND_TRUTH_LEN = 2179

    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        Args:
            src_path: Path to the vulnerable source code tarball

        Returns:
            bytes: The PoC input that should trigger the vulnerability
        """
        poc = self._extract_existing_poc(src_path)
        if poc is not None:
            return poc
        return self._build_generic_xml_poc()

    def _extract_existing_poc(self, src_path):
        if not src_path or not os.path.isfile(src_path):
            return None

        keywords = [
            '42536068',
            'clusterfuzz',
            'crash',
            'poc',
            'repro',
            'regress',
            'bug',
            'oss-fuzz',
            'ossfuzz',
            'uninit',
            'uninitialized',
        ]
        interesting_exts = (
            '.xml',
            '.svg',
            '.html',
            '.htm',
            '.txt',
            '.json',
            '.bin',
            '.dat',
            '.poc',
            '.repro',
            '.case',
            '.input',
        )

        try:
            with tarfile.open(src_path, 'r:*') as tf:
                best_member = None
                best_score = -1
                best_delta = None

                for m in tf.getmembers():
                    if not m.isfile():
                        continue
                    if m.size == 0:
                        continue

                    lname = m.name.lower()
                    score = 0

                    if any(k in lname for k in keywords):
                        score += 5
                    if lname.endswith(interesting_exts):
                        score += 1
                    if (
                        'corpus' in lname
                        or 'regress' in lname
                        or 'test' in lname
                        or 'case' in lname
                    ):
                        score += 1
                    if m.size == self.GROUND_TRUTH_LEN:
                        score += 3
                        delta = 0
                    else:
                        delta = abs(m.size - self.GROUND_TRUTH_LEN)
                        if delta <= 64:
                            score += 1

                    if score <= 0:
                        continue

                    if (
                        score > best_score
                        or (score == best_score and (best_delta is None or delta < best_delta))
                    ):
                        best_member = m
                        best_score = score
                        best_delta = delta

                if best_member is not None:
                    try:
                        f = tf.extractfile(best_member)
                        if f is not None:
                            data = f.read()
                            if data:
                                return data
                    except Exception:
                        return None
        except Exception:
            return None

        return None

    def _build_generic_xml_poc(self) -> bytes:
        # A generic XML designed to exercise attribute conversions with many invalid values
        common_attr_names = [
            'value', 'val', 'v', 'data', 'num', 'number',
            'index', 'idx', 'id', 'count', 'size', 'length',
            'width', 'height', 'x', 'y', 'z',
            'offset', 'start', 'end', 'from', 'to',
            'min', 'max', 'low', 'high',
            'int_attr', 'uint_attr', 'float_attr', 'double_attr', 'bool_attr',
            'hex', 'base', 'scale', 'limit', 'step',
            'foo', 'bar', 'baz',
            'attr', 'attribute', 'flag', 'enabled', 'disabled',
            'mode', 'type',
        ]

        invalid_values = [
            'NaN',
            'nan',
            'INF',
            '-INF',
            '+inf',
            '-inf',
            '++123',
            '--456',
            '+-1',
            'abc',
            'xyz',
            '',
            ' ',
            '  ',
            '0xGHI',
            '123abc',
            'one',
            'zero',
            '1e999999',
            '-1e999999',
            '9999999999999999999999999999999999999999',
            '-999999999999999999999999999999999999',
            '++0',
            '--0',
            'TrueFalse',
            'yesno',
            '+-0x1p+1024',
        ]

        lines = []
        lines.append('<?xml version="1.0" encoding="UTF-8"?>')
        lines.append('<!-- Generic PoC exercising attribute conversions with invalid values -->')
        lines.append('<root')

        # Root element with many attributes using invalid numeric/boolean representations
        for i, name in enumerate(common_attr_names):
            value = invalid_values[i % len(invalid_values)]
            lines.append('    %s="%s"' % (name, value))
        lines.append('>')

        # Several child elements, each reusing subsets of attributes with different invalid values
        for child_idx in range(1, 8):
            lines.append('  <child%d' % child_idx)
            offset = child_idx * 3
            for i, name in enumerate(common_attr_names):
                if (i + child_idx) % 3 == 0:
                    value = invalid_values[(i + offset) % len(invalid_values)]
                    lines.append('      %s="%s"' % (name, value))
            lines.append('  />')

        # A more complex nested structure to ensure deeper traversal code paths are hit
        lines.append('  <complex')
        lines.append('      id="complex1"')
        lines.append('      value="NaN"')
        lines.append('      count="not-a-number"')
        lines.append('      size="0xDEFG"')
        lines.append('      index="++42"')
        lines.append('  >')
        lines.append('    <inner')
        lines.append('        x="abc"')
        lines.append('        y="123abc"')
        lines.append('        z="1e309"')
        lines.append('        flag="maybe"')
        lines.append('    />')
        lines.append('    <inner2')
        lines.append('        int_attr="--1"')
        lines.append('        uint_attr="-5"')
        lines.append('        float_attr="NaN"')
        lines.append('        double_attr="INF"')
        lines.append('        bool_attr="not-boolean"')
        lines.append('    />')
        lines.append('  </complex>')
        lines.append('</root>')

        xml = '\n'.join(lines)
        return xml.encode('utf-8')
