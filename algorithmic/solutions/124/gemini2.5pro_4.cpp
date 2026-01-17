#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <map>

int n;

bool ask(const std::vector<int>& indices) {
    if (indices.empty()) return true;
    std::cout << "? " << indices.size();
    for (int idx : indices) {
        std::cout << " " << idx;
    }
    std::cout << std::endl;
    int response;
    std::cin >> response;
    return response == 1;
}

void answer(const std::vector<int>& p) {
    std::cout << "!";
    for (int i = 0; i < n; ++i) {
        std::cout << " " << p[i];
    }
    std::cout << std::endl;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    std::cin >> n;

    std::vector<int> group_A, group_B;
    group_A.push_back(1);

    for (int i = 2; i <= n; ++i) {
        if (ask({1, i})) {
            group_A.push_back(i);
        } else {
            group_B.push_back(i);
        }
    }

    int pos1 = -1, posn = -1;
    if (n > 2) {
        std::vector<int> all_indices(n);
        std::iota(all_indices.begin(), all_indices.end(), 1);

        for (int i = 1; i <= n; ++i) {
            std::vector<int> query_indices;
            for (int j = 1; j <= n; ++j) {
                if (i == j) continue;
                query_indices.push_back(j);
            }
            if (ask(query_indices)) {
                if (pos1 == -1) {
                    pos1 = i;
                } else {
                    posn = i;
                }
            }
        }
    } else { // n=2 case
        pos1 = 1;
        posn = 2;
    }


    auto solve_case = [&](bool A_is_odd_hypo) {
        std::vector<int> p_sol(n + 1, 0);
        int u = pos1, v = posn;
        
        bool u_in_A = false;
        for(int x: group_A) if(x==u) u_in_A = true;
        
        if (A_is_odd_hypo) {
            p_sol[u] = u_in_A ? 1 : n;
            p_sol[v] = u_in_A ? n : 1;
        } else {
            p_sol[u] = u_in_A ? n : 1;
            p_sol[v] = u_in_A ? 1 : n;
        }

        std::vector<int> unpaired_A, unpaired_B;
        for(int i : group_A) if(i != u && i != v) unpaired_A.push_back(i);
        for(int i : group_B) if(i != u && i != v) unpaired_B.push_back(i);

        for(int i : unpaired_A) {
            int comp_j = -1;
            for(int j : unpaired_B) {
                if(p_sol[j] != 0) continue;
                 // p[i]+p[j]+p[u]+p[v] = p[i]+p[j]+n+1. If i,j are complements, sum is 2(n+1), not divisible by 4.
                if (!ask({i, j, u, v})) {
                    comp_j = j;
                    break;
                }
            }
            if (comp_j != -1) {
                int val_mod_3 = -1;
                if (ask({i, u, v})) { // (p[i] + n + 1) % 3 == 0
                    val_mod_3 = (-(n + 1)) % 3;
                    if(val_mod_3 < 0) val_mod_3 += 3;
                }
                
                std::vector<int> p_A_vals;
                if(A_is_odd_hypo) for(int k=1; k<=n; k+=2) p_A_vals.push_back(k);
                else for(int k=2; k<=n; k+=2) p_A_vals.push_back(k);

                for(int val : p_A_vals) {
                    if (val == p_sol[u] || val == p_sol[v]) continue;
                    bool used = false;
                    for(int k=1; k<=n; ++k) if(p_sol[k] == val) used = true;
                    if(used) continue;

                    if(val_mod_3 != -1) {
                        if (val % 3 == val_mod_3) {
                             p_sol[i] = val;
                             p_sol[comp_j] = n + 1 - val;
                             break;
                        }
                    } else { // val_mod_3 is not known for sure
                        if ((val + n + 1) % 3 != 0) {
                            p_sol[i] = val;
                            p_sol[comp_j] = n + 1 - val;
                            break;
                        }
                    }
                }
            }
        }
        return p_sol;
    };

    bool is_1_in_A = false;
    for(int x : group_A) if(x==1) is_1_in_A = true;
    
    std::vector<int> p_final;

    if ( (is_1_in_A && pos1 == 1) || (is_1_in_A && posn != 1)) {
        p_final = solve_case(true);
    } else {
        p_final = solve_case(false);
    }
    
    if (p_final[1] > n/2) {
       for(int i=1; i<=n; ++i) p_final[i] = n + 1 - p_final[i];
    }
    
    std::vector<int> p_vec(n);
    for(int i=1; i<=n; ++i) p_vec[i-1] = p_final[i];
    answer(p_vec);

    return 0;
}