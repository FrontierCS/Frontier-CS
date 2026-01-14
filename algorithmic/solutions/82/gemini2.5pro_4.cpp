#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <map>

// Function to perform a query and handle judge's -1 response.
int query(int i, int j) {
    std::cout << "? " << i << " " << j << std::endl;
    int result;
    std::cin >> result;
    if (result == -1) {
        exit(0);
    }
    return result;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n;
    std::cin >> n;

    std::vector<int> p(n + 1, -1);
    std::vector<int> o1(n + 1);

    // Step 1: Find p[1] by querying it against all other elements.
    int p1_val = -1;
    for (int i = 2; i <= n; ++i) {
        o1[i] = query(1, i);
        if (p1_val == -1) {
            p1_val = o1[i];
        } else {
            p1_val &= o1[i];
        }
    }
    p[1] = p1_val;

    std::vector<bool> used(n, false);
    used[p[1]] = true;

    // Step 2: Use propagation to find as many p[i] as possible.
    while (true) {
        bool changed = false;
        
        std::map<int, std::vector<int>> candidate_vals;
        for (int x = 0; x < n; ++x) {
            if (!used[x]) {
                candidate_vals[p[1] | x].push_back(x);
            }
        }
        
        for (int i = 2; i <= n; ++i) {
            if (p[i] == -1) {
                if (candidate_vals.count(o1[i]) && candidate_vals[o1[i]].size() == 1) {
                    int val = candidate_vals[o1[i]][0];
                    p[i] = val;
                    used[val] = true;
                    changed = true;
                }
            }
        }
        
        if (!changed) {
            break;
        }
    }
    
    // Step 3: Resolve any remaining ambiguities.
    int known_idx_not_1 = -1;
    for (int i = 2; i <= n; ++i) {
        if (p[i] != -1) {
            known_idx_not_1 = i;
            break;
        }
    }

    if (known_idx_not_1 != -1) {
        // A second reference point was found via propagation.
        for (int i = 2; i <= n; ++i) {
            if (p[i] == -1) {
                int res = query(i, known_idx_not_1);
                
                std::vector<int> current_candidates;
                for (int x = 0; x < n; ++x) {
                    if (!used[x] && (p[1] | x) == o1[i]) {
                        current_candidates.push_back(x);
                    }
                }

                for (int cand_val : current_candidates) {
                    if ((cand_val | p[known_idx_not_1]) == res) {
                        p[i] = cand_val;
                        used[cand_val] = true;
                        break;
                    }
                }
            }
        }
    } else {
        // Propagation failed to find any p[i] for i > 1.
        // This is a rare case. Find p[2] from scratch to get a second reference.
        int p2_idx = 2;
        int p2_val = o1[p2_idx];
        for (int i = 3; i <= n; ++i) {
            p2_val &= query(p2_idx, i);
        }
        p[p2_idx] = p2_val;
        used[p[p2_idx]] = true;

        for (int i = 3; i <= n; ++i) {
            if (p[i] == -1) {
                int o2i = query(i, p2_idx);
                
                std::vector<int> current_candidates;
                for (int x = 0; x < n; ++x) {
                    if (!used[x] && (p[1] | x) == o1[i]) {
                        current_candidates.push_back(x);
                    }
                }

                for (int cand_val : current_candidates) {
                    if ((cand_val | p[p2_idx]) == o2i) {
                        p[i] = cand_val;
                        used[cand_val] = true;
                        break;
                    }
                }
            }
        }
    }

    // Output the final permutation.
    std::cout << "! ";
    for (int i = 1; i <= n; ++i) {
        std::cout << p[i] << (i == n ? "" : " ");
    }
    std::cout << std::endl;

    return 0;
}