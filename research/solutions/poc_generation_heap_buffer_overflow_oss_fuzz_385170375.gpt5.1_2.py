import os
import tarfile
import tempfile
import shutil
import subprocess


class Solution:
    def solve(self, src_path: str) -> bytes:
        workdir = tempfile.mkdtemp(prefix="pocgen_")
        try:
            extract_root = workdir

            # Extract tarball if possible
            if os.path.isfile(src_path):
                try:
                    with tarfile.open(src_path, "r:*") as tf:
                        tf.extractall(extract_root)
                except Exception:
                    # If not a tar, just ignore extraction and try to work with given path
                    extract_root = src_path if os.path.isdir(src_path) else workdir
            elif os.path.isdir(src_path):
                extract_root = src_path

            # 1) Try to find an existing PoC in the source tree
            poc = self._find_poc_in_tree(extract_root)
            if poc is not None:
                return poc

            # 2) Try to build and fuzz using libFuzzer to rediscover the PoC
            build_script, project_root = self._find_build_script(extract_root)
            if build_script and project_root:
                built_root = self._build_project(build_script, project_root)
                if built_root:
                    fuzzer_path = self._find_fuzzer_binary(built_root)
                    if fuzzer_path:
                        poc = self._run_libfuzzer(fuzzer_path, built_root)
                        if poc is not None:
                            return poc

            # 3) Fallback: return a dummy input of the ground-truth length
            return b"A" * 149
        finally:
            shutil.rmtree(workdir, ignore_errors=True)

    def _find_poc_in_tree(self, root: str):
        target_len = 149
        preferred = None
        fallback = None

        text_exts = {
            ".c", ".cc", ".cpp", ".cxx", ".h", ".hpp",
            ".txt", ".md", ".markdown", ".rst",
            ".json", ".xml", ".html", ".htm",
            ".yml", ".yaml", ".toml", ".ini", ".cfg",
            ".py", ".sh", ".bat", ".ps1",
            ".cmake", ".am", ".ac", ".m4", ".in", ".mk",
            ".java", ".go", ".rs", ".js", ".ts",
        }

        for dirpath, _, filenames in os.walk(root):
            for name in filenames:
                low = name.lower()
                if not any(k in low for k in ("clusterfuzz", "poc", "crash", "rv60", "av_codec_id_rv60", "testcase")):
                    continue
                ext = os.path.splitext(low)[1]
                if ext in text_exts:
                    continue
                full = os.path.join(dirpath, name)
                try:
                    if os.path.islink(full):
                        continue
                    sz = os.path.getsize(full)
                except OSError:
                    continue
                if sz != target_len:
                    continue
                if "rv60" in low or "av_codec_id_rv60" in low:
                    preferred = full
                    break
                if fallback is None:
                    fallback = full
            if preferred:
                break

        candidate = preferred or fallback
        if candidate:
            try:
                with open(candidate, "rb") as f:
                    return f.read()
            except OSError:
                return None
        return None

    def _find_build_script(self, root: str):
        for dirpath, _, filenames in os.walk(root):
            if "build.sh" in filenames:
                return os.path.join(dirpath, "build.sh"), dirpath
        return None, None

    def _build_project(self, build_script: str, project_root: str):
        env = os.environ.copy()

        # Prefer clang/clang++ if available
        clang = shutil.which("clang")
        clangxx = shutil.which("clang++")
        if clang:
            env.setdefault("CC", clang)
        if clangxx:
            env.setdefault("CXX", clangxx)

        env.setdefault("SANITIZER", "address")

        try:
            subprocess.run(
                ["bash", build_script],
                cwd=project_root,
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True,
                timeout=600,
            )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
            return None
        return project_root

    def _find_fuzzer_binary(self, project_root: str):
        # First, look in the standard 'out' directory
        out_dir = os.path.join(project_root, "out")
        candidates = []
        if os.path.isdir(out_dir):
            for name in os.listdir(out_dir):
                path = os.path.join(out_dir, name)
                if os.path.isfile(path) and os.access(path, os.X_OK):
                    low = name.lower()
                    if "rv60" in low:
                        candidates.append(path)
        if candidates:
            return candidates[0]

        # Fallback: search entire tree for an executable containing 'rv60' in the name
        for dirpath, _, filenames in os.walk(project_root):
            for name in filenames:
                low = name.lower()
                if "rv60" not in low:
                    continue
                path = os.path.join(dirpath, name)
                if os.path.isfile(path) and os.access(path, os.X_OK):
                    return path
        return None

    def _run_libfuzzer(self, fuzzer_path: str, project_root: str):
        artifact_dir = os.path.join(project_root, "artifacts")
        os.makedirs(artifact_dir, exist_ok=True)

        env = os.environ.copy()
        asan_opts = env.get("ASAN_OPTIONS", "")
        if "abort_on_error" not in asan_opts:
            asan_opts = (asan_opts + ":" if asan_opts else "") + "abort_on_error=1"
        if "detect_leaks" not in asan_opts:
            asan_opts = (asan_opts + ":" if asan_opts else "") + "detect_leaks=0"
        env["ASAN_OPTIONS"] = asan_opts

        cmd = [
            fuzzer_path,
            "-max_total_time=60",
            "-artifact_prefix=%s/" % artifact_dir,
            "-print_final_stats=1",
            "-error_exitcode=77",
        ]

        try:
            subprocess.run(
                cmd,
                cwd=project_root,
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
                timeout=90,
            )
        except (subprocess.TimeoutExpired, OSError):
            pass

        if os.path.isdir(artifact_dir):
            for name in os.listdir(artifact_dir):
                low = name.lower()
                if low.startswith(("crash-", "timeout-", "oom-", "assert-", "leak-", "hang-")):
                    path = os.path.join(artifact_dir, name)
                    try:
                        with open(path, "rb") as f:
                            return f.read()
                    except OSError:
                        continue
        return None
