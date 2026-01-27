#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, m;
    if (!(cin >> n >> m)) return 0;
    vector<string> s(m);
    for (int i = 0; i < m; ++i) cin >> s[i];

    int M = 1 << m;
    vector<uint32_t> cnt(M, 0);

    vector<uint32_t> confmask(m, 0);

    for (int j = 0; j < n; ++j) {
        uint32_t B = 0;
        uint32_t maskA = 0, maskC = 0, maskG = 0, maskT = 0;
        for (int i = 0; i < m; ++i) {
            char c = s[i][j];
            if (c == '?') {
                B |= (1u << i);
            } else if (c == 'A') {
                maskA |= (1u << i);
            } else if (c == 'C') {
                maskC |= (1u << i);
            } else if (c == 'G') {
                maskG |= (1u << i);
            } else if (c == 'T') {
                maskT |= (1u << i);
            }
        }
        cnt[B]++;

        uint32_t allFixed = maskA | maskC | maskG | maskT;
        // For each letter group, patterns in that group conflict with all others in allFixed not in their group
        auto apply_conflicts = [&](uint32_t groupMask) {
            if (!groupMask) return;
            uint32_t conflict_set = allFixed ^ groupMask;
            uint32_t x = groupMask;
            while (x) {
                uint32_t lsb = x & -x;
                int idx = __builtin_ctz(x);
                confmask[idx] |= conflict_set;
                x ^= lsb;
            }
        };
        apply_conflicts(maskA);
        apply_conflicts(maskC);
        apply_conflicts(maskG);
        apply_conflicts(maskT);
    }

    // ok[S] whether subset S is pairwise compatible (no conflicts)
    vector<char> ok(M, 0);
    ok[0] = 1;
    for (int mask = 1; mask < M; ++mask) {
        int i = __builtin_ctz(mask);
        int prev = mask & (mask - 1);
        ok[mask] = ok[prev] && ((confmask[i] & (uint32_t)prev) == 0);
    }

    // Superset zeta transform: F[S] = sum_{T superset S} cnt[T]
    vector<uint32_t> F = cnt;
    for (int b = 0; b < m; ++b) {
        for (int mask = 0; mask < M; ++mask) {
            if ((mask & (1 << b)) == 0) {
                F[mask] += F[mask | (1 << b)];
            }
        }
    }

    long double ans = 0.0L;
    for (int mask = 1; mask < M; ++mask) {
        if (!ok[mask]) continue;
        int pop = __builtin_popcount((unsigned)mask);
        long long freePos = F[mask];
        long long fixedPos = (long long)n - freePos;
        long double term = powl(0.25L, (long double)fixedPos);
        if (pop & 1) ans += term;
        else ans -= term;
    }

    // Clamp to [0,1] due to numeric errors
    if (ans < 0) ans = 0;
    if (ans > 1) ans = 1;

    cout.setf(std::ios::fixed); 
    cout << setprecision(15) << (double)ans << "\n";
    return 0;
}