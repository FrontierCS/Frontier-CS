import os
import re
import sys
import textwrap


class Solution:
    def solve(self, resources_path: str) -> dict:
        rp = os.path.abspath(resources_path)

        fuzzer_code = textwrap.dedent(
            f"""
            import os
            import re
            import sys
            import time
            import random

            RESOURCES_PATH = {rp!r}

            _INITED = False
            _CORPUS = []
            _POS = 0
            _CALLS = 0
            _START = 0.0

            def _try_read(path):
                try:
                    with open(path, "r", encoding="utf-8", errors="ignore") as f:
                        return f.read()
                except Exception:
                    return ""

            def _find_resources_root():
                # Prefer embedded RESOURCES_PATH; if missing, attempt heuristic search
                if RESOURCES_PATH and os.path.isdir(RESOURCES_PATH):
                    return RESOURCES_PATH
                cwd = os.getcwd()
                cand = cwd
                for _ in range(6):
                    if os.path.isfile(os.path.join(cand, "sql_grammar.txt")) and os.path.isdir(os.path.join(cand, "sql_engine")):
                        return cand
                    cand2 = os.path.join(cand, "resources")
                    if os.path.isfile(os.path.join(cand2, "sql_grammar.txt")) and os.path.isdir(os.path.join(cand2, "sql_engine")):
                        return cand2
                    parent = os.path.dirname(cand)
                    if parent == cand:
                        break
                    cand = parent
                # fallback: search in cwd for sql_grammar.txt
                try:
                    for root, dirs, files in os.walk(cwd):
                        if "sql_grammar.txt" in files and "sql_engine" in dirs:
                            return root
                except Exception:
                    pass
                return RESOURCES_PATH or cwd

            def _extract_keywords(text):
                kws = set()
                # quoted strings that look like keywords
                for m in re.finditer(r"(?<![A-Za-z0-9_])'([A-Z][A-Z0-9_]{{1,}})'(?![A-Za-z0-9_])", text):
                    kws.add(m.group(1))
                # bare uppercase words from grammar / code
                for m in re.finditer(r"\\b([A-Z][A-Z0-9_]{{1,}})\\b", text):
                    w = m.group(1)
                    kws.add(w)
                stop = {{
                    "EOF","EOL","WS","WHITESPACE","IDENT","IDENTIFIER","ID","NAME","STRING","STR","NUMBER","NUM","INT","INTEGER",
                    "FLOAT","REAL","BOOL","BOOLEAN","NULL","TRUE","FALSE","TOKEN","TOK","ERROR","EXPR","STMT","CLAUSE",
                    "PRIMARY","KEY","FOREIGN","REFERENCES","CHECK","DEFAULT","UNIQUE","NOT","AND","OR","IN","IS","LIKE","BETWEEN",
                    "AS","ON","USING","BY","INTO","VALUES","SET","FROM","WHERE","SELECT","INSERT","UPDATE","DELETE","CREATE","DROP",
                    "TABLE","INDEX","VIEW","TRIGGER","ALTER","JOIN","LEFT","RIGHT","FULL","OUTER","INNER","CROSS","NATURAL",
                    "GROUP","HAVING","ORDER","LIMIT","OFFSET","DISTINCT","ALL","UNION","EXCEPT","INTERSECT","CASE","WHEN","THEN","ELSE","END",
                    "BEGIN","COMMIT","ROLLBACK","SAVEPOINT","RELEASE","PRAGMA","EXPLAIN","ANALYZE","VACUUM"
                }}
                kws2 = set()
                for k in kws:
                    if 2 <= len(k) <= 20 and k.isupper() and k not in stop:
                        kws2.add(k)
                return sorted(kws2)

            def _compact_spaces(s):
                s = re.sub(r"[ \\t\\r\\f\\v]+", " ", s).strip()
                s = re.sub(r" *([(),;+*/%<>=-]) *", r"\\1", s)
                return s

            def _decorate(rng, s):
                # Add whitespace/comments/semicolons to exercise tokenizer edges.
                pre = ""
                post = ""
                r = rng.random()
                if r < 0.10:
                    pre = "--c\\n"
                elif r < 0.18:
                    pre = "/*c*/ "
                elif r < 0.23:
                    pre = "/*c\\n*/ "
                # trailing
                r = rng.random()
                if r < 0.30:
                    post = ";"
                elif r < 0.35:
                    post = ";;"
                elif r < 0.39:
                    post = " ; --e\\n"
                elif r < 0.42:
                    post = " /*e*/"
                # weird spacing
                if rng.random() < 0.12:
                    s = s.replace(" ", "\\t")
                elif rng.random() < 0.12:
                    s = s.replace(" ", "\\n")
                return pre + s + post

            def _mutate(rng, s, keywords):
                if not s:
                    return s
                ops = rng.randrange(10)
                if ops == 0:
                    # flip case randomly
                    out = []
                    for ch in s:
                        if "a" <= ch <= "z" and rng.random() < 0.35:
                            out.append(ch.upper())
                        elif "A" <= ch <= "Z" and rng.random() < 0.35:
                            out.append(ch.lower())
                        else:
                            out.append(ch)
                    return "".join(out)
                elif ops == 1:
                    # insert keyword
                    kw = rng.choice(keywords) if keywords else "FOO"
                    i = rng.randrange(0, len(s) + 1)
                    return s[:i] + " " + kw + " " + s[i:]
                elif ops == 2:
                    # delete a chunk
                    if len(s) < 5:
                        return s[:-1]
                    a = rng.randrange(0, len(s) - 1)
                    b = rng.randrange(a + 1, min(len(s), a + 1 + rng.randrange(1, 8)))
                    return s[:a] + s[b:]
                elif ops == 3:
                    # duplicate a fragment
                    if len(s) < 8:
                        return s + s
                    a = rng.randrange(0, len(s) - 3)
                    b = rng.randrange(a + 1, min(len(s), a + 1 + rng.randrange(1, 10)))
                    frag = s[a:b]
                    i = rng.randrange(0, len(s) + 1)
                    return s[:i] + frag + s[i:]
                elif ops == 4:
                    # add parentheses
                    i = rng.randrange(0, len(s) + 1)
                    j = rng.randrange(i, len(s) + 1)
                    return s[:i] + "(" + s[i:j] + ")" + s[j:]
                elif ops == 5:
                    # mess with quotes
                    i = rng.randrange(0, len(s) + 1)
                    return s[:i] + "'" + s[i:]
                elif ops == 6:
                    # replace an identifier-ish token with a weird one
                    weird = rng.choice(['"select"', '"weird name"', "`from`", "[group]", "_x", "x1", "t_1", "A", "ZZ", "x$y"])
                    return re.sub(r"\\b[a-zA-Z_][a-zA-Z0-9_]*\\b", weird, s, count=1)
                elif ops == 7:
                    # add comment midstream
                    i = rng.randrange(0, len(s) + 1)
                    c = rng.choice(["/*x*/", "--x\\n", "/*unterminated", "/**/"])
                    return s[:i] + c + s[i:]
                elif ops == 8:
                    # random punctuation insertion
                    i = rng.randrange(0, len(s) + 1)
                    return s[:i] + rng.choice([",", ")", "(", "==", "!=", "<>", "::", "||", "&&", "??"]) + s[i:]
                else:
                    # swap a keyword if present
                    return re.sub(r"\\bSELECT\\b", rng.choice(["SELect", "SELECT", "SELEC", "SELECT DISTINCT"]), s, count=1)

            def _init():
                global _INITED, _CORPUS, _POS, _CALLS, _START

                if _INITED:
                    return

                _START = time.perf_counter()

                root = _find_resources_root()
                eng = os.path.join(root, "sql_engine")
                if os.path.isdir(root) and root not in sys.path:
                    sys.path.insert(0, root)

                grammar = _try_read(os.path.join(root, "sql_grammar.txt"))
                parser_py = _try_read(os.path.join(eng, "parser.py"))
                tokenizer_py = _try_read(os.path.join(eng, "tokenizer.py"))
                ast_py = _try_read(os.path.join(eng, "ast_nodes.py"))

                keywords = _extract_keywords(grammar + "\\n" + parser_py + "\\n" + tokenizer_py + "\\n" + ast_py)
                # keep some known keywords (common SQL) even if extraction fails
                base_kws = [
                    "SELECT","FROM","WHERE","INSERT","INTO","VALUES","UPDATE","SET","DELETE","CREATE","TABLE","DROP","ALTER",
                    "INDEX","VIEW","TRIGGER","JOIN","LEFT","RIGHT","INNER","OUTER","CROSS","NATURAL","ON","USING",
                    "GROUP","BY","HAVING","ORDER","LIMIT","OFFSET","DISTINCT","ALL","UNION","INTERSECT","EXCEPT",
                    "CASE","WHEN","THEN","ELSE","END","AS","AND","OR","NOT","IN","IS","NULL","LIKE","BETWEEN","EXISTS",
                    "BEGIN","COMMIT","ROLLBACK","SAVEPOINT","RELEASE","PRAGMA","EXPLAIN"
                ]
                kwset = set(keywords)
                for k in base_kws:
                    kwset.add(k)
                keywords = sorted(kwset)

                rng = random.Random(0)

                id_plain = ["t","t1","t2","users","orders","items","a","b","c","x","y","z","u","o","i","tmp","main","schema1"]
                id_quoted = ['"t"', '"select"', '"weird name"', "`t`", "`from`", "[t]", "[group]"]
                ids = id_plain + id_quoted

                cols_plain = ["id","name","value","price","qty","created_at","updated_at","col","c1","c2","x","y","z","select","from","where","group","order"]
                cols_quoted = ['"id"', '"name"', '"select"', "`group`", "[order]"]
                cols = cols_plain + cols_quoted

                types = ["INT","INTEGER","TEXT","REAL","BLOB","NUMERIC","BOOLEAN","VARCHAR(10)","CHAR(3)","DECIMAL(10,2)"]

                nums = ["0","1","2","-1","999999999","1.0",".5","-0.0","1e3","-2E-2","0.0001"]
                strs = ["''","'a'","'A'","'test'","'a''b'","'%'","'_'","'\\n'","'中文'","'\\\\'"]
                others = ["NULL","TRUE","FALSE","?","$x",":p","@q"]

                lit = nums + strs + others

                expr_atoms = [
                    "1","0","NULL","TRUE","FALSE","?","$x",":p","@q",
                    "id","name","value","t.id","t1.id","t2.id",
                    "'a'","''","'a''b'","1.0",".5","-1","1e3"
                ]
                expr_more = [
                    "id+1","id-1","id*2","id/2","id%2",
                    "name||'x'","'x'||name",
                    "NOT 0","NOT 1","-1","+1",
                    "id=1","id<>1","id!=1","id<1","id<=1","id>1","id>=1",
                    "name='a'","name LIKE 'a%'","name NOT LIKE 'a_'",
                    "id IN (1,2,3)","id NOT IN (1,2)",
                    "id BETWEEN 1 AND 2","id NOT BETWEEN 1 AND 2",
                    "id IS NULL","id IS NOT NULL",
                    "(id=1 AND name='a') OR NOT (id=2)",
                    "EXISTS (SELECT 1)",
                    "id IN (SELECT id FROM t)",
                    "CASE WHEN 1 THEN 2 ELSE 3 END",
                    "CASE WHEN id>1 THEN name ELSE 'x' END",
                    "COALESCE(NULL,1)",
                    "COUNT(*)",
                    "MAX(id)","MIN(id)","SUM(id)","AVG(id)",
                    "(SELECT 1)","(SELECT id FROM t LIMIT 1)"
                ]
                exprs = expr_atoms + expr_more

                select_list_opts = [
                    "*",
                    "1",
                    "NULL",
                    "id",
                    "name",
                    "id,name",
                    "t.id,t.name",
                    "id AS x",
                    "name AS \"alias\"",
                    "COUNT(*)",
                    "MAX(id),MIN(id)",
                    "SUM(price) AS total",
                    "id+1 AS id2",
                    "CASE WHEN 1 THEN 2 ELSE 3 END AS c",
                    "(SELECT 1) AS subq",
                ]

                from_opts = [
                    "",
                    "FROM t",
                    "FROM t AS a",
                    "FROM t a",
                    "FROM t1,t2",
                    "FROM t1 JOIN t2 ON t1.id=t2.id",
                    "FROM t1 LEFT JOIN t2 ON t1.id=t2.id",
                    "FROM t1 INNER JOIN t2 ON t1.id=t2.id",
                    "FROM (SELECT 1 AS id) sub",
                    "FROM (SELECT * FROM t) sub",
                    "FROM t1 CROSS JOIN t2",
                ]

                where_opts = [
                    "",
                    "WHERE 1",
                    "WHERE 0",
                    "WHERE id=1",
                    "WHERE id<>1",
                    "WHERE id!=1",
                    "WHERE id<1",
                    "WHERE id<=1",
                    "WHERE id>1",
                    "WHERE id>=1",
                    "WHERE name='a'",
                    "WHERE name LIKE 'a%'",
                    "WHERE name NOT LIKE 'a_'",
                    "WHERE id IN (1,2,3)",
                    "WHERE id NOT IN (1,2)",
                    "WHERE id BETWEEN 1 AND 2",
                    "WHERE id NOT BETWEEN 1 AND 2",
                    "WHERE id IS NULL",
                    "WHERE id IS NOT NULL",
                    "WHERE EXISTS (SELECT 1)",
                    "WHERE id IN (SELECT id FROM t)",
                    "WHERE (id=1 AND name='a') OR NOT (id=2)",
                    "WHERE id=?",
                ]

                group_having_opts = [
                    "",
                    "GROUP BY id",
                    "GROUP BY 1",
                    "GROUP BY id,name",
                    "GROUP BY id HAVING COUNT(*)>1",
                    "GROUP BY id HAVING 1",
                ]

                order_opts = [
                    "",
                    "ORDER BY id",
                    "ORDER BY id DESC",
                    "ORDER BY 1",
                    "ORDER BY name ASC,id DESC",
                ]

                limit_opts = [
                    "",
                    "LIMIT 1",
                    "LIMIT 0",
                    "LIMIT 10 OFFSET 5",
                    "LIMIT 5,10",
                    "LIMIT -1",
                ]

                distinct_opts = ["", "DISTINCT", "ALL"]

                corpus = []
                add = corpus.append

                # Curated "likely valid" basics
                basics = [
                    "SELECT 1",
                    "SELECT 1 FROM t",
                    "SELECT * FROM t",
                    "SELECT id,name FROM users WHERE id=1",
                    "INSERT INTO t VALUES (1,'a')",
                    "INSERT INTO t(id,name) VALUES (1,'a')",
                    "UPDATE t SET name='x' WHERE id=1",
                    "UPDATE t SET id=id+1",
                    "DELETE FROM t WHERE id=1",
                    "DELETE FROM t",
                    "CREATE TABLE t (id INT, name TEXT)",
                    "CREATE TABLE IF NOT EXISTS t (id INTEGER PRIMARY KEY, name TEXT NOT NULL, value REAL DEFAULT 0)",
                    "DROP TABLE t",
                    "DROP TABLE IF EXISTS t",
                    "CREATE INDEX idx_t_id ON t(id)",
                    "DROP INDEX idx_t_id",
                    "CREATE VIEW v AS SELECT * FROM t",
                    "DROP VIEW v",
                    "BEGIN",
                    "COMMIT",
                    "ROLLBACK",
                    "EXPLAIN SELECT * FROM t",
                    "PRAGMA cache_size=1000",
                ]
                for s in basics:
                    add(s)

                # Systematic SELECT generation (random combos)
                for _ in range(2200):
                    distinct = rng.choice(distinct_opts)
                    sl = rng.choice(select_list_opts)
                    frm = rng.choice(from_opts)
                    wh = rng.choice(where_opts)
                    gh = rng.choice(group_having_opts)
                    ob = rng.choice(order_opts)
                    lim = rng.choice(limit_opts)
                    parts = ["SELECT"]
                    if distinct:
                        parts.append(distinct)
                    parts.append(sl)
                    if frm:
                        parts.append(frm)
                    if wh:
                        parts.append(wh)
                    if gh:
                        parts.append(gh)
                    if ob:
                        parts.append(ob)
                    if lim:
                        parts.append(lim)
                    s = _compact_spaces(" ".join(parts))
                    if len(s) <= 260:
                        add(s)

                # Set operations / nested selects / CTEs
                setops = ["UNION", "UNION ALL", "INTERSECT", "EXCEPT"]
                for _ in range(500):
                    op = rng.choice(setops)
                    a = rng.choice([
                        "SELECT 1",
                        "SELECT id FROM t",
                        "SELECT name FROM t WHERE id=1",
                        "SELECT COUNT(*) FROM t",
                        "SELECT id FROM t LIMIT 1",
                    ])
                    b = rng.choice([
                        "SELECT 2",
                        "SELECT id FROM t2",
                        "SELECT name FROM t2 WHERE id=2",
                        "SELECT COUNT(*) FROM t2",
                        "SELECT id FROM t2 LIMIT 1",
                    ])
                    s = f"{a} {op} {b}"
                    add(_compact_spaces(s))

                for _ in range(250):
                    cte_name = rng.choice(["c","cte","x","r","tmp"])
                    inner = rng.choice([
                        "SELECT 1 AS id",
                        "SELECT id,name FROM t",
                        "SELECT id FROM t WHERE id IN (1,2,3)",
                        "SELECT id FROM t LIMIT 1",
                    ])
                    outer = rng.choice([
                        f"SELECT * FROM {cte_name}",
                        f"SELECT id FROM {cte_name} WHERE id=1",
                        f"SELECT COUNT(*) FROM {cte_name}",
                    ])
                    s = f"WITH {cte_name} AS ({inner}) {outer}"
                    add(_compact_spaces(s))

                # DDL / DML variations
                for _ in range(700):
                    t = rng.choice(ids)
                    c1 = rng.choice(cols)
                    c2 = rng.choice(cols)
                    ty1 = rng.choice(types)
                    ty2 = rng.choice(types)
                    constraints = rng.choice([
                        "",
                        "PRIMARY KEY",
                        "NOT NULL",
                        "UNIQUE",
                        "DEFAULT 0",
                        "DEFAULT 'x'",
                        "DEFAULT NULL",
                    ])
                    constraints2 = rng.choice([
                        "",
                        "NOT NULL",
                        "DEFAULT 1",
                        "DEFAULT 'a'",
                    ])
                    stmt = rng.choice([
                        f"CREATE TABLE {t} ({c1} {ty1} {constraints}, {c2} {ty2} {constraints2})",
                        f"CREATE TEMP TABLE {t} ({c1} {ty1}, {c2} {ty2})",
                        f"CREATE TABLE IF NOT EXISTS {t} ({c1} {ty1}, {c2} {ty2})",
                        f"CREATE TABLE {t} AS SELECT 1",
                        f"DROP TABLE {t}",
                        f"DROP TABLE IF EXISTS {t}",
                        f"CREATE INDEX idx_{rng.choice(id_plain)} ON {t}({c1})",
                        f"CREATE UNIQUE INDEX idxu_{rng.choice(id_plain)} ON {t}({c1},{c2})",
                        f"DROP INDEX idx_{rng.choice(id_plain)}",
                        f"ALTER TABLE {t} ADD COLUMN {rng.choice(cols)} {rng.choice(types)}",
                        f"ALTER TABLE {t} RENAME TO {rng.choice(id_plain)}",
                        f"CREATE VIEW v_{rng.choice(id_plain)} AS SELECT * FROM {t}",
                        f"DROP VIEW v_{rng.choice(id_plain)}",
                    ])
                    add(_compact_spaces(stmt))

                for _ in range(900):
                    t = rng.choice(ids)
                    c1 = rng.choice(cols_plain)
                    c2 = rng.choice(cols_plain)
                    v1 = rng.choice(lit)
                    v2 = rng.choice(lit)
                    stmt = rng.choice([
                        f"INSERT INTO {t} VALUES ({v1})",
                        f"INSERT INTO {t} VALUES ({v1},{v2})",
                        f"INSERT INTO {t}({c1}) VALUES ({v1})",
                        f"INSERT INTO {t}({c1},{c2}) VALUES ({v1},{v2})",
                        f"INSERT INTO {t}({c1},{c2}) VALUES ({v1},{v2}),({rng.choice(lit)},{rng.choice(lit)})",
                        f"INSERT INTO {t} SELECT {rng.choice(exprs)}",
                        f"UPDATE {t} SET {c1}={rng.choice(exprs)}",
                        f"UPDATE {t} SET {c1}={rng.choice(exprs)}, {c2}={rng.choice(exprs)} WHERE {rng.choice(exprs)}",
                        f"DELETE FROM {t}",
                        f"DELETE FROM {t} WHERE {rng.choice(exprs)}",
                    ])
                    add(_compact_spaces(stmt))

                # Tokenizer edge cases
                tok_edges = [
                    "SELECT/*c*/1",
                    "SELECT--c\\n1",
                    "SELECT 1--e",
                    "SELECT 1 /* unterminated",
                    "SELECT 'unterminated",
                    "SELECT \"unterminated",
                    "SELECT 0xFF",
                    "SELECT 01",
                    "SELECT 1..2",
                    "SELECT .",
                    "SELECT 1e+",
                    "SELECT 1E--x\\n2",
                    "SELECT 'a''b'",
                    "SELECT \"a\"\"b\"",
                    "SELECT [a]]b]",
                    "SELECT `a``b`",
                    "/* leading */ SELECT 1",
                    "-- leading\\nSELECT 1",
                    "SELECT\\t*\\nFROM\\t t\\nWHERE\\t id\\t=\\t1",
                ]
                for s in tok_edges:
                    add(s)

                # Keyword-driven "likely to trigger branches" (errors included)
                if keywords:
                    sample = keywords[:]
                    rng.shuffle(sample)
                    sample = sample[:240]
                    for kw in sample:
                        add(_compact_spaces(f"SELECT {kw} FROM t"))
                        add(_compact_spaces(f"SELECT 1 {kw} 2 FROM t"))
                        add(_compact_spaces(f"CREATE {kw} t"))
                        add(_compact_spaces(f"DROP {kw} t"))
                        add(_compact_spaces(f"INSERT {kw} t VALUES (1)"))
                        add(_compact_spaces(f"UPDATE t SET id=1 {kw}"))

                # Add decorated variants to exercise tokenization
                decorated = []
                for s in corpus[:]:
                    if rng.random() < 0.55:
                        decorated.append(_decorate(rng, s))
                corpus.extend(decorated)

                # Create a pool of invalid mutations
                muts = []
                pool = corpus[:]
                for _ in range(1800):
                    base = pool[rng.randrange(0, len(pool))]
                    m = _mutate(rng, base, keywords)
                    m = _decorate(rng, _compact_spaces(m))
                    if 0 < len(m) <= 350:
                        muts.append(m)
                corpus.extend(muts)

                # A few "nasty but bounded" random statements
                punct = ["(",")",",",";","=","<>","!=","<",">","<=",">=","+","-","*","/","%","||","AND","OR","NOT"]
                for _ in range(250):
                    parts = []
                    for _j in range(rng.randrange(6, 18)):
                        r = rng.random()
                        if r < 0.22:
                            parts.append(rng.choice(keywords) if keywords else "KW")
                        elif r < 0.44:
                            parts.append(rng.choice(ids))
                        elif r < 0.62:
                            parts.append(rng.choice(cols))
                        elif r < 0.78:
                            parts.append(rng.choice(lit))
                        else:
                            parts.append(rng.choice(punct))
                    s = " ".join(parts)
                    s = _decorate(rng, s)
                    if len(s) <= 350:
                        corpus.append(s)

                # Dedup and shuffle
                seen = set()
                out = []
                for s in corpus:
                    if not s:
                        continue
                    s2 = s.strip()
                    if not s2:
                        continue
                    if s2 in seen:
                        continue
                    seen.add(s2)
                    out.append(s2)
                rng.shuffle(out)

                _CORPUS = out
                _POS = 0
                _CALLS = 0
                _INITED = True

            def fuzz(parse_sql):
                global _INITED, _CORPUS, _POS, _CALLS, _START

                if not _INITED:
                    _init()

                # Stop near end of budget to avoid starting a long parse near cutoff
                if (time.perf_counter() - _START) > 58.5:
                    return False

                # Keep parse_sql calls low for efficiency bonus.
                # Use 3-4 calls with large batches.
                if _CALLS >= 4:
                    return False

                remaining = len(_CORPUS) - _POS
                if remaining <= 0:
                    return False

                if _CALLS == 0:
                    batch_n = 2600
                elif _CALLS == 1:
                    batch_n = 2600
                elif _CALLS == 2:
                    batch_n = 1800
                else:
                    batch_n = 1400

                end = _POS + batch_n
                if end > len(_CORPUS):
                    end = len(_CORPUS)

                batch = _CORPUS[_POS:end]
                _POS = end
                _CALLS += 1

                parse_sql(batch)
                return True
            """
        ).lstrip()

        return {"code": fuzzer_code}