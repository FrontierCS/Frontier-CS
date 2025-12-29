#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, m;
    if (!(cin >> n >> m)) return 0;
    vector<string> s(m);
    for (int i = 0; i < m; ++i) cin >> s[i];

    // If any pattern is all '?', probability is 1
    for (int i = 0; i < m; ++i) {
        bool allq = true;
        for (int j = 0; j < n; ++j) if (s[i][j] != '?') { allq = false; break; }
        if (allq) {
            cout.setf(std::ios::fixed);
            cout << setprecision(15) << 1.0 << "\n";
            return 0;
        }
    }

    if (m == 0) {
        cout.setf(std::ios::fixed);
        cout << setprecision(15) << 0.0 << "\n";
        return 0;
    }

    // Limitations assumed (problem is designed for small m)
    size_t S = 1ULL << m;
    vector<uint32_t> arr4(S, 0), arr3(S, 0);

    auto idx = [](char c)->int{
        if (c=='A') return 0;
        if (c=='C') return 1;
        if (c=='G') return 2;
        if (c=='T') return 3;
        return -1;
    };

    // Build counts for union-of-all letters (arr4) and aggregated union-of-3 letters (arr3)
    for (int j = 0; j < n; ++j) {
        uint32_t M[4] = {0,0,0,0};
        for (int i = 0; i < m; ++i) {
            int t = idx(s[i][j]);
            if (t >= 0) M[t] |= (1u << i);
        }
        uint32_t U4 = M[0] | M[1] | M[2] | M[3];
        arr4[U4] += 1;
        // Aggregated over the 4 triples (exclude each letter once)
        arr3[U4 & ~M[0]] += 1;
        arr3[U4 & ~M[1]] += 1;
        arr3[U4 & ~M[2]] += 1;
        arr3[U4 & ~M[3]] += 1;
    }

    // Subset Zeta Transform on arr4 and arr3
    for (int i = 0; i < m; ++i) {
        size_t bit = 1ULL << i;
        size_t step = bit << 1;
        for (size_t base = 0; base < S; base += step) {
            for (size_t k = 0; k < bit; ++k) {
                arr4[base + bit + k] += arr4[base + k];
                arr3[base + bit + k] += arr3[base + k];
            }
        }
    }

    // Precompute powers of 1/4: pow4inv[q] = 4^{-q}
    vector<long double> pow4inv(n + 1);
    pow4inv[0] = 1.0L;
    for (int i = 1; i <= n; ++i) pow4inv[i] = pow4inv[i-1] * 0.25L;

    // Inclusion-Exclusion sum
    long double ans = 0.0L;
    uint64_t fullMask = S - 1;
    for (size_t T = 1; T < S; ++T) {
        size_t Y = (~T) & fullMask;
        uint32_t z = arr4[Y];            // positions with no letter from T (i.e., T has none fixed at these)
        uint32_t sum3 = arr3[Y];         // aggregated over all 3-letter unions
        int64_t Nge2 = (int64_t)n + 3LL * z - (int64_t)sum3; // positions with at least 2 different letters among T
        if (Nge2 > 0) continue;          // conflict exists -> intersection empty
        int q = n - (int)z;              // positions where at least one letter from T is present (no conflicts)
        long double w = pow4inv[q];
        int parity = __builtin_popcount((unsigned)T) & 1;
        if (parity) ans += w; else ans -= w;
    }

    if (ans < 0) ans = 0;
    if (ans > 1) ans = 1;
    cout.setf(std::ios::fixed);
    cout << setprecision(15) << (double)ans << "\n";
    return 0;
}