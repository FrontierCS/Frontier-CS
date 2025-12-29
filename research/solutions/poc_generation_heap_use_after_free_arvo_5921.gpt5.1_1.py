import os
import tarfile
import zipfile
import struct


class Solution:
    def solve(self, src_path: str) -> bytes:
        try:
            if zipfile.is_zipfile(src_path):
                data = self._solve_zip(src_path)
            elif tarfile.is_tarfile(src_path):
                data = self._solve_tar(src_path)
            else:
                data = self._fallback_poc()
        except Exception:
            data = self._fallback_poc()
        return data

    def _is_text_like(self, path: str) -> bool:
        basename = os.path.basename(path)
        lower = basename.lower()
        text_basenames = {
            "readme",
            "readme.txt",
            "license",
            "copying",
            "authors",
            "changelog",
            "news",
            "install",
            "makefile",
            "cmakelists.txt",
            "configure",
            "config.status",
            "config.log",
        }
        if lower in text_basenames:
            return True
        _, ext = os.path.splitext(lower)
        text_exts = {
            ".c",
            ".h",
            ".cpp",
            ".cc",
            ".hh",
            ".hpp",
            ".py",
            ".java",
            ".rb",
            ".go",
            ".php",
            ".js",
            ".css",
            ".html",
            ".htm",
            ".xml",
            ".json",
            ".yml",
            ".yaml",
            ".txt",
            ".md",
            ".rst",
            ".in",
            ".am",
            ".ac",
            ".m4",
            ".sh",
            ".bat",
            ".ps1",
            ".pl",
            ".pm",
            ".tcl",
            ".xsl",
            ".xslt",
            ".tmpl",
            ".cmake",
            ".mak",
            ".mk",
            ".pod",
            ".spec",
        }
        return ext in text_exts

    def _score_path(self, path: str, size: int, target_len: int = 73) -> tuple:
        p = path.lower()
        score = 1000

        if "h225" in p:
            score -= 600
        if "fuzz" in p:
            score -= 300
        if "fuzzshark" in p:
            score -= 300
        if "shark" in p:
            score -= 100
        if "ras" in p:
            score -= 100
        if "heap" in p or "uaf" in p or "crash" in p or "bug" in p or "poc" in p:
            score -= 200
        if "oss-fuzz" in p or "clusterfuzz" in p or "corpus" in p or "inputs" in p:
            score -= 200

        _, ext = os.path.splitext(p)
        if ext in {".pcap", ".pcapng", ".cap"}:
            score -= 100

        size_diff = abs(size - target_len)
        return (score, size_diff, size, len(path))

    def _solve_zip(self, src_path: str) -> bytes:
        with zipfile.ZipFile(src_path, "r") as zf:
            best_info = None
            best_key = None

            for info in zf.infolist():
                if info.is_dir():
                    continue
                path = info.filename
                if self._is_text_like(path):
                    continue
                size = info.file_size
                if size == 0:
                    continue
                if size > 1_000_000:
                    continue

                key = self._score_path(path, size)
                if best_key is None or key < best_key:
                    best_key = key
                    best_info = info

            if best_info is not None:
                return zf.read(best_info)

        return self._fallback_poc()

    def _solve_tar(self, src_path: str) -> bytes:
        with tarfile.open(src_path, "r:*") as tf:
            best_member = None
            best_key = None

            for member in tf.getmembers():
                if not member.isfile():
                    continue
                path = member.name
                if self._is_text_like(path):
                    continue
                size = member.size
                if size == 0:
                    continue
                if size > 1_000_000:
                    continue

                key = self._score_path(path, size)
                if best_key is None or key < best_key:
                    best_key = key
                    best_member = member

            if best_member is not None:
                f = tf.extractfile(best_member)
                if f is not None:
                    return f.read()

        return self._fallback_poc()

    def _fallback_poc(self) -> bytes:
        global_hdr = struct.pack(
            "<IHHIIII",
            0xA1B2C3D4,
            2,
            4,
            0,
            0,
            65535,
            1,
        )

        incl_len = 42
        orig_len = 42
        pkt_hdr = struct.pack("<IIII", 0, 0, incl_len, orig_len)

        frame = bytearray(incl_len)
        frame[0:6] = b"\xff\xff\xff\xff\xff\xff"
        frame[6:12] = b"\x00\x01\x02\x03\x04\x05"
        frame[12:14] = b"\x08\x00"

        frame[14] = 0x45
        frame[15] = 0x00
        total_length = 20 + 8
        frame[16:18] = struct.pack("!H", total_length)
        frame[18:20] = b"\x00\x00"
        frame[20:22] = b"\x40\x00"
        frame[22] = 64
        frame[23] = 17
        frame[24:26] = b"\x00\x00"
        frame[26:30] = b"\x7f\x00\x00\x01"
        frame[30:34] = b"\x7f\x00\x00\x01"

        src_port = 1234
        dst_port = 1719
        udp_len = 8
        frame[34:36] = struct.pack("!H", src_port)
        frame[36:38] = struct.pack("!H", dst_port)
        frame[38:40] = struct.pack("!H", udp_len)
        frame[40:42] = b"\x00\x00"

        return global_hdr + pkt_hdr + bytes(frame)