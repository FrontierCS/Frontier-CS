#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <map>

int n;

int do_query(const std::vector<int>& q) {
    std::cout << "0";
    for (int i = 0; i < n; ++i) {
        std::cout << " " << q[i];
    }
    std::cout << std::endl;
    int result;
    std::cin >> result;
    if (result == -1) exit(0);
    return result;
}

void guess_permutation(const std::vector<int>& perm) {
    std::cout << "1";
    for (int i = 0; i < n; ++i) {
        std::cout << " " << perm[i];
    }
    std::cout << std::endl;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    std::cin >> n;

    std::vector<int> p(n + 1);
    std::vector<bool> p_found(n + 1, false);
    std::vector<bool> val_used(n + 1, false);

    int block_size = 400;
    if (n <= 500) block_size = 150;
    if (n <= 200) block_size = 50;
    if (n <= 60) block_size = n;


    for (int start_idx = 1; start_idx <= n; start_idx += block_size) {
        int end_idx = std::min(start_idx + block_size - 1, n);
        
        // Step 1: Find the set of values for the current block
        std::vector<int> vals_to_check;
        for (int v = 1; v <= n; ++v) {
            if (!val_used[v]) {
                vals_to_check.push_back(v);
            }
        }

        std::vector<int> current_block_vals;
        if (!vals_to_check.empty()) {
            std::map<int, std::vector<int>> responses;
            std::vector<int> q(n);
            
            for (int v : vals_to_check) {
                for (int i = 1; i <= n; ++i) {
                    if (i >= start_idx && i <= end_idx) {
                        q[i-1] = v;
                    } else {
                        if (p_found[i]) {
                            q[i-1] = p[i];
                        } else {
                            q[i-1] = 1; // Any constant filler works
                        }
                    }
                }
                responses[do_query(q)].push_back(v);
            }

            if (responses.size() <= 1) { 
                current_block_vals = vals_to_check;
            } else {
                size_t max_freq = 0;
                int C_response = -1;
                for(auto const& [resp, vals] : responses) {
                    if (vals.size() > max_freq) {
                        max_freq = vals.size();
                        C_response = resp;
                    }
                }
                for(auto const& [resp, vals] : responses) {
                    if (resp != C_response) {
                        current_block_vals.insert(current_block_vals.end(), vals.begin(), vals.end());
                    }
                }
            }
        }
        
        // Step 2: Match values to positions
        int s0 = -1;
        for(int v : vals_to_check) {
            bool in_block = false;
            for(int bv : current_block_vals) {
                if(v == bv) {
                    in_block = true;
                    break;
                }
            }
            if(!in_block) {
                s0 = v;
                break;
            }
        }
        
        if (s0 == -1) {
             for(int v=1; v<=n; ++v) { if(val_used[v]) { s0 = v; break; } }
             if (s0 == -1) s0 = 1; // Case n=block_size
        }

        std::vector<int> base_q(n);
        for (int i = 1; i <= n; ++i) {
             if (p_found[i]) {
                base_q[i-1] = p[i];
            } else {
                base_q[i-1] = s0;
            }
        }
        int C = do_query(base_q);

        for (int val : current_block_vals) {
            std::vector<int> unknown_indices;
            for(int i = start_idx; i <= end_idx; ++i) {
                if(!p_found[i]) unknown_indices.push_back(i);
            }

            int L = 0, R = unknown_indices.size() - 1;
            int pos_idx = -1;

            while (L <= R) {
                if (L == R) {
                    pos_idx = L;
                    break;
                }
                int mid_idx = L + (R - L) / 2;
                std::vector<int> q = base_q;
                for (int i = L; i <= mid_idx; ++i) {
                    q[unknown_indices[i]-1] = val;
                }
                
                if (do_query(q) > C) {
                    R = mid_idx;
                } else {
                    L = mid_idx + 1;
                }
            }
            int final_pos = unknown_indices[pos_idx];
            p[final_pos] = val;
            p_found[final_pos] = true;
            val_used[val] = true;
            base_q[final_pos-1] = val; 
            C++;
        }
    }

    std::vector<int> final_p(n);
    for(int i = 0; i < n; ++i) final_p[i] = p[i+1];
    guess_permutation(final_p);

    return 0;
}