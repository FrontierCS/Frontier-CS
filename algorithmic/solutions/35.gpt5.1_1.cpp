#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    const int MAX_N = 300;
    const int MAX_IND = 2 * MAX_N - 1; // 599
    const int BITS = 12;
    const int WEIGHT = 6;

    // Precompute constant-weight codes for positions 1..MAX_IND
    vector<int> masks;
    for (int mask = 0; mask < (1 << BITS) && (int)masks.size() < MAX_IND; ++mask) {
        if (__builtin_popcount(mask) == WEIGHT) {
            masks.push_back(mask);
        }
    }
    if ((int)masks.size() < MAX_IND) {
        // Should never happen for BITS=12, WEIGHT=6
        return 0;
    }
    vector<int> posMask(MAX_IND + 1);
    for (int i = 1; i <= MAX_IND; ++i) posMask[i] = masks[i - 1];

    int t;
    if (!(cin >> t)) return 0;

    for (int tc = 0; tc < t; ++tc) {
        int n;
        cin >> n;              // n for this test case
        int status;
        cin >> status;         // verdict for previous test case (or 0 for the first)
        if (status == -1) return 0;

        int m = 2 * n - 1;

        // Build subsets S_b for this test (indices 1..m)
        vector<vector<int>> S(BITS);
        for (int i = 1; i <= m; ++i) {
            int mask = posMask[i];
            for (int b = 0; b < BITS; ++b) {
                if (mask & (1 << b)) S[b].push_back(i);
            }
        }

        vector<int> pattern(n + 1, 0);

        // Query patterns for each value x
        for (int x = 1; x <= n; ++x) {
            int pat = 0;
            for (int b = 0; b < BITS; ++b) {
                cout << "? " << x << " " << S[b].size();
                for (int idx : S[b]) cout << " " << idx;
                cout << '\n';
                cout.flush();

                int res;
                if (!(cin >> res)) return 0;
                if (res == -1) return 0;
                if (res == 1) pat |= (1 << b);
            }
            pattern[x] = pat;
        }

        int unique_x = -1;
        for (int x = 1; x <= n; ++x) {
            if (__builtin_popcount(pattern[x]) == WEIGHT) {
                unique_x = x;
                break;
            }
        }
        if (unique_x == -1) unique_x = 1; // fallback, should not occur

        cout << "! " << unique_x << '\n';
        cout.flush();
    }

    return 0;
}