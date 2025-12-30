#include <iostream>
#include <vector>
#include <string>
#include <numeric>
#include <algorithm>
#include <map>

using namespace std;

long long power(long long base, long long exp) {
    long long res = 1;
    base %= 1000000007;
    while (exp > 0) {
        if (exp % 2 == 1) res = (res * base) % 1000000007;
        base = (base * base) % 1000000007;
        exp /= 2;
    }
    return res;
}

long long modInverse(long long n) {
    return power(n, 1000000007 - 2);
}

long long ask_query(const vector<long long>& a) {
    cout << "?";
    for (long long x : a) {
        cout << " " << x;
    }
    cout << endl;
    long long response;
    cin >> response;
    return response;
}

const int MOD = 1e9 + 7;

void solve_subset_product(long long target, int k, const vector<int>& p_map, vector<vector<bool>>& candidates) {
    if (k == 0) {
        if (target == 1) {
            candidates.push_back({});
        }
        return;
    }
    int k1 = k / 2;
    map<long long, vector<int>> products1;
    for (int i = 0; i < (1 << k1); ++i) {
        long long p = 1;
        for (int j = 0; j < k1; ++j) {
            if ((i >> j) & 1) {
                p = (p * (p_map[j])) % MOD;
            }
        }
        products1[p].push_back(i);
    }

    int k2 = k - k1;
    for (int i = 0; i < (1 << k2); ++i) {
        long long p2 = 1;
        for (int j = 0; j < k2; ++j) {
            if ((i >> j) & 1) {
                p2 = (p2 * (p_map[k1 + j])) % MOD;
            }
        }
        long long required = (target * modInverse(p2)) % MOD;
        
        if (products1.count(required)) {
            for (int mask1 : products1[required]) {
                int mask2 = i;
                vector<bool> current_ops(k, false); // false for +, true for x
                for (int j = 0; j < k1; ++j) {
                    if ((mask1 >> j) & 1) {
                        current_ops[j] = true;
                    }
                }
                for (int j = 0; j < k2; ++j) {
                    if ((mask2 >> j) & 1) {
                        current_ops[k1 + j] = true;
                    }
                }
                candidates.push_back(current_ops);
            }
        }
    }
}


int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    cin >> n;

    vector<int> final_ops(n + 1, 0);
    const int BLOCK_SIZE = 38;
    int num_blocks = (n + BLOCK_SIZE - 1) / BLOCK_SIZE;

    vector<long long> prefix_a(n + 1, 1);
    long long current_A = 1, current_B = 0;

    for (int b = 0; b < num_blocks; ++b) {
        int start_idx = b * BLOCK_SIZE + 1;
        int end_idx = min((b + 1) * BLOCK_SIZE, n);
        int k = end_idx - start_idx + 1;

        vector<long long> a_q1(n + 1);
        vector<long long> a_q2(n + 1);
        vector<int> p_map;

        for (int i = 1; i <= n; ++i) {
            if (i < start_idx) {
                a_q1[i] = prefix_a[i];
                a_q2[i] = prefix_a[i];
            } else if (i >= start_idx && i <= end_idx) {
                a_q1[i] = i - start_idx + 2;
                a_q2[i] = i - start_idx + 2;
                p_map.push_back(i - start_idx + 2);
            } else {
                a_q1[i] = 1;
                a_q2[i] = 1;
            }
        }

        long long R_prefix_val1 = 2, R_prefix_val2 = 3;
        
        long long a0_1, a0_2;

        if (b == 0) {
            a0_1 = R_prefix_val1;
            a0_2 = R_prefix_val2;
        } else {
            long long inv_A = modInverse(current_A);
            a0_1 = ((R_prefix_val1 - current_B + MOD) % MOD * inv_A) % MOD;
            a0_2 = ((R_prefix_val2 - current_B + MOD) % MOD * inv_A) % MOD;
        }

        if (a0_1 == 0) a0_1 = MOD;
        if (a0_2 == 0) a0_2 = MOD;

        a_q1[0] = a0_1;
        a_q2[0] = a0_2;

        long long v1 = ask_query(a_q1);
        long long v2 = ask_query(a_q2);
        
        long long A_block = (v2 - v1 + MOD) % MOD * modInverse((R_prefix_val2 - R_prefix_val1 + MOD) % MOD) % MOD;

        vector<vector<bool>> candidates;
        solve_subset_product(A_block, k, p_map, candidates);

        vector<bool> block_ops;

        long long known_val = (v1 - (A_block * R_prefix_val1) % MOD + MOD) % MOD;
        long long max_C = n - end_idx;
        
        for (const auto& cand : candidates) {
            long long B_block = 0;
            for (int i = 0; i < k; ++i) {
                long long val = i + 2;
                if (cand[i]) { // multiply
                    B_block = (B_block * val) % MOD;
                } else { // add
                    B_block = (B_block + val) % MOD;
                }
            }
            long long C_cand = (known_val - B_block + MOD) % MOD;
            if (C_cand >= 0 && C_cand <= max_C) {
                block_ops = cand;
                break;
            }
        }
        
        for (int i = 0; i < k; ++i) {
            final_ops[start_idx + i] = block_ops[i] ? 1 : 0;
        }
        
        if (b < num_blocks - 1) {
            for(int i = start_idx; i <= end_idx; ++i) {
                prefix_a[i] = i - start_idx + 2;
            }

            long long next_A = 1;
            long long next_B = 0;
            for(int i=0; i<k; ++i){
                if(block_ops[i]){
                    next_A = (next_A * p_map[i]) % MOD;
                    next_B = (next_B * p_map[i]) % MOD;
                } else {
                    next_B = (next_B + p_map[i]) % MOD;
                }
            }
            
            long long old_A = current_A;
            long long old_B = current_B;
            
            current_A = (next_A * old_A) % MOD;
            current_B = (next_A * old_B + next_B) % MOD;
        }
    }

    cout << "!";
    for (int i = 1; i <= n; ++i) {
        cout << " " << final_ops[i];
    }
    cout << endl;

    return 0;
}