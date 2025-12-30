#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>

using namespace std;

// Function to calculate degree of a polynomial (position of MSB)
int get_deg(int p) {
    if (p == 0) return -1;
    return 31 - __builtin_clz(p);
}

// Modulo reduction over GF(2)
int mod_poly(long long val, int poly) {
    int d_val = 63 - __builtin_clzll(val);
    int d_poly = 31 - __builtin_clz(poly);
    while (d_val >= d_poly && val > 0) {
        val ^= ((long long)poly << (d_val - d_poly));
        if (val == 0) return 0;
        d_val = 63 - __builtin_clzll(val);
    }
    return (int)val;
}

// Multiplication over GF(2^m) modulo poly
int mul_poly(int a, int b, int poly) {
    long long res = 0;
    for (int i = 0; i < 32; i++) {
        if ((b >> i) & 1) {
            res ^= ((long long)a << i);
        }
    }
    return mod_poly(res, poly);
}

// Check if polynomial p is irreducible
bool is_irreducible(int p) {
    int d = get_deg(p);
    // Check divisibility by all polynomials of degree 1 to d/2
    // Iterating up to 1<<(d/2+1) is sufficient
    int limit = (1 << (d / 2 + 1));
    for (int i = 2; i < limit; i++) {
        if (mod_poly(p, i) == 0) return false;
    }
    return true;
}

// Find first irreducible polynomial of degree d
int find_irreducible(int d) {
    // Start search from 1<<d | 1 (monic, constant term 1)
    for (int p = (1 << d) | 1; ; p += 2) {
        if (is_irreducible(p)) return p;
    }
}

// Greedy strategy
vector<int> solve_greedy(int n) {
    vector<int> S;
    // We need to maintain forbidden values.
    // A value x is forbidden if x = a ^ b ^ c for distinct a, b, c in S.
    // Max XOR sum can be up to ~2*n (next power of 2)
    int limit = 1;
    while (limit <= n) limit <<= 1;
    limit <<= 2; 
    
    // bitset or vector<bool>
    vector<bool> forbidden(limit, false);
    
    for (int x = 1; x <= n; ++x) {
        if (!forbidden[x]) {
            // Add x
            // Update forbidden with new triplets {x, s1, s2}
            int sz = S.size();
            for (int i = 0; i < sz; ++i) {
                for (int j = 0; j < i; ++j) {
                    int val = x ^ S[i] ^ S[j];
                    if (val < limit) forbidden[val] = true;
                }
            }
            S.push_back(x);
        }
    }
    return S;
}

// Algebraic strategy
vector<int> solve_algebraic(int n) {
    // Determine m such that size ~ N / 2^m >= sqrt(N/2)
    // Heuristic: 2m approx logN
    int logn = 0;
    int temp = n;
    while (temp >>= 1) logn++;
    int m = (logn + 1) / 2;
    if (m < 1) m = 1;

    int poly = find_irreducible(m);
    vector<int> S;
    
    // Iterate x such that (x << m) ^ x^3 <= n
    // Roughly x up to n >> m
    int limit_x = (n >> m) + 5; 
    
    for (int x = 1; x <= limit_x; ++x) {
        // x^3 in GF(2^m)
        int x2 = mul_poly(x, x, poly);
        int x3 = mul_poly(x2, x, poly);
        
        long long val = ((long long)x << m) ^ x3;
        if (val <= n && val > 0) {
            S.push_back((int)val);
        }
    }
    return S;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    int n;
    if (!(cin >> n)) return 0;
    
    // For small N, greedy is fast and effective.
    // For large N, algebraic is necessary for performance.
    // Threshold 5000 is safe for greedy (M^3 complexity).
    if (n <= 5000) {
        vector<int> sg = solve_greedy(n);
        vector<int> sa = solve_algebraic(n);
        
        if (sg.size() >= sa.size()) {
            cout << sg.size() << "\n";
            for (int i = 0; i < sg.size(); ++i) cout << sg[i] << (i==sg.size()-1?"":" ");
        } else {
            cout << sa.size() << "\n";
            for (int i = 0; i < sa.size(); ++i) cout << sa[i] << (i==sa.size()-1?"":" ");
        }
        cout << "\n";
    } else {
        vector<int> sa = solve_algebraic(n);
        cout << sa.size() << "\n";
        for (int i = 0; i < sa.size(); ++i) cout << sa[i] << (i==sa.size()-1?"":" ");
        cout << "\n";
    }
    
    return 0;
}