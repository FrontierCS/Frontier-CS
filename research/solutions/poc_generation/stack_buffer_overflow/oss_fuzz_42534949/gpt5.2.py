import os
import re
import tarfile
import zipfile
from typing import Optional


class Solution:
    def solve(self, src_path: str) -> bytes:
        return b"-" + (b"9" * 15)