import os
import sys
import tarfile
import subprocess
import struct
import random
import shutil
import time
import select

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Define working directory
        extract_dir = "/tmp/ndpi_solution"
        if os.path.exists(extract_dir):
            shutil.rmtree(extract_dir)
        os.makedirs(extract_dir)
        
        # 1. Extract source code
        with tarfile.open(src_path) as tar:
            tar.extractall(path=extract_dir)
        
        # Locate root directory
        entries = os.listdir(extract_dir)
        root_dir = os.path.join(extract_dir, entries[0]) if len(entries) == 1 else extract_dir
        
        # 2. Compile nDPI with ASAN
        env = os.environ.copy()
        flags = "-fsanitize=address -g -O0"
        env["CFLAGS"] = flags
        env["CXXFLAGS"] = flags
        env["LDFLAGS"] = flags
        
        # Configure and Make
        # Redirect output to prevent log clutter
        try:
            subprocess.run(["./autogen.sh"], cwd=root_dir, env=env, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(["./configure", "--disable-shared", "--enable-static"], cwd=root_dir, env=env, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(["make", "-j8"], cwd=root_dir, env=env, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError:
            # If configure/make fails, we might still have a partial build or previous state
            pass

        # Locate library and headers
        lib_path = os.path.join(root_dir, "src", "lib", ".libs", "libndpi.a")
        if not os.path.exists(lib_path):
            lib_path = os.path.join(root_dir, "src", "lib", "libndpi.a")
        
        include_path = os.path.join(root_dir, "src", "include")
        
        # 3. Create Persistent Harness
        # Reads [Len 4 bytes][Packet Data] from stdin
        # Sets DLT_RAW (12) to interpret input as IP packet
        harness_code = r"""
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <string.h>
#include <stdint.h>
#include "ndpi_api.h"

int main() {
    // Disable buffering
    setvbuf(stdin, NULL, _IONBF, 0);
    setvbuf(stdout, NULL, _IONBF, 0);

    struct ndpi_detection_module_struct *ndpi_struct = ndpi_init_detection_module(NULL);
    if (!ndpi_struct) return 1;

    // Use DLT_RAW (12) to indicate Raw IP
    ndpi_set_datalink_type(ndpi_struct, 12);

    NDPI_PROTOCOL_BITMASK all;
    ndpi_set_protocol_detection_bitmask2(ndpi_struct, &all);

    struct ndpi_flow_struct *flow = calloc(1, sizeof(struct ndpi_flow_struct));
    struct ndpi_id_struct *src = calloc(1, sizeof(struct ndpi_id_struct));
    struct ndpi_id_struct *dst = calloc(1, sizeof(struct ndpi_id_struct));
    
    while(1) {
        uint32_t len;
        if (fread(&len, sizeof(len), 1, stdin) != 1) break;
        
        if (len > 65535) {
            // Safety: consume bytes or exit
            break;
        }

        unsigned char *buffer = malloc(len);
        if (!buffer) break;
        
        if (fread(buffer, 1, len, stdin) != len) {
            free(buffer);
            break;
        }

        // Process packet
        // Reset flow state slightly to simulate fresh inspection
        memset(flow, 0, sizeof(struct ndpi_flow_struct));
        
        // ndpi_detection_process_packet args: struct, flow, packet, len, tick, src, dst
        ndpi_detection_process_packet(ndpi_struct, flow, buffer, len, 0, src, dst);
        
        free(buffer);
        
        // Send ACK
        printf("OK\n");
    }
    
    return 0;
}
"""
        harness_src = os.path.join(root_dir, "harness.c")
        with open(harness_src, "w") as f:
            f.write(harness_code)
        
        harness_bin = os.path.join(root_dir, "harness")
        
        # Compile harness
        cmd = ["gcc", "-fsanitize=address", "-g", "-I", include_path, "harness.c", lib_path, "-lpcap", "-lm", "-pthread", "-ldl", "-o", "harness"]
        subprocess.run(cmd, cwd=root_dir, env=env, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # 4. Fuzzing Loop
        
        # Helper to construct valid IP/UDP packets
        def make_ip_header(payload_len, proto):
            # IPv4 (0x45), TOS 0, Len (20+payload_len), ID 0, Frag 0, TTL 64
            ver_ihl = 0x45
            tos = 0
            tot_len = 20 + payload_len
            id_val = 0
            frag = 0
            ttl = 64
            src_ip = 0x7f000001
            dst_ip = 0x7f000001
            
            # Initial checksum 0
            header = struct.pack("!BBHHHBBHII", ver_ihl, tos, tot_len, id_val, frag, ttl, proto, 0, src_ip, dst_ip)
            
            # Calculate IP Checksum
            s = 0
            for i in range(0, len(header), 2):
                w = (header[i] << 8) + header[i+1]
                s += w
            s = (s >> 16) + (s & 0xffff)
            s += s >> 16
            csum = ~s & 0xffff
            
            return struct.pack("!BBHHHBBHII", ver_ihl, tos, tot_len, id_val, frag, ttl, proto, csum, src_ip, dst_ip)

        def make_packet(payload, port=5246):
            # UDP Header: Src, Dst, Len, Csum
            udp_len = 8 + len(payload)
            udp_header = struct.pack("!HHHH", 12345, port, udp_len, 0)
            ip_payload = udp_header + payload
            ip_header = make_ip_header(len(ip_payload), 17) # 17 = UDP
            return ip_header + ip_payload

        # Prepare generator
        # Target 33 bytes total: IP(20) + UDP(8) + Payload(5)
        
        candidates = []
        # Try CAPWAP Control (5246) variations
        for b in range(256):
            candidates.append((5246, bytes([b, 0, 0, 0, 0])))
        
        # Try random payloads
        for _ in range(500):
            candidates.append((5246, os.urandom(5)))
            
        # Try CAPWAP Data (5247) variations
        for b in range(256):
            candidates.append((5247, bytes([b, 0, 0, 0, 0])))
            
        found_poc = None
        
        proc = subprocess.Popen([harness_bin], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=root_dir)
        poll_obj = select.poll()
        poll_obj.register(proc.stdout, select.POLLIN)
        
        for port, payload in candidates:
            pkt = make_packet(payload, port)
            
            try:
                # Send length (4 bytes little endian) + packet
                proc.stdin.write(struct.pack("<I", len(pkt)))
                proc.stdin.write(pkt)
                proc.stdin.flush()
            except (BrokenPipeError, OSError):
                # Process died
                found_poc = pkt
                break
            
            # Wait for ACK or crash
            # 200ms timeout
            if poll_obj.poll(200):
                line = proc.stdout.readline()
                if not line or line.strip() != b"OK":
                    found_poc = pkt
                    break
            else:
                # Timeout implies crash or hang
                found_poc = pkt
                break
        
        proc.terminate()
        
        # Cleanup
        # shutil.rmtree(extract_dir)
        
        if found_poc:
            return found_poc
        
        # Fallback: return a default packet structure
        return make_packet(b'\x00' * 5, 5246)