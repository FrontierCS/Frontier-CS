import os
import tarfile
import tempfile
import subprocess
import re
import json
import random
import shutil


class Solution:
    def solve(self, src_path: str) -> bytes:
        root_dir = self._prepare_source(src_path)
        self._build_project(root_dir)
        runner = self._make_runner(root_dir)
        json_keys = self._collect_json_related_keys(root_dir)

        # Time and run limits to avoid timeouts
        self.run_timeout = 0.7
        self.max_json_runs = 30
        self.max_generic_runs = 30

        poc = self._find_poc_via_json_samples(root_dir, runner, json_keys)
        if poc is not None:
            return poc

        poc = self._find_poc_via_generic_seeds(runner, json_keys)
        if poc is not None:
            return poc

        # Fallback PoC if nothing else found
        return b"A" * 160

    # --- Source preparation and build ---

    def _prepare_source(self, src_path: str) -> str:
        if os.path.isdir(src_path):
            return src_path

        tmp_root = tempfile.mkdtemp(prefix="src-")
        try:
            try:
                with tarfile.open(src_path, "r:*") as tar:
                    tar.extractall(tmp_root)
            except tarfile.TarError:
                return src_path
            entries = [
                os.path.join(tmp_root, name)
                for name in os.listdir(tmp_root)
                if not name.startswith(".")
            ]
            if len(entries) == 1 and os.path.isdir(entries[0]):
                return entries[0]
            return tmp_root
        except Exception:
            return src_path

    def _build_project(self, root_dir: str) -> None:
        try:
            build_sh = os.path.join(root_dir, "build.sh")
            if os.path.exists(build_sh):
                subprocess.run(
                    ["bash", build_sh],
                    cwd=root_dir,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=300,
                )
            else:
                makefile = os.path.join(root_dir, "Makefile")
                if os.path.exists(makefile):
                    subprocess.run(
                        ["make", "-j4"],
                        cwd=root_dir,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        timeout=300,
                    )
        except Exception:
            pass

    # --- Runner / harness detection ---

    def _make_runner(self, root_dir):
        run_sh = os.path.join(root_dir, "run.sh")
        if os.path.exists(run_sh):
            try:
                script_text = open(run_sh, "r", errors="ignore").read()
            except Exception:
                script_text = ""
            uses_arg = "$1" in script_text or "$@" in script_text

            def runner(data: bytes, timeout: float = 1.0):
                try:
                    if uses_arg:
                        tmp_file = None
                        try:
                            fd, tmp_path = tempfile.mkstemp(dir=root_dir, prefix="poc-")
                            os.close(fd)
                            with open(tmp_path, "wb") as f:
                                f.write(data)
                            tmp_file = tmp_path
                            proc = subprocess.run(
                                ["bash", run_sh, tmp_path],
                                cwd=root_dir,
                                stdin=subprocess.DEVNULL,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                timeout=timeout,
                            )
                        finally:
                            if tmp_file is not None:
                                try:
                                    os.unlink(tmp_file)
                                except Exception:
                                    pass
                    else:
                        proc = subprocess.run(
                            ["bash", run_sh],
                            cwd=root_dir,
                            input=data,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            timeout=timeout,
                        )
                    crashed = self._is_crash(proc)
                    out = (proc.stdout or b"") + (proc.stderr or b"")
                    return proc.returncode, crashed, out
                except subprocess.TimeoutExpired:
                    return -1, False, b"timeout"
                except Exception:
                    return -1, False, b"error"

            return runner

        bin_path = self._find_executable(root_dir)

        def runner(data: bytes, timeout: float = 1.0):
            if bin_path is None:
                return -1, False, b"no-binary"
            try:
                proc = subprocess.run(
                    [bin_path],
                    cwd=os.path.dirname(bin_path),
                    input=data,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=timeout,
                )
                crashed = self._is_crash(proc)
                out = (proc.stdout or b"") + (proc.stderr or b"")
                return proc.returncode, crashed, out
            except subprocess.TimeoutExpired:
                return -1, False, b"timeout"
            except Exception:
                return -1, False, b"error"

        return runner

    def _find_executable(self, root_dir: str):
        skip_dirs = {
            ".git",
            "build",
            "out",
            "dist",
            "cmake-build-debug",
            "cmake-build-release",
            "__pycache__",
        }
        best = None
        for dirpath, dirnames, filenames in os.walk(root_dir):
            base = os.path.basename(dirpath)
            if base in skip_dirs:
                dirnames[:] = []
                continue
            for fname in filenames:
                path = os.path.join(dirpath, fname)
                if not os.path.isfile(path):
                    continue
                if not os.access(path, os.X_OK):
                    continue
                ext = os.path.splitext(fname)[1].lower()
                if ext in (".sh", ".py", ".pl", ".rb", ".jar", ".bat", ".cmd"):
                    continue
                if fname in ("build.sh", "configure"):
                    continue
                best = path
                return best
        return best

    def _is_crash(self, proc: subprocess.CompletedProcess) -> bool:
        out = (proc.stdout or b"") + (proc.stderr or b"")
        low = out.lower()
        if b"addresssanitizer" in low:
            return True
        if b"sanitizer" in low and b"error" in low:
            return True
        if b"stack-buffer-overflow" in low:
            return True
        if b"heap-buffer-overflow" in low:
            return True
        if b"segmentation fault" in low:
            return True
        return False

    # --- JSON-related static analysis ---

    def _collect_json_related_keys(self, root_dir: str):
        keys = set()
        for dirpath, dirnames, filenames in os.walk(root_dir):
            base = os.path.basename(dirpath)
            if base in (".git", "build", "out", "dist", "__pycache__"):
                dirnames[:] = []
                continue
            for fname in filenames:
                if not fname.endswith(
                    (".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh", ".ipp")
                ):
                    continue
                path = os.path.join(dirpath, fname)
                try:
                    text = open(path, "r", errors="ignore").read()
                except Exception:
                    continue
                if not any(
                    tok in text
                    for tok in (
                        "node_id_map",
                        "snapshot",
                        "Snapshot",
                        "SNAPSHOT",
                        "json",
                        "JSON",
                        "Json",
                    )
                ):
                    continue
                try:
                    keys.update(re.findall(r'\[\s*"([A-Za-z_][A-Za-z0-9_]*)"\s*\]', text))
                except re.error:
                    pass
                try:
                    keys.update(
                        re.findall(r'FindMember\("([A-Za-z_][A-Za-z0-9_]*)"\)', text)
                    )
                except re.error:
                    pass
                try:
                    keys.update(re.findall(r'get\("([A-Za-z_][A-Za-z0-9_]*)"', text))
                except re.error:
                    pass
                try:
                    keys.update(
                        re.findall(
                            r'"([A-Za-z_][A-Za-z0-9_]*id)"', text, re.IGNORECASE
                        )
                    )
                except re.error:
                    pass
        return keys

    # --- JSON sample file discovery and mutation ---

    def _find_json_candidate_files(self, root_dir: str, max_files: int = 8):
        candidates = []
        for dirpath, dirnames, filenames in os.walk(root_dir):
            base = os.path.basename(dirpath)
            if base in (".git", "build", "out", "dist", "__pycache__"):
                dirnames[:] = []
                continue
            for fname in filenames:
                low_name = fname.lower()
                if not low_name.endswith(
                    (".json", ".jsn", ".txt", ".snap", ".log", ".dat", ".in")
                ):
                    continue
                path = os.path.join(dirpath, fname)
                try:
                    size = os.path.getsize(path)
                except OSError:
                    continue
                if size == 0 or size > 200000:
                    continue
                try:
                    with open(path, "r", errors="ignore") as f:
                        snippet = f.read(4096)
                except Exception:
                    continue
                score = 0
                low = snippet.lower()
                if "snapshot" in low:
                    score += 4
                if "memory" in low:
                    score += 2
                if "node_id" in low:
                    score += 4
                if "node" in low:
                    score += 2
                if "edges" in low:
                    score += 2
                if "{" in snippet and "}" in snippet:
                    score += 1
                if "[" in snippet and "]" in snippet:
                    score += 1
                if score == 0:
                    continue
                candidates.append((score, path))
        candidates.sort(reverse=True)
        return [p for score, p in candidates[:max_files]]

    def _mutate_json_text(self, json_text: str, json_keys, variant_index: int):
        try:
            obj = json.loads(json_text)
        except Exception:
            return None

        id_field_names = set(["id", "node_id", "nodeId", "nodeID", "nid"])
        for key in json_keys:
            lk = key.lower()
            if lk.endswith("id") or lk in ("id", "node_id", "nodeid"):
                id_field_names.add(key)

        nodes = []

        def collect_nodes(x):
            if isinstance(x, dict):
                keys = set(x.keys())
                id_keys_here = [k for k in keys if k in id_field_names]
                if id_keys_here:
                    joined = " ".join(keys).lower()
                    if not any(
                        tok in joined
                        for tok in (
                            "from",
                            "to",
                            "source",
                            "target",
                            "src",
                            "dst",
                            "edge",
                        )
                    ):
                        nodes.append((x, id_keys_here[0]))
                for v in x.values():
                    collect_nodes(v)
            elif isinstance(x, list):
                for elem in x:
                    collect_nodes(elem)

        collect_nodes(obj)
        if not nodes:
            return None

        old_ids = []
        for d, k in nodes:
            v = d.get(k)
            if isinstance(v, int):
                old_ids.append(v)
            elif isinstance(v, str) and v.isdigit():
                old_ids.append(int(v))
        if not old_ids:
            return None

        max_id = max(old_ids)
        missing_base = max_id + 1000

        if variant_index == 0:
            d, k = nodes[0]
            v = d.get(k)
            if isinstance(v, int) or (isinstance(v, str) and v.isdigit()):
                d[k] = missing_base
        elif variant_index == 1:
            d, k = nodes[-1]
            v = d.get(k)
            if isinstance(v, int) or (isinstance(v, str) and v.isdigit()):
                d[k] = missing_base
        elif variant_index == 2:
            for i, (d, k) in enumerate(nodes):
                v = d.get(k)
                if isinstance(v, int) or (isinstance(v, str) and v.isdigit()):
                    d[k] = missing_base + i
        elif variant_index == 3:
            for i, (d, k) in enumerate(nodes):
                if i % 2 == 0:
                    v = d.get(k)
                    if isinstance(v, int) or (isinstance(v, str) and v.isdigit()):
                        d[k] = missing_base + i
        elif variant_index == 4:
            for d, k in nodes:
                v = d.get(k)
                if isinstance(v, int) or (isinstance(v, str) and v.isdigit()):
                    d[k] = random.randint(missing_base, missing_base + 100000)
        else:
            return None

        try:
            mutated_text = json.dumps(obj, separators=(",", ":"))
        except Exception:
            return None
        return mutated_text.encode("utf-8")

    def _find_poc_via_json_samples(self, root_dir, runner, json_keys):
        candidate_files = self._find_json_candidate_files(root_dir, max_files=8)
        if not candidate_files:
            return None

        runs_done = 0
        max_runs = self.max_json_runs
        max_variants_per_sample = 5

        for path in candidate_files:
            if runs_done >= max_runs:
                break
            try:
                with open(path, "rb") as f:
                    seed_bytes = f.read()
            except Exception:
                continue
            if not seed_bytes or len(seed_bytes) > 500000:
                continue
            try:
                seed_text = seed_bytes.decode("utf-8")
            except UnicodeDecodeError:
                continue
            try:
                json.loads(seed_text)
            except Exception:
                continue
            for variant_index in range(max_variants_per_sample):
                if runs_done >= max_runs:
                    break
                mutated = self._mutate_json_text(seed_text, json_keys, variant_index)
                if mutated is None:
                    continue
                exit_code, crashed, _ = runner(mutated, timeout=self.run_timeout)
                runs_done += 1
                if crashed:
                    return mutated
        return None

    # --- Generic seeds and fuzzing ---

    def _build_generic_json_seeds(self, json_keys):
        def pick_key(preferred, default):
            for cand in preferred:
                for k in json_keys:
                    if k.lower() == cand:
                        return k
            for cand in preferred:
                for k in json_keys:
                    if cand in k.lower():
                        return k
            return default

        nodes_k = pick_key(["nodes", "node_list", "node"], "nodes")
        edges_k = pick_key(["edges", "links", "connections"], "edges")
        id_k = pick_key(["id", "node_id", "nodeid"], "id")
        parent_k = pick_key(["parent", "parent_id", "parentid"], "parent")
        from_k = pick_key(["from", "source", "src"], "from")
        to_k = pick_key(["to", "target", "dst"], "to")
        snap_k = pick_key(
            ["snapshot", "memory_snapshot", "heap_snapshot"], "snapshot"
        )

        seeds = []

        obj1 = {
            nodes_k: [{id_k: 1}, {id_k: 2}],
            edges_k: [{from_k: 999, to_k: 1}],
        }
        try:
            seeds.append(json.dumps(obj1, separators=(",", ":")).encode("utf-8"))
        except Exception:
            pass

        obj2 = {nodes_k: [{id_k: 1}, {id_k: 2, parent_k: 999}]}
        try:
            seeds.append(json.dumps(obj2, separators=(",", ":")).encode("utf-8"))
        except Exception:
            pass

        obj3 = {snap_k: obj1}
        try:
            seeds.append(json.dumps(obj3, separators=(",", ":")).encode("utf-8"))
        except Exception:
            pass

        try:
            seeds.append(
                json.dumps(obj1.get(nodes_k, []), separators=(",", ":")).encode(
                    "utf-8"
                )
            )
        except Exception:
            pass

        return seeds

    def _randomly_mutate_json_numbers(self, obj):
        def recurse(x):
            if isinstance(x, dict):
                for k in list(x.keys()):
                    v = x[k]
                    if isinstance(v, int):
                        if random.random() < 0.7:
                            delta = random.randint(1, 1000)
                            x[k] = v + delta
                    elif isinstance(v, (dict, list)):
                        recurse(v)
            elif isinstance(x, list):
                for i, v in enumerate(x):
                    if isinstance(v, int):
                        if random.random() < 0.7:
                            delta = random.randint(1, 1000)
                            x[i] = v + delta
                    elif isinstance(v, (dict, list)):
                        recurse(v)

        recurse(obj)

    def _find_poc_via_generic_seeds(self, runner, json_keys):
        seeds = []

        seeds.extend(self._build_generic_json_seeds(json_keys))

        seeds.append(b"A" * 256)
        seeds.append(b"B" * 512)
        seeds.append(b"C" * 1024)
        seeds.append(b"\x00" * 256)
        seeds.append(b"%p" * 128)

        random_json_seed = {
            "nodes": [{"id": 1}, {"id": 2, "parent": 3}],
            "edges": [{"from": 4, "to": 1}],
        }
        try:
            seeds.append(
                json.dumps(random_json_seed, separators=(",", ":")).encode("utf-8")
            )
        except Exception:
            pass

        random.shuffle(seeds)

        runs_done = 0
        max_runs = self.max_generic_runs

        for seed in seeds:
            if runs_done >= max_runs:
                break
            exit_code, crashed, _ = runner(seed, timeout=self.run_timeout)
            runs_done += 1
            if crashed:
                return seed

        template_seeds = self._build_generic_json_seeds(json_keys)
        if not template_seeds:
            return None

        while runs_done < max_runs:
            base = random.choice(template_seeds)
            try:
                text = base.decode("utf-8")
            except Exception:
                runs_done += 1
                continue
            try:
                obj = json.loads(text)
            except Exception:
                runs_done += 1
                continue
            self._randomly_mutate_json_numbers(obj)
            try:
                mutated = json.dumps(obj, separators=(",", ":")).encode("utf-8")
            except Exception:
                runs_done += 1
                continue
            exit_code, crashed, _ = runner(mutated, timeout=self.run_timeout)
            runs_done += 1
            if crashed:
                return mutated

        return None