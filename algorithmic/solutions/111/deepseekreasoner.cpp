#include <iostream>
#include <vector>
#include <unordered_set>
#include <cmath>

using namespace std;

// Irreducible polynomials for GF(2^r), for r = 1..12
const int IRRED[] = {
    0,    // dummy
    2,    // r=1: x
    7,    // r=2: x^2 + x + 1
    11,   // r=3: x^3 + x + 1
    19,   // r=4: x^4 + x + 1
    37,   // r=5: x^5 + x^2 + 1
    67,   // r=6: x^6 + x + 1
    131,  // r=7: x^7 + x + 1
    283,  // r=8: x^8 + x^4 + x^3 + x + 1 (AES)
    529,  // r=9: x^9 + x^4 + 1
    1033, // r=10: x^10 + x^3 + 1
    2053, // r=11: x^11 + x^2 + 1
    4105  // r=12: x^12 + x^3 + 1
};

// Multiply two elements in GF(2^r) modulo given irreducible polynomial.
// a and b are in [0, 2^r - 1], result is in the same range.
int multiply(int a, int b, int r, int mod) {
    int res = 0;
    while (b) {
        if (b & 1) res ^= a;
        a <<= 1;
        if (a & (1 << r)) a ^= mod;
        b >>= 1;
    }
    return res;
}

// Construct a Sidon set using the algebraic method: { (x << r) + cube(x) }
// where cube(x) = x^3 in GF(2^r).
// Returns a vector of numbers <= n, of size at least min_m if possible.
vector<int> construct_algebraic(int n, int min_m) {
    for (int r = 1; r <= 12; ++r) {
        int max_x = (1 << r) - 1;
        int mod = IRRED[r];
        // Precompute cube(x) for all x in [0, max_x]
        vector<int> cube(max_x + 1);
        for (int x = 0; x <= max_x; ++x) {
            int sq = multiply(x, x, r, mod);
            cube[x] = multiply(sq, x, r, mod);
        }
        vector<int> S;
        S.reserve(max_x);
        for (int x = 1; x <= max_x; ++x) {
            int a = (x << r) + cube[x];
            if (a <= n) {
                S.push_back(a);
            }
        }
        if ((int)S.size() >= min_m) {
            return S;
        }
    }
    return {}; // fallback (should not happen for moderate n)
}

// Greedy construction: scan numbers from 1 to n, add if it does not create
// a duplicate XOR with already chosen numbers.
vector<int> construct_greedy(int n, int min_m) {
    vector<int> S;
    unordered_set<int> xor_set;
    S.reserve(min_m);
    for (int x = 1; x <= n; ++x) {
        bool ok = true;
        for (int a : S) {
            int xr = x ^ a;
            if (xor_set.find(xr) != xor_set.end()) {
                ok = false;
                break;
            }
        }
        if (ok) {
            for (int a : S) {
                xor_set.insert(x ^ a);
            }
            S.push_back(x);
        }
    }
    return S;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    cin >> n;

    int min_m = (int)sqrt(n / 2.0);
    vector<int> ans;

    if (n <= 20000) {
        ans = construct_greedy(n, min_m);
    } else {
        ans = construct_algebraic(n, min_m);
        if ((int)ans.size() < min_m) {
            ans = construct_greedy(n, min_m);
        }
    }

    cout << ans.size() << '\n';
    if (!ans.empty()) {
        for (size_t i = 0; i < ans.size(); ++i) {
            if (i > 0) cout << ' ';
            cout << ans[i];
        }
        cout << '\n';
    }

    return 0;
}