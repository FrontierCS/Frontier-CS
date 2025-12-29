#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>

using namespace std;

// Calculate degree of polynomial (represented by bits)
int deg(int p) {
    if (p == 0) return -1;
    return 31 - __builtin_clz(p);
}

// Polynomial modulo over GF(2)
int poly_mod(int a, int b) {
    int da = deg(a);
    int db = deg(b);
    while (da >= db) {
        a ^= (b << (da - db));
        da = deg(a);
    }
    return a;
}

// Polynomial multiplication modulo poly over GF(2)
int poly_mul(int a, int b, int poly) {
    int raw_prod = 0;
    for (int i = 0; i <= deg(a); ++i) {
        if ((a >> i) & 1) {
            raw_prod ^= (b << i);
        }
    }
    return poly_mod(raw_prod, poly);
}

// Find irreducible polynomial of degree k
int find_irreducible(int k) {
    // Try odd numbers starting from 2^k + 1
    for (int p = (1 << k) | 1; p < (1 << (k + 1)); p += 2) {
        bool ok = true;
        // Check divisibility by polynomials of degree 1 to k/2
        // We iterate integers d from 2 up to 2^(k/2 + 1)
        int limit = 1 << (k / 2 + 1);
        for (int d = 2; d < limit; ++d) {
             if (poly_mod(p, d) == 0) {
                 ok = false;
                 break;
             }
        }
        if (ok) return p;
    }
    return 0;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    if (!(cin >> n)) return 0;

    // Requirement: m >= floor(sqrt(n/2))
    int target = floor(sqrt(n / 2.0));
    
    vector<int> best_S;
    
    // Try different field sizes K to find the best Sidon set construction
    // Typically K around log2(sqrt(n)) is optimal.
    // We try a range of K. Given n <= 10^7, max K is around 12 or 13.
    for (int k = 1; k <= 13; ++k) {
        // Optimization: if the smallest element (approx 2^k) is > n, stop
        if ((1 << k) > n) break;
        
        int poly = find_irreducible(k);
        vector<int> current_S;
        
        // Generate elements using Bose-Chowla type construction adapted for GF(2^k)
        // Element form: x * 2^k + x^3 in GF(2^k)
        int limit_x = (1 << k);
        for (int x = 1; x < limit_x; ++x) {
            int x2 = poly_mul(x, x, poly);
            int x3 = poly_mul(x2, x, poly);
            
            // Construct value: high bits x, low bits x^3
            long long val = ((long long)x << k) ^ x3;
            
            if (val <= n) {
                current_S.push_back((int)val);
            }
        }
        
        if (current_S.size() > best_S.size()) {
            best_S = current_S;
        }
    }
    
    // If constructed set is smaller than required, fill greedily
    if ((int)best_S.size() < target) {
        int max_xor_limit = 2 * n + 2000; // Safe upper bound for XOR sums
        vector<bool> used(max_xor_limit, false);
        
        // Mark XOR sums from current set
        int m = best_S.size();
        for (int i = 0; i < m; ++i) {
            for (int j = i + 1; j < m; ++j) {
                used[best_S[i] ^ best_S[j]] = true;
            }
        }
        
        // Mark elements currently in set to avoid duplicates
        vector<bool> present(n + 1, false);
        for (int x : best_S) present[x] = true;
        
        int current_val = 1;
        while ((int)best_S.size() < target && current_val <= n) {
            if (!present[current_val]) {
                bool possible = true;
                // Check conflicts with existing elements
                for (int s : best_S) {
                    int x = current_val ^ s;
                    if (x >= max_xor_limit || used[x]) {
                        possible = false;
                        break;
                    }
                }
                
                if (possible) {
                    // Add element and update used XORs
                    for (int s : best_S) {
                        used[current_val ^ s] = true;
                    }
                    best_S.push_back(current_val);
                    present[current_val] = true;
                }
            }
            current_val++;
        }
    }
    
    cout << best_S.size() << "\n";
    for (int i = 0; i < (int)best_S.size(); ++i) {
        cout << best_S[i] << (i == (int)best_S.size() - 1 ? "" : " ");
    }
    cout << "\n";

    return 0;
}