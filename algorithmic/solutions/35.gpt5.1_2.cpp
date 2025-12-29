#include <bits/stdc++.h>
using namespace std;

const int K = 12;          // number of bits
const int R = 6;           // number of 1s in each code
const int MAXN = 300;
const int MAXM = 2 * MAXN - 1;

int codes[MAXM + 1];

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    // Precompute codes for positions up to MAXM
    int cnt = 0;
    for (int mask = 0; mask < (1 << K) && cnt < MAXM; ++mask) {
        if (__builtin_popcount(mask) == R) {
            codes[++cnt] = mask;
        }
    }

    int t;
    if (!(cin >> t)) return 0;

    for (int tc = 1; tc <= t; ++tc) {
        int n;
        if (!(cin >> n)) return 0;
        int m = 2 * n - 1;

        // Build sets S_j for this test case
        vector<int> S[K];
        for (int i = 1; i <= m; ++i) {
            int mask = codes[i];
            for (int j = 0; j < K; ++j) {
                if (mask & (1 << j)) {
                    S[j].push_back(i);
                }
            }
        }

        int unique_val = -1;

        for (int x = 1; x <= n; ++x) {
            int weight = 0;
            for (int j = 0; j < K; ++j) {
                cout << "? " << x << " " << S[j].size();
                for (int idx : S[j]) {
                    cout << " " << idx;
                }
                cout << '\n';
                cout.flush();

                int ans;
                if (!(cin >> ans)) return 0;
                if (ans == -1) return 0;
                weight += ans;
            }
            if (weight == R) {
                unique_val = x;
            }
        }

        if (unique_val == -1) unique_val = 1;  // fallback, should not happen

        cout << "! " << unique_val << '\n';
        cout.flush();

        int verdict;
        if (!(cin >> verdict)) return 0;
        if (verdict == -1) return 0;
    }

    return 0;
}