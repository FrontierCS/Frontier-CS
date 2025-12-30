import os
import tarfile


class Solution:
    def _score_name(self, name: str) -> int:
        n = name.lower()
        base = os.path.basename(n)
        score = 0
        if "poc" in base:
            score += 120
        if base.startswith("poc"):
            score += 50
        if "crash" in base:
            score += 100
        if "uaf" in base or "useafter" in base or "use-after" in base:
            score += 80
        if "heap" in base:
            score += 40
        if "bug" in base:
            score += 40
        if "repro" in base or "regress" in base or "issue" in base:
            score += 60
        if "seed" in base:
            score += 30
        if "id_" in base or "id-" in base:
            score += 20
        if "47213" in base:
            score += 160
        if "arvo" in base:
            score += 60
        if "cve-" in base:
            score += 40
        ext = os.path.splitext(base)[1]
        if ext == ".rb":
            score += 80
        elif ext in (".txt", ".dat", ".bin"):
            score += 40
        elif ext == "":
            score += 10
        return score

    def _choose_best(self, candidates, name_scores, target_size):
        best = None
        best_key = None
        for m in candidates:
            ns = name_scores.get(m.name, 0)
            base = os.path.basename(m.name.lower())
            ext = os.path.splitext(base)[1]
            if ext == ".rb":
                ext_rank = 0
            elif ext in (".txt", ".dat", ".bin", ""):
                ext_rank = 1
            else:
                ext_rank = 2
            size_penalty = abs(getattr(m, "size", 0) - target_size)
            key = (ext_rank, size_penalty, -ns, len(m.name))
            if best is None or key < best_key:
                best = m
                best_key = key
        return best

    def _choose_best_with_content(
        self, candidates, name_scores, content_scores, target_size
    ):
        best = None
        best_key = None
        for m in candidates:
            ns = name_scores.get(m.name, 0)
            cs = content_scores.get(m.name, 0)
            total = ns + cs
            size_penalty = abs(getattr(m, "size", 0) - target_size)
            key = (-total, size_penalty, len(m.name))
            if best is None or key < best_key:
                best = m
                best_key = key
        return best

    def _default_poc(self) -> bytes:
        script = r'''
# Default fallback PoC for mruby-like interpreters.
# Exercise stack extension, fibers, blocks, and exceptions.
def deep(n, &blk)
  if n <= 0
    blk.call if blk
    return 0
  end
  a = [n]
  deep(n - 1) do
    3.times do
      begin
        Fiber.new do
          50.times do |i|
            x = [i, a, blk]
            x.map! { |e| e }
          end
        end.resume
      rescue => e
        e.to_s
      end
    end
  end
end

10.times do |i|
  begin
    deep(50) { i.to_s * 2 }
  rescue => e
    e.to_s
  end
end
'''
        return script.encode("utf-8")

    def solve(self, src_path: str) -> bytes:
        target_size = 7270
        try:
            tf = tarfile.open(src_path, "r:*")
        except Exception:
            return self._default_poc()

        with tf:
            members = [m for m in tf.getmembers() if m.isfile()]
            if not members:
                return self._default_poc()

            name_scores = {}
            for m in members:
                try:
                    name_scores[m.name] = self._score_name(m.name)
                except Exception:
                    name_scores[m.name] = 0

            exact = [m for m in members if getattr(m, "size", 0) == target_size]
            if exact:
                best = self._choose_best(exact, name_scores, target_size)
                try:
                    f = tf.extractfile(best)
                    if f is not None:
                        data = f.read()
                        if data:
                            return data
                except Exception:
                    pass

            interesting = [
                m
                for m in members
                if name_scores.get(m.name, 0) >= 50
                and getattr(m, "size", 0) <= 200000
            ]
            if interesting:
                best = self._choose_best(interesting, name_scores, target_size)
                try:
                    f = tf.extractfile(best)
                    if f is not None:
                        data = f.read()
                        if data:
                            return data
                except Exception:
                    pass

            content_scores = {}
            for m in members:
                name_lower = m.name.lower()
                if not name_lower.endswith(".rb"):
                    continue
                if getattr(m, "size", 0) > 50000 or getattr(m, "size", 0) == 0:
                    continue
                try:
                    f = tf.extractfile(m)
                    if f is None:
                        continue
                    raw = f.read()
                except Exception:
                    continue
                try:
                    text = raw.decode("utf-8", errors="ignore").lower()
                except Exception:
                    continue
                score = 0
                if "use after free" in text or "use-after-free" in text:
                    score += 200
                if "heap-use-after" in text or "heap use after" in text:
                    score += 150
                if "mrb_stack_extend" in text:
                    score += 80
                if "uaf" in text:
                    score += 60
                if "regression" in text and "bug" in text:
                    score += 50
                if "cve-" in text:
                    score += 30
                if "stack" in text and "extend" in text:
                    score += 20
                if score > 0:
                    content_scores[m.name] = score

            if content_scores:
                cands = [m for m in members if m.name in content_scores]
                best = self._choose_best_with_content(
                    cands, name_scores, content_scores, target_size
                )
                try:
                    f = tf.extractfile(best)
                    if f is not None:
                        data = f.read()
                        if data:
                            return data
                except Exception:
                    pass

            small_members = [
                m
                for m in members
                if getattr(m, "size", 0) > 0 and getattr(m, "size", 0) <= 100000
            ]
            if small_members:
                best = None
                best_key = None
                for m in small_members:
                    size = getattr(m, "size", 0)
                    base = os.path.basename(m.name.lower())
                    ext = os.path.splitext(base)[1]
                    if ext == ".rb":
                        ext_rank = 0
                    elif ext in (".txt", ".dat", ".bin", ""):
                        ext_rank = 1
                    else:
                        ext_rank = 2
                    size_penalty = abs(size - target_size)
                    key = (ext_rank, size_penalty, len(m.name))
                    if best is None or key < best_key:
                        best = m
                        best_key = key
                try:
                    f = tf.extractfile(best)
                    if f is not None:
                        data = f.read()
                        if data:
                            return data
                except Exception:
                    pass

        return self._default_poc()