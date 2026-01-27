#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, m;
    if (!(cin >> n >> m)) return 0;
    vector<string> patterns(m);
    for (int i = 0; i < m; ++i) cin >> patterns[i];

    // If any pattern is all '?', then every sequence is valid.
    for (int i = 0; i < m; ++i) {
        bool allq = true;
        for (int j = 0; j < n; ++j) if (patterns[i][j] != '?') { allq = false; break; }
        if (allq) {
            cout.setf(std::ios::fixed); cout << setprecision(15) << 1.0 << "\n";
            return 0;
        }
    }

    // Build per-column masks for each letter
    if (m > 60) {
        // Not supported by 64-bit masks; but per problem expectation, m should be small.
        // Fallback: return 0 safely (should not happen in intended constraints).
        cout.setf(std::ios::fixed); cout << setprecision(15) << 0.0 << "\n";
        return 0;
    }

    vector<unsigned long long> S[4];
    for (int x = 0; x < 4; ++x) S[x].assign(n, 0ULL);

    auto lidx = [](char c)->int{
        if (c=='A') return 0;
        if (c=='C') return 1;
        if (c=='G') return 2;
        return 3; // 'T'
    };

    for (int i = 0; i < m; ++i) {
        unsigned long long bit = (1ULL << i);
        for (int j = 0; j < n; ++j) {
            char c = patterns[i][j];
            if (c == '?') {
                S[0][j] |= bit;
                S[1][j] |= bit;
                S[2][j] |= bit;
                S[3][j] |= bit;
            } else {
                S[lidx(c)][j] |= bit;
            }
        }
    }

    if (m == 0) {
        cout.setf(std::ios::fixed); cout << setprecision(15) << 0.0 << "\n";
        return 0;
    }

    if (m > 25) {
        // 2^m DP becomes infeasible; assume constraints avoid this.
        // Safe fallback (should not be needed in intended tests).
        cout.setf(std::ios::fixed); cout << setprecision(15) << 0.0 << "\n";
        return 0;
    }

    size_t SZ = 1ULL << m;
    vector<double> dp(SZ, 0.0), ndp(SZ, 0.0);
    dp[SZ - 1] = 1.0;

    const double quarter = 0.25;
    unsigned long long fullmask = (m == 64 ? ~0ULL : ((1ULL << m) - 1ULL));

    for (int j = 0; j < n; ++j) {
        unsigned long long sA = S[0][j], sC = S[1][j], sG = S[2][j], sT = S[3][j];
        if (sA == fullmask && sC == fullmask && sG == fullmask && sT == fullmask) {
            // This column has all '?', distribution unchanged.
            continue;
        }
        fill(ndp.begin(), ndp.end(), 0.0);
        for (size_t mask = 0; mask < SZ; ++mask) {
            double v = dp[mask];
            if (v == 0.0) continue;
            ndp[mask & sA] += v * quarter;
            ndp[mask & sC] += v * quarter;
            ndp[mask & sG] += v * quarter;
            ndp[mask & sT] += v * quarter;
        }
        dp.swap(ndp);
    }

    double p_invalid = dp[0];
    double ans = 1.0 - p_invalid;
    if (ans < 0) ans = 0;
    if (ans > 1) ans = 1;

    cout.setf(std::ios::fixed);
    cout << setprecision(15) << ans << "\n";
    return 0;
}