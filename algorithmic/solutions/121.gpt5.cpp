#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n, m;
    if (!(cin >> n >> m)) return 0;

    // Assume m <= 60 (we use 64-bit masks) and practically <= ~25 for feasibility.
    vector<uint64_t> L[4];
    for (int k = 0; k < 4; ++k) L[k].assign(n, 0);

    for (int i = 0; i < m; ++i) {
        string s;
        cin >> s;
        for (int j = 0; j < n; ++j) {
            char c = s[j];
            if (c == 'A') L[0][j] |= (1ULL << i);
            else if (c == 'C') L[1][j] |= (1ULL << i);
            else if (c == 'G') L[2][j] |= (1ULL << i);
            else if (c == 'T') L[3][j] |= (1ULL << i);
        }
    }

    // Build conflict graph adjacency
    vector<uint64_t> adj(m, 0);
    for (int j = 0; j < n; ++j) {
        uint64_t a = L[0][j], c = L[1][j], g = L[2][j], t = L[3][j];
        if (a) {
            uint64_t others = c | g | t;
            uint64_t x = a;
            while (x) {
                uint64_t b = x & -x;
                int v = __builtin_ctzll(b);
                adj[v] |= others;
                x ^= b;
            }
        }
        if (c) {
            uint64_t others = a | g | t;
            uint64_t x = c;
            while (x) {
                uint64_t b = x & -x;
                int v = __builtin_ctzll(b);
                adj[v] |= others;
                x ^= b;
            }
        }
        if (g) {
            uint64_t others = a | c | t;
            uint64_t x = g;
            while (x) {
                uint64_t b = x & -x;
                int v = __builtin_ctzll(b);
                adj[v] |= others;
                x ^= b;
            }
        }
        if (t) {
            uint64_t others = a | c | g;
            uint64_t x = t;
            while (x) {
                uint64_t b = x & -x;
                int v = __builtin_ctzll(b);
                adj[v] |= others;
                x ^= b;
            }
        }
    }

    // Count positions by U = union of letters at position
    if (m >= 63) {
        // Not expected per problem intended constraints; fallback to 0.
        cout.setf(std::ios::fixed); cout<<setprecision(15)<<0.0<<"\n";
        return 0;
    }
    size_t N = 1ULL << m;
    vector<uint32_t> G(N, 0); // counts g[V]
    for (int j = 0; j < n; ++j) {
        uint64_t U = L[0][j] | L[1][j] | L[2][j] | L[3][j];
        G[(size_t)U] += 1;
    }

    // Zeta transform over subsets: H[T] = sum_{V subset T} g[V], in-place on G
    for (int b = 0; b < m; ++b) {
        size_t step = 1ULL << b;
        for (size_t mask = 0; mask < N; mask += (step << 1)) {
            uint32_t* base = G.data() + mask;
            for (size_t i = 0; i < step; ++i) {
                base[step + i] += base[i];
            }
        }
    }

    // Precompute powers of 1/4
    vector<long double> pw(n + 1);
    pw[0] = 1.0L;
    for (int i = 1; i <= n; ++i) pw[i] = pw[i - 1] * 0.25L;

    // DP over masks for independent sets and inclusion-exclusion sum
    vector<uint8_t> indep(N, 0);
    indep[0] = 1;
    long double ans = 0.0L;
    uint64_t full = N - 1;
    for (size_t mask = 1; mask < N; ++mask) {
        uint64_t lsb = mask & -mask;
        int v = __builtin_ctzll(lsb);
        uint64_t rest = mask ^ lsb;
        indep[mask] = indep[rest] && ((adj[v] & rest) == 0);
        if (indep[mask]) {
            int F = n - (int)G[(~mask) & full];
            long double term = pw[F];
            if ((__builtin_popcountll(mask) & 1) == 1) ans += term;
            else ans -= term;
        }
    }

    // Output
    if (ans < 0) ans = 0; // numerical safety
    if (ans > 1) ans = 1;
    cout.setf(std::ios::fixed);
    cout << setprecision(15) << (double)ans << "\n";
    return 0;
}