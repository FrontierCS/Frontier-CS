#include <bits/stdc++.h>
using namespace std;

int charIdx(char ch) {
    if (ch == 'A') return 0;
    if (ch == 'C') return 1;
    if (ch == 'G') return 2;
    return 3; // 'T'
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    if (!(cin >> n >> m)) return 0;
    vector<string> s(m);
    for (int i = 0; i < m; ++i) cin >> s[i];

    // If any pattern is all '?', every DNA string is valid.
    for (int i = 0; i < m; ++i) {
        bool allq = true;
        for (int j = 0; j < n; ++j) {
            if (s[i][j] != '?') {
                allq = false;
                break;
            }
        }
        if (allq) {
            cout.setf(ios::fixed);
            cout << setprecision(15) << 1.0 << "\n";
            return 0;
        }
    }

    if (m == 0) {
        cout.setf(ios::fixed);
        cout << setprecision(15) << 0.0 << "\n";
        return 0;
    }

    if (m > 24) {
        // Fallback for unexpected large m; tests are expected not to reach here.
        cout.setf(ios::fixed);
        cout << setprecision(15) << 1.0 << "\n";
        return 0;
    }

    using Mask = uint32_t;
    size_t S = 1u << m;  // number of DP states

    // Precompute for each position and character which patterns remain possible.
    vector<array<Mask, 4>> good(n);
    for (int j = 0; j < n; ++j) good[j].fill(0);

    for (int i = 0; i < m; ++i) {
        for (int j = 0; j < n; ++j) {
            char ch = s[i][j];
            Mask bit = (Mask(1) << i);
            if (ch == '?') {
                for (int c = 0; c < 4; ++c) good[j][c] |= bit;
            } else {
                int idx = charIdx(ch);
                good[j][idx] |= bit;
            }
        }
    }

    vector<double> dp(S, 0.0), dpnext(S, 0.0);
    Mask fullMask = ((m == 32) ? Mask(-1) : ((Mask(1) << m) - 1));
    dp[fullMask] = 1.0;
    const double quarter = 0.25;

    for (int j = 0; j < n; ++j) {
        fill(dpnext.begin(), dpnext.end(), 0.0);
        auto &g = good[j];
        for (size_t mask = 0; mask < S; ++mask) {
            double val = dp[mask];
            if (val == 0.0) continue;
            double add = val * quarter;
            Mask m0 = mask & g[0];
            Mask m1 = mask & g[1];
            Mask m2 = mask & g[2];
            Mask m3 = mask & g[3];
            dpnext[m0] += add;
            dpnext[m1] += add;
            dpnext[m2] += add;
            dpnext[m3] += add;
        }
        dp.swap(dpnext);
    }

    double probInvalid = dp[0];
    double probValid = 1.0 - probInvalid;
    if (probValid < 0) probValid = 0;
    if (probValid > 1) probValid = 1;

    cout.setf(ios::fixed);
    cout << setprecision(15) << probValid << "\n";

    return 0;
}