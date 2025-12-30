#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>

using namespace std;

// Irreducible polynomials for GF(2^k) for k = 1 to 15
const int polys[] = {
    0, 
    3,      // 1: x + 1
    7,      // 2: x^2 + x + 1
    11,     // 3: x^3 + x + 1
    19,     // 4: x^4 + x + 1
    37,     // 5: x^5 + x^2 + 1
    67,     // 6: x^6 + x + 1
    131,    // 7: x^7 + x + 1
    283,    // 8: x^8 + x^4 + x^3 + x + 1
    515,    // 9: x^9 + x + 1
    1033,   // 10: x^10 + x^3 + 1
    2053,   // 11: x^11 + x^2 + 1
    4105,   // 12: x^12 + x^3 + 1
    8219,   // 13: x^13 + x^4 + x^3 + x + 1
    16427,  // 14: x^14 + x^5 + x^3 + x + 1
    32771   // 15: x^15 + x + 1
};

// Multiplication in GF(2^k) modulo p
int gf_mul(int a, int b, int k, int p) {
    int res = 0;
    for (int i = 0; i < k; ++i) {
        if ((b >> i) & 1) {
            res ^= a;
        }
        bool carry = (a >> (k - 1)) & 1;
        a <<= 1;
        if (carry) {
            a ^= p;
        }
        a &= ((1 << k) - 1);
    }
    return res;
}

// Compute a^3 in GF(2^k)
int gf_pow3(int a, int k, int p) {
    int a2 = gf_mul(a, a, k, p);
    return gf_mul(a2, a, k, p);
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    int n;
    if (!(cin >> n)) return 0;

    vector<int> best_S;

    // Algebraic construction: S = { x*2^k + x^3 } for x in GF(2^k)
    // This forms a Sidon set in the vector space, implying distinct pairwise XORs.
    // We iterate k to find the best fit for n.
    for (int k = 1; k <= 15; ++k) {
        // Optimization: if the smallest element for this k is significantly larger than n, stop.
        if ((1 << k) > n + 100 && k > 5) break;

        vector<int> current_S;
        int p = polys[k];
        
        int limit = 1 << k;
        // x contributes to the high bits, so x cannot exceed n >> k roughly.
        int max_x = (n >> k) + 2; 
        if (max_x > limit) max_x = limit;

        for (int x = 1; x < max_x; ++x) {
            int x3 = gf_pow3(x, k, p);
            long long val = ((long long)x << k) ^ x3;
            if (val >= 1 && val <= n) {
                current_S.push_back((int)val);
            }
        }

        if (current_S.size() > best_S.size()) {
            best_S = current_S;
        }
    }
    
    // For small n, the algebraic construction might be suboptimal due to overhead.
    // We use a simple greedy approach for small n.
    if (n < 500) {
        vector<int> greedy_S;
        greedy_S.push_back(1);
        vector<bool> used_xor(2048, false); // Sufficient size for XORs with n < 500
        
        for (int x = 2; x <= n; ++x) {
            bool ok = true;
            for (int s : greedy_S) {
                int val = x ^ s;
                if (val < 2048 && used_xor[val]) {
                    ok = false;
                    break;
                }
            }
            if (ok) {
                for (int s : greedy_S) {
                    int val = x ^ s;
                    if (val < 2048) used_xor[val] = true;
                }
                greedy_S.push_back(x);
            }
        }
        if (greedy_S.size() > best_S.size()) {
            best_S = greedy_S;
        }
    }

    cout << best_S.size() << "\n";
    for (size_t i = 0; i < best_S.size(); ++i) {
        cout << best_S[i] << (i == best_S.size() - 1 ? "" : " ");
    }
    cout << "\n";

    return 0;
}