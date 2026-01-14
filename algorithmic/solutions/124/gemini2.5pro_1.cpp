#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <map>

int n;

bool ask(const std::vector<int>& indices) {
    std::cout << "? " << indices.size();
    for (int i : indices) {
        std::cout << " " << i;
    }
    std::cout << std::endl;
    int result;
    std::cin >> result;
    return result == 1;
}

void answer(const std::vector<int>& p) {
    std::cout << "!";
    for (int i = 1; i <= n; ++i) {
        std::cout << " " << p[i];
    }
    std::cout << std::endl;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    std::cin >> n;

    std::vector<int> p(n + 1, 0);
    std::vector<int> p_parity_wrt_1(n + 1);
    
    std::vector<int> p1_group_indices, p0_group_indices;
    p1_group_indices.push_back(1);
    p_parity_wrt_1[1] = 0;

    for (int i = 2; i <= n; ++i) {
        if (ask({1, i})) {
            p_parity_wrt_1[i] = 0;
            p1_group_indices.push_back(i);
        } else {
            p_parity_wrt_1[i] = 1;
            p0_group_indices.push_back(i);
        }
    }

    std::vector<int> odd_indices, even_indices;
    int val_at_known_idx = -1, known_idx = -1;

    int m = n / 2;
    std::vector<int> query_indices = p1_group_indices;
    bool found = false;
    for (int j : p0_group_indices) {
        query_indices.push_back(j);
        if (ask(query_indices)) {
            odd_indices = p1_group_indices;
            even_indices = p0_group_indices;
            known_idx = j;
            val_at_known_idx = m;
            found = true;
            break;
        }
        query_indices.pop_back();
    }

    if (!found) {
        query_indices = p0_group_indices;
        for (int j : p1_group_indices) {
            if (j == 1) continue;
            query_indices.push_back(j);
            if (ask(query_indices)) {
                odd_indices = p0_group_indices;
                even_indices = p1_group_indices;
                known_idx = j;
                val_at_known_idx = (m % 2 != 0) ? m : -1; 
                if (val_at_known_idx == -1) { // m is even, p_j has to be m+1 if m+1 is odd
                    val_at_known_idx = m+1;
                }
                found = true;
                break;
            }
            query_indices.pop_back();
        }
    }

    if (!found) {
        // This case implies no p_j makes the sum divisible, which should not happen
        // unless m is odd and we test P1+j. Or m+1 is odd and we test P0+j.
        // Let's test for p_1.
        query_indices = p0_group_indices;
        query_indices.push_back(1);
        if(ask(query_indices)) {
             odd_indices = p0_group_indices;
             even_indices = p1_group_indices;
             known_idx = 1;
             val_at_known_idx = (m%2 != 0) ? m : -1;
             if (val_at_known_idx == -1) {
                val_at_known_idx = m+1;
             }
        } else {
            // Should be the only remaining case: p_1 is in odd group and no other element satisfied the condition
            odd_indices = p1_group_indices;
            even_indices = p0_group_indices;
            if (m % 2 != 0) { // m is odd, should be in odd group
                known_idx = 1;
                val_at_known_idx = m;
            }
        }
    }
    
    p[known_idx] = val_at_known_idx;
    int partner_val = n + 1 - val_at_known_idx;
    
    std::vector<int>* partner_group;
    if (std::find(odd_indices.begin(), odd_indices.end(), known_idx) != odd_indices.end()) {
        partner_group = &even_indices;
    } else {
        partner_group = &odd_indices;
    }

    std::vector<int> partner_candidates;
    for(int idx : *partner_group) {
        if(p[idx] == 0) partner_candidates.push_back(idx);
    }
    
    int c_known_idx = -1;
    if(partner_candidates.size() == 1) {
        c_known_idx = partner_candidates[0];
    } else {
        std::vector<int> k_indices;
        auto& group_of_known = (partner_group == &even_indices) ? odd_indices : even_indices;
        for(int k_cand : group_of_known) {
            if (k_cand != known_idx) {
                k_indices.push_back(k_cand);
                if (k_indices.size() >= 10) break;
            }
        }
        
        std::map<std::vector<bool>, std::vector<int>> masks;
        for (int j : partner_candidates) {
            std::vector<bool> mask;
            for (int k : k_indices) {
                mask.push_back(ask({known_idx, j, k}));
            }
            masks[mask].push_back(j);
        }
        
        for (auto const& [mask, v] : masks) {
            bool check = true;
            for(bool b : mask) {
                if (b) { // (p[known] + p[j] + p[k]) % 3 == 0. If j is partner, (n+1+p[k])%3==0
                    check = false; // Heuristically assume not all p[k] satisfy this
                }
            }
            if(check && v.size() == 1) {
                c_known_idx = v[0];
                break;
            }
        }
        if(c_known_idx == -1) {
            // Fallback
             for (auto const& [mask, v] : masks) {
                if(v.size() == 1) {
                    c_known_idx = v[0];
                    break;
                }
            }
        }
        if(c_known_idx == -1) c_known_idx = partner_candidates[0];
    }
    
    p[c_known_idx] = partner_val;
    
    for(int i = 1; i <= n; ++i) {
        if(p[i] == 0) {
            if(p_parity_wrt_1[i] == p_parity_wrt_1[known_idx]) { // same group as known_idx
                if(ask({known_idx, c_known_idx, i})) {
                    p[i] = (p[known_idx] % 3 == 1) ? (n+1-1) : ( (p[known_idx]%3==2) ? (n+1-2) : (n+1-3));
                }
            } else { // different group
                if(ask({known_idx, i})) {
                   // same parity
                } else {
                   // different parity
                }
            }
        }
    }

    std::vector<int> partner(n+1, 0);
    partner[known_idx] = c_known_idx;
    partner[c_known_idx] = known_idx;

    auto find_partner_of = [&](int i, std::vector<int>& candidates) {
        if(candidates.size() == 1) return candidates[0];
        
        for(int j : candidates) {
            if(!ask({known_idx, c_known_idx, i, j})) {
                 return j;
            }
        }
        return candidates.back(); // fallback
    };
    
    for(int i = 1; i <= n; ++i) {
        if(p[i] != 0 || partner[i] != 0) continue;
        
        std::vector<int> cands;
        bool i_is_odd;
        if (std::find(odd_indices.begin(), odd_indices.end(), i) != odd_indices.end()) {
            i_is_odd = true;
            for(int j : even_indices) if(p[j] == 0 && partner[j] == 0) cands.push_back(j);
        } else {
            i_is_odd = false;
            for(int j : odd_indices) if(p[j] == 0 && partner[j] == 0) cands.push_back(j);
        }
        int pi = find_partner_of(i, cands);
        partner[i] = pi;
        partner[pi] = i;
    }
    
    for(int i = 1; i <= n; ++i) {
        if(p[i] != 0) continue;
        int pi = partner[i];
        
        int p_mod_3 = -1;
        if(ask({known_idx, i, c_known_idx})) { // p_known + p_i + p_c_known
             p_mod_3 = (-(p[known_idx] + p[c_known_idx])) % 3;
             if(p_mod_3 < 0) p_mod_3 += 3;
        } else {
            for(int r=0; r<3; ++r) {
                 if((p[known_idx] + p[c_known_idx] + r)%3 != 0) {
                     p_mod_3 = r;
                     break;
                 }
            }
        }
        
        bool i_is_odd = (std::find(odd_indices.begin(), odd_indices.end(), i) != odd_indices.end());

        for(int v=1; v<=n/2; ++v) {
            if(p[v] != 0 || p[partner[v]] != 0) { // value already taken
                 bool used=false;
                 for(int k=1; k<=n; ++k) if(p[k] == v) used=true;
                 if(used) continue;
            }
            int u = n+1-v;
            bool v_is_odd = (v%2!=0);
            
            if(i_is_odd == v_is_odd) { // p[i] could be v
                if(v%3 == p_mod_3) {
                    p[i] = v;
                    p[pi] = u;
                    break;
                }
            } else { // p[i] could be u
                 if(u%3 == p_mod_3) {
                    p[i] = u;
                    p[pi] = v;
                    break;
                }
            }
        }
    }


    if (p[1] > n / 2) {
        for (int i = 1; i <= n; ++i) {
            p[i] = n + 1 - p[i];
        }
    }

    answer(p);

    return 0;
}