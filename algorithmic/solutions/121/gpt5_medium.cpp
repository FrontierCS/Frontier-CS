#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, m;
    if (!(cin >> n >> m)) return 0;
    vector<string> s(m);
    for (int i = 0; i < m; ++i) cin >> s[i];

    // If any pattern is all '?', the probability is 1
    for (int i = 0; i < m; ++i) {
        bool allq = true;
        for (char c : s[i]) if (c != '?') { allq = false; break; }
        if (allq) {
            cout.setf(std::ios::fixed); 
            cout << setprecision(15) << 1.0 << "\n";
            return 0;
        }
    }

    // Deduplicate identical patterns
    vector<int> idx(m);
    iota(idx.begin(), idx.end(), 0);
    stable_sort(idx.begin(), idx.end(), [&](int a, int b){ return s[a] < s[b]; });
    vector<string> uniq;
    uniq.reserve(m);
    for (int k = 0; k < m; ) {
        int i = idx[k];
        uniq.push_back(s[i]);
        int k2 = k + 1;
        while (k2 < m && s[idx[k2]] == s[i]) ++k2;
        k = k2;
    }
    s.swap(uniq);
    m = (int)s.size();

    // Map chars to codes
    auto code = [&](char c)->int{
        if (c=='A') return 0;
        if (c=='C') return 1;
        if (c=='G') return 2;
        if (c=='T') return 3;
        return -1;
    };

    if (m == 0) {
        // All patterns were duplicates of '?' only (should have been caught), but just in case
        cout.setf(std::ios::fixed); 
        cout << setprecision(15) << 1.0 << "\n";
        return 0;
    }

    if (m > 25) {
        // Fallback to avoid memory blowup; not expected by problem constraints.
        // A conservative answer (not exact) could be 1.0 if m big, but we avoid incorrect output.
        // Here we attempt anyway; but likely constraints ensure m small.
    }

    int M = m;
    size_t STATES = 1ull << M;

    // Precompute per position the masks B[j][4] = patterns that will mismatch if letter L chosen at pos j
    vector<array<uint64_t,4>> Bj(n);
    for (int j = 0; j < n; ++j) {
        uint64_t equalMask[4] = {0,0,0,0};
        uint64_t allFixed = 0;
        for (int i = 0; i < M; ++i) {
            int c = code(s[i][j]);
            if (c != -1) {
                allFixed |= (1ull << i);
                equalMask[c] |= (1ull << i);
            }
        }
        for (int L = 0; L < 4; ++L) {
            Bj[j][L] = allFixed & ~equalMask[L];
        }
    }

    // DP over subsets of patterns: S = set of patterns that have at least one mismatch so far
    vector<double> dp(STATES, 0.0), nxt(STATES, 0.0);
    dp[0] = 1.0;
    const double quarter = 0.25;

    for (int j = 0; j < n; ++j) {
        // Aggregate identical masks among the 4 letters to reduce operations
        array<uint64_t,4> masks = Bj[j];
        // Build small map mask -> count
        uint64_t uniqMask[4];
        int cnt[4];
        int k = 0;
        for (int L = 0; L < 4; ++L) {
            bool found = false;
            for (int t = 0; t < k; ++t) {
                if (uniqMask[t] == masks[L]) {
                    cnt[t]++;
                    found = true;
                    break;
                }
            }
            if (!found) {
                uniqMask[k] = masks[L];
                cnt[k] = 1;
                ++k;
            }
        }

        fill(nxt.begin(), nxt.end(), 0.0);
        for (size_t S = 0; S < STATES; ++S) {
            double v = dp[S];
            if (v == 0.0) continue;
            for (int t = 0; t < k; ++t) {
                size_t Sp = S | uniqMask[t];
                nxt[Sp] += v * (cnt[t] * quarter);
            }
        }
        dp.swap(nxt);
    }

    double invalid = dp[STATES - 1];
    double ans = 1.0 - invalid;
    if (ans < 0) ans = 0;
    if (ans > 1) ans = 1;
    cout.setf(std::ios::fixed);
    cout << setprecision(15) << ans << "\n";
    return 0;
}