#include <bits/stdc++.h>
using namespace std;

static inline long long comb_ll(int n, int k) {
    if (k < 0 || k > n) return 0;
    if (k > n - k) k = n - k;
    long long res = 1;
    for (int i = 1; i <= k; ++i) {
        res = res * (n - k + i) / i;
    }
    return res;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int T;
    if (!(cin >> T)) return 0;
    while (T--) {
        int n;
        if (!(cin >> n)) return 0;
        if (n == -1) return 0; // protocol: -1 means wrong answer to previous test

        int m = 2 * n - 1;

        // Choose minimal L such that C(L, floor(L/2)) >= m
        int L = 1;
        while (comb_ll(L, L / 2) < m) ++L;
        int w = L / 2;

        // Generate first m distinct masks of length L with exactly w ones
        vector<uint64_t> masks(m, 0);
        vector<int> pick(w);
        for (int i = 0; i < w; ++i) pick[i] = i;

        auto next_comb = [&](vector<int> &c) -> bool {
            int k = (int)c.size();
            for (int i = k - 1; i >= 0; --i) {
                if (c[i] != i + (L - k)) {
                    ++c[i];
                    for (int j = i + 1; j < k; ++j) c[j] = c[j - 1] + 1;
                    return true;
                }
            }
            return false;
        };

        for (int idx = 0; idx < m; ++idx) {
            uint64_t mask = 0;
            for (int b : pick) mask |= (1ULL << b);
            masks[idx] = mask;
            if (idx + 1 < m) {
                bool ok = next_comb(pick);
                if (!ok) {
                    // Should not happen since choose(L, w) >= m
                    // But if it does, just repeat last mask (still distinctness needed though)
                    // In practice, this won't occur.
                }
            }
        }

        // Build S_k = { positions j | bit k in masks[j] is set }
        vector<vector<int>> S(L);
        for (int k = 0; k < L; ++k) {
            for (int j = 0; j < m; ++j) {
                if ((masks[j] >> k) & 1ULL) S[k].push_back(j + 1);
            }
        }

        auto ask = [&](int x, const vector<int>& subset) -> int {
            cout << "? " << x << " " << subset.size();
            for (int v : subset) cout << " " << v;
            cout << "\n";
            cout.flush();
            int ans;
            if (!(cin >> ans)) return -1;
            return ans;
        };

        int answer = 1; // fallback
        for (int x = 1; x <= n; ++x) {
            int cnt = 0;
            for (int k = 0; k < L; ++k) {
                int r = ask(x, S[k]);
                if (r == -1) return 0;
                cnt += r;
            }
            if (cnt == w) {
                answer = x;
                break;
            }
        }

        cout << "! " << answer << "\n";
        cout.flush();
    }

    return 0;
}