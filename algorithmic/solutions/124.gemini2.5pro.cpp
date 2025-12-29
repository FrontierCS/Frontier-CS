#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <cmath>

int n;
std::vector<int> p_final;

bool ask(const std::vector<int>& indices) {
    if (indices.empty()) return true;
    std::cout << "? " << indices.size();
    for (int index : indices) {
        std::cout << " " << index;
    }
    std::cout << std::endl;
    int result;
    std::cin >> result;
    if (result == -1) exit(0);
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

    p_final.resize(n + 1);
    std::vector<int> par(n + 1, 0);
    std::vector<int> s0, s1;

    s0.push_back(1);
    par[1] = 0;
    for (int i = 2; i <= n; ++i) {
        if (ask({1, i})) {
            par[i] = 0;
            s0.push_back(i);
        } else {
            par[i] = 1;
            s1.push_back(i);
        }
    }

    int pos1 = -1, pos2 = -1;

    for (int i : s0) {
        for (int j : s1) {
            int rem_count = 0;
            for(int l=1; l<=n; ++l) {
                if(l!=1 && l!=2) {
                    if (l % 3 == 0) rem_count++;
                }
            }

            int query_rem_count = 0;
            int test_count = 0;
            std::vector<int> test_indices;
            for (int l = 1; l <= n; ++l) {
                if (l != i && l != j) {
                    test_indices.push_back(l);
                }
            }
            std::random_shuffle(test_indices.begin(), test_indices.end());
            int num_to_test = std::min((int)test_indices.size(), 20);

            for (int k=0; k<num_to_test; ++k) {
                if (ask({i, j, test_indices[k]})) {
                    query_rem_count++;
                }
            }
            
            double expected_ratio = (double)rem_count / (n-2);
            double actual_ratio = (double)query_rem_count / num_to_test;
            
            if (std::abs(expected_ratio - actual_ratio) < 0.2) {
                 pos1 = i; pos2 = j;
                 goto found_pos12;
            }
        }
    }

found_pos12:
    if (pos1 == -1) { // Fallback if random check fails
        pos1 = s0[0];
        pos2 = s1[0];
    }
    p_final[pos1] = 1;
    p_final[pos2] = 2;
    
    std::vector<bool> used(n + 1, false);
    used[1] = true;
    used[2] = true;

    for (int i = 1; i <= n; ++i) {
        if (i == pos1 || i == pos2) continue;

        bool is_mult_of_3 = ask({pos1, pos2, i});
        bool i_should_be_odd = (par[i] == par[pos1]);

        for (int v = 1; v <= n; ++v) {
            if (used[v]) continue;

            bool v_is_odd = v % 2 != 0;
            if (v_is_odd != i_should_be_odd) continue;

            if ((v % 3 == 0) == is_mult_of_3) {
                p_final[i] = v;
                used[v] = true;
                break;
            }
        }
    }

    if (p_final[1] > n / 2) {
        for (int i = 1; i <= n; ++i) {
            p_final[i] = n + 1 - p_final[i];
        }
    }

    answer(p_final);

    return 0;
}