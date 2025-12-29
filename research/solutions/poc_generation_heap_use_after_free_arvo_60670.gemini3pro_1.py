class Solution:
    def solve(self, src_path: str) -> bytes:
        return b"""(handleunknown allow)
(mls true)
(class c (p))
(classorder (c))
(sid kernel)
(sidorder (kernel))
(user u)
(role r)
(type t)
(sensitivity s0)
(sensitivityorder (s0))
(sidcontext kernel (u r t ((s0) (s0))))
(macro m ((classpermission n))
    (classpermissionset n (c (p)))
)
(call m (c (p)))
"""