import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        return b"<?php\n$o=new stdClass;$o->p=1;try{$o->p/=0;}catch(Throwable $e){}\n"
