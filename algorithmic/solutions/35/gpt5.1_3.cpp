#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    const int MAX_N = 300;
    const int MAX_M = 2 * MAX_N - 1; // 599
    const int K = 12;
    const int W = K / 2; // 6

    // Precompute constant-weight (W) codes for up to MAX_M positions
    vector<int> base_code(MAX_M + 1); // 1-based
    int cnt = 1;
    for (int mask = 0; mask < (1 << K) && cnt <= MAX_M; ++mask) {
        if (__builtin_popcount(mask) == W) {
            base_code[cnt++] = mask;
        }
    }

    int T;
    if (!(cin >> T)) return 0;

    while (T--) {
        int n;
        if (!(cin >> n)) return 0;
        if (n == -1) return 0; // previous answer was wrong

        int m = 2 * n - 1;

        // Build subsets S[b] for this test case (only indices 1..m)
        vector<vector<int>> S(K);
        for (int i = 1; i <= m; ++i) {
            int mask = base_code[i];
            for (int b = 0; b < K; ++b) {
                if (mask & (1 << b)) {
                    S[b].push_back(i);
                }
            }
        }

        int unique_x = -1;

        for (int x = 1; x <= n; ++x) {
            int pop = 0;
            for (int b = 0; b < K; ++b) {
                const auto &vec = S[b];
                cout << "? " << x << " " << vec.size();
                for (int idx : vec) cout << " " << idx;
                cout << endl;
                cout.flush();

                int ans;
                if (!(cin >> ans)) return 0;
                if (ans == -1) return 0; // invalid query or too many
                pop += ans;
            }
            if (pop == W) {
                unique_x = x;
            }
        }

        if (unique_x == -1) unique_x = 1; // fallback, should not happen

        cout << "! " << unique_x << endl;
        cout.flush();
    }

    return 0;
}