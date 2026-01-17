#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

int query(int i, int j) {
    std::cout << "? " << i << " " << j << std::endl;
    int result;
    std::cin >> result;
    if (result == -1) exit(0);
    return result;
}

void answer(const std::vector<int>& p) {
    std::cout << "! ";
    for (size_t i = 1; i < p.size(); ++i) {
        std::cout << p[i] << (i == p.size() - 1 ? "" : " ");
    }
    std::cout << std::endl;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n;
    std::cin >> n;

    std::vector<int> p(n + 1, -1);
    
    // Step 1: Determine p[1]
    int p1_val = (1 << 12) - 1; 
    std::vector<int> o1(n + 1);
    for (int i = 2; i <= n; ++i) {
        o1[i] = query(1, i);
        p1_val &= o1[i];
    }
    p[1] = p1_val;

    // Step 2 & 3: Find candidate indices for 0
    std::vector<int> zero_candidates;
    bool p1_could_be_zero = true;
    for (int i = 2; i <= n; ++i) {
        if (o1[i] == p[1]) {
            zero_candidates.push_back(i);
        } else {
            p1_could_be_zero = false;
        }
    }

    if (p1_could_be_zero) {
        // If all o1[i] are equal, p[1] could be 0.
        // The values p[2..n] are submasks of p[1]. If p[1] has few bits,
        // there might not be enough distinct values for a permutation.
        // This implies p[1] must be 0 for a valid permutation.
        bool all_equal = true;
        for (int i = 3; i <= n; ++i) {
            if (o1[i] != o1[2]) {
                all_equal = false;
                break;
            }
        }
        if (all_equal) {
             zero_candidates.insert(zero_candidates.begin(), 1);
        }
    }
    
    // Step 4: Test candidates and find the permutation
    for (int z_cand : zero_candidates) {
        std::vector<int> p_cand(n + 1);
        p_cand[z_cand] = 0;
        bool possible = true;
        
        for (int i = 1; i <= n; ++i) {
            if (i == z_cand) continue;
            if (i == 1) {
                p_cand[i] = p[1];
            } else if (z_cand == 1) {
                p_cand[i] = o1[i];
            } else {
                p_cand[i] = query(z_cand, i);
            }
        }

        std::vector<bool> seen(n, false);
        bool is_perm = true;
        for (int i = 1; i <= n; ++i) {
            if (p_cand[i] >= n || seen[p_cand[i]]) {
                is_perm = false;
                break;
            }
            seen[p_cand[i]] = true;
        }

        if (is_perm) {
            p = p_cand;
            break;
        }
    }
    
    // Fallback if no candidate from submasks worked. p[1] must be 0.
    if(p[1] == -1 || p[zero_candidates[0]] != 0) {
        p[1] = 0;
        for(int i = 2; i <= n; ++i) {
            p[i] = o1[i];
        }
    }


    answer(p);

    return 0;
}