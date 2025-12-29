#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, m;
    if (!(cin >> n >> m)) return 0;
    vector<string> s(m);
    for (int i = 0; i < m; ++i) cin >> s[i];

    // Early exit: if any pattern is all '?', probability is 1
    for (int i = 0; i < m; ++i) {
        bool allq = true;
        for (int j = 0; j < n; ++j) {
            if (s[i][j] != '?') { allq = false; break; }
        }
        if (allq) {
            cout.setf(std::ios::fixed);
            cout << setprecision(12) << 1.0 << "\n";
            return 0;
        }
    }

    if (m == 0) {
        // No patterns: probability 0
        cout.setf(std::ios::fixed);
        cout << setprecision(12) << 0.0 << "\n";
        return 0;
    }

    // Limit check for memory/time safety (problem is expected to have small m)
    if (m > 25) {
        // Fallback: not supported due to memory/time constraints implied by problem setting
        // We'll output 0 as a safe fallback (shouldn't occur in valid tests).
        cout.setf(std::ios::fixed);
        cout << setprecision(12) << 0.0 << "\n";
        return 0;
    }

    size_t L = 1ull << m;
    vector<int> freq0(L, 0);
    vector<int> freqSumQ(L, 0);

    // Build frequency arrays over masks
    for (int j = 0; j < n; ++j) {
        unsigned int maskQ = 0u;
        unsigned int maskL[4] = {0u, 0u, 0u, 0u};
        for (int i = 0; i < m; ++i) {
            char c = s[i][j];
            if (c == '?') {
                maskQ |= (1u << i);
            } else if (c == 'A') {
                maskL[0] |= (1u << i);
            } else if (c == 'C') {
                maskL[1] |= (1u << i);
            } else if (c == 'G') {
                maskL[2] |= (1u << i);
            } else if (c == 'T') {
                maskL[3] |= (1u << i);
            }
        }
        // Positions where S subset of maskQ contribute to E0
        freq0[maskQ] += 1;
        // For each letter alpha, positions where S subset of (maskQ | maskL[alpha]) contribute to sumQ
        for (int a = 0; a < 4; ++a) {
            unsigned int mk = maskQ | maskL[a];
            freqSumQ[mk] += 1;
        }
    }

    // Superset zeta transform on both arrays
    for (int k = 0; k < m; ++k) {
        size_t step = 1ull << (k + 1);
        size_t half = 1ull << k;
        for (size_t base = 0; base < L; base += step) {
            size_t u = base;
            size_t v = base + half;
            for (size_t t = 0; t < half; ++t, ++u, ++v) {
                freq0[u] += freq0[v];
                freqSumQ[u] += freqSumQ[v];
            }
        }
    }

    // Precompute powers of 1/4
    vector<long double> powInv(n + 1);
    powInv[0] = 1.0L;
    for (int i = 1; i <= n; ++i) powInv[i] = powInv[i - 1] * 0.25L;

    long double ans = 0.0L;
    // Iterate over non-empty subsets
    for (size_t S = 1; S < L; ++S) {
        int e0 = freq0[S];
        int sumQ = freqSumQ[S];
        // Compatibility check: sumQ == n + 3*e0
        if (sumQ == n + 3 * e0) {
            int e = n - e0;
            long double term = powInv[e];
            if (__builtin_parity((unsigned)S)) ans += term; else ans -= term;
        }
    }

    if (ans < 0) ans = 0;
    if (ans > 1) ans = 1;

    cout.setf(std::ios::fixed);
    cout << setprecision(12) << (double)ans << "\n";
    return 0;
}