#include <iostream>
#include <vector>
#include <algorithm>
#include <cmath>

using namespace std;

// Returns the degree of the polynomial (index of MSB)
// Returns -1 for zero polynomial
int deg(int p) {
    if (p == 0) return -1;
    return 31 - __builtin_clz(p);
}

// Polynomial multiplication modulo poly over GF(2)
int poly_mul(int a, int b, int poly) {
    int res = 0;
    int deg_poly = deg(poly);
    // Standard carry-less multiplication
    for (int i = 0; i <= deg(b); ++i) {
        if ((b >> i) & 1) {
            res ^= (a << i);
        }
    }
    // Reduction
    if (deg_poly != -1) {
        for (int i = deg(res); i >= deg_poly; --i) {
            if ((res >> i) & 1) {
                res ^= (poly << (i - deg_poly));
            }
        }
    }
    return res;
}

// Polynomial GCD
int poly_gcd(int a, int b) {
    while (b != 0) {
        int deg_b = deg(b);
        int rem = a;
        while (rem != 0 && deg(rem) >= deg_b) {
            rem ^= (b << (deg(rem) - deg_b));
        }
        a = b;
        b = rem;
    }
    return a;
}

// Check if polynomial is irreducible over GF(2)
bool is_irreducible(int poly) {
    int r = deg(poly);
    if (r < 1) return false;
    // Must have constant term 1
    if ((poly & 1) == 0) return false;
    
    // Check gcd(x^(2^i) + x, poly) == 1 for 1 <= i <= r/2
    // x is represented as 2 (binary 10)
    for (int i = 1; i <= r / 2; ++i) {
        // Calculate x^(2^i) mod poly by repeated squaring
        int xi = 2; // start with x
        for (int k = 0; k < i; ++k) {
            xi = poly_mul(xi, xi, poly);
        }
        // Check gcd(xi + x, poly)
        int term = xi ^ 2;
        if (poly_gcd(poly, term) != 1) return false;
    }
    return true;
}

// Find an irreducible polynomial of degree r
int find_irred(int r) {
    if (r == 1) return 3; // x + 1
    // Iterate odd polynomials starting from 2^r + 1
    for (int p = (1 << r) | 1; p < (1 << (r + 1)); p += 2) {
        if (is_irreducible(p)) return p;
    }
    return 0; // Should not happen
}

// Generate set using algebraic construction for a fixed r
// The set consists of values x*2^r + x^3 mod poly, for x in GF(2^r)
vector<int> generate_alg(int n, int r) {
    vector<int> res;
    int poly = find_irred(r);
    // Elements are of form (x << r) ^ (x^3 mod poly)
    // x ranges from 1 to 2^r - 1
    // Optimization: we can stop if x*2^r > n roughly
    int limit = min((1 << r) - 1, (n >> r) + 2);
    
    for (int x = 1; x <= limit; ++x) {
        if (x >= (1 << r)) break;
        // Compute x^3 mod poly
        int x2 = poly_mul(x, x, poly);
        int x3 = poly_mul(x, x2, poly);
        
        long long val = ((long long)x << r) ^ x3;
        if (val <= n && val >= 1) {
            res.push_back((int)val);
        }
    }
    return res;
}

// Greedy solution for small n
vector<int> solve_greedy(int n) {
    vector<int> S;
    S.reserve((int)sqrt(n) * 2); 
    
    // used array to mark pairwise XOR sums
    // Max sum < 2*n (next power of 2 roughly)
    int limit = 2 * n + 200;
    vector<bool> used(limit, false);
    
    for (int x = 1; x <= n; ++x) {
        bool ok = true;
        for (int y : S) {
            if (used[x ^ y]) {
                ok = false;
                break;
            }
        }
        if (ok) {
            for (int y : S) {
                used[x ^ y] = true;
            }
            S.push_back(x);
        }
    }
    return S;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    if (!(cin >> n)) return 0;

    vector<int> best_sol;
    
    // Algebraic Strategy
    // We try different values of r to find the one that yields the largest set.
    // The construction works for any subset of the field, so we just filter by <= n.
    // We check r up to 22 since 2^22 > 10^7.
    for (int r = 1; r <= 22; ++r) {
        // Heuristic cut-off: if min element > n, break
        // Min element is roughly 2^r.
        if ((1 << r) > n + 100) break; 
        
        vector<int> sol = generate_alg(n, r);
        if (sol.size() > best_sol.size()) {
            best_sol = sol;
        }
    }
    
    // Greedy Strategy for small n
    // Greedy often performs better than algebraic bounds for small inputs
    if (n <= 5000) {
        vector<int> g_sol = solve_greedy(n);
        if (g_sol.size() > best_sol.size()) {
            best_sol = g_sol;
        }
    }
    
    cout << best_sol.size() << "\n";
    for (size_t i = 0; i < best_sol.size(); ++i) {
        cout << best_sol[i] << (i == best_sol.size() - 1 ? "" : " ");
    }
    cout << "\n";
    
    return 0;
}