#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <cmath>
#include <set>
#include <map>

// Using base B with M digits to represent positions 0-999
// We need B^M >= 1000
// Total robots: M*B + M*(M-1)/2
// B=4, M=5: 4*5 + 10 = 30
// B=6, M=4: 6*4 + 6 = 30
// We choose B=6, M=4 as it might be slightly faster to generate queries.
const int B = 6;
const int M = 4;
const int N_POS = 1000;

std::vector<int> to_base_B(int n) {
    std::vector<int> digits(M);
    if (n < 0) return digits;
    for (int i = 0; i < M; ++i) {
        digits[i] = n % B;
        n /= B;
    }
    return digits;
}

void solve() {
    std::vector<std::vector<int>> queries;
    std::map<int, std::pair<int, int>> type1_map; // query_idx -> {digit_idx, val}
    std::map<int, std::pair<int, int>> type2_map; // query_idx -> {digit_idx1, digit_idx2}

    int query_idx_counter = 0;

    // Part 1 queries: digit values
    for (int i = 0; i < M; ++i) {
        for (int v = 0; v < B; ++v) {
            std::vector<int> p_list;
            for (int p = 1; p <= N_POS; ++p) {
                if (to_base_B(p - 1)[i] == v) {
                    p_list.push_back(p);
                }
            }
            queries.push_back(p_list);
            type1_map[query_idx_counter++] = {i, v};
        }
    }

    // Part 2 queries: digit pairs
    for (int i = 0; i < M; ++i) {
        for (int j = i + 1; j < M; ++j) {
            std::vector<int> p_list;
            for (int p = 1; p <= N_POS; ++p) {
                auto digits = to_base_B(p - 1);
                if (digits[i] == digits[j]) {
                    p_list.push_back(p);
                }
            }
            queries.push_back(p_list);
            type2_map[query_idx_counter++] = {i, j};
        }
    }

    for (const auto& q : queries) {
        std::cout << "? " << q.size();
        for (int p : q) {
            std::cout << " " << p;
        }
        std::cout << std::endl;
    }

    std::cout << "@" << std::endl;

    int L;
    std::cin >> L;
    std::vector<int> results(L);
    for (int i = 0; i < L; ++i) {
        std::cin >> results[i];
    }

    std::vector<std::vector<int>> D(M);
    std::set<int> U;

    for (int k = 0; k < M * B; ++k) {
        if (results[k] == 1) {
            auto const& [digit_idx, val] = type1_map[k];
            D[digit_idx].push_back(val);
        }
    }

    for (int i = 0; i < M; ++i) {
        if (D[i].size() == 2) {
            U.insert(i);
        }
    }

    long long c1_val = 0, c2_val = 0;
    
    std::vector<int> c1_digits(M), c2_digits(M);

    for (int i = 0; i < M; ++i) {
        if (U.find(i) == U.end()) {
            int digit = D[i][0];
            c1_digits[i] = digit;
            c2_digits[i] = digit;
        }
    }

    if (!U.empty()) {
        int ref_d = *U.begin();
        c1_digits[ref_d] = D[ref_d][0];
        c2_digits[ref_d] = D[ref_d][1];

        for (int i : U) {
            if (i == ref_d) continue;

            int pair_res = -1;
            int u = std::min(i, ref_d);
            int v = std::max(i, ref_d);
            for(auto const& [q_idx, p] : type2_map){
                if(p.first == u && p.second == v){
                    pair_res = results[q_idx];
                    break;
                }
            }
            
            int a = D[i][0], b = D[i][1];
            bool test1_true = (c1_digits[ref_d] == a || c2_digits[ref_d] == b);
            
            if (pair_res == 1) {
                if (test1_true) {
                    c1_digits[i] = a; c2_digits[i] = b;
                } else {
                    c1_digits[i] = b; c2_digits[i] = a;
                }
            } else { // pair_res == 0
                if (!test1_true) {
                    c1_digits[i] = a; c2_digits[i] = b;
                } else {
                    c1_digits[i] = b; c2_digits[i] = a;
                }
            }
        }
    }
    
    long long p_b = 1;
    for(int i = 0; i < M; ++i){
        c1_val += (long long)c1_digits[i] * p_b;
        c2_val += (long long)c2_digits[i] * p_b;
        p_b *= B;
    }

    if (c1_val > c2_val) std::swap(c1_val, c2_val);
    std::cout << "! " << c1_val + 1 << " " << c2_val + 1 << std::endl;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    int R, H;
    std::cin >> R >> H;
    solve();
    return 0;
}