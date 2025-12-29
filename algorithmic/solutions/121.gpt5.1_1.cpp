#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    if (!(cin >> n >> m)) return 0;

    vector<string> s(m);
    for (int i = 0; i < m; ++i) cin >> s[i];

    auto mp = [](char c) -> uint8_t {
        if (c == 'A') return 0;
        if (c == 'C') return 1;
        if (c == 'G') return 2;
        if (c == 'T') return 3;
        return 4; // '?'
    };

    vector<vector<uint8_t>> pat(m, vector<uint8_t>(n));
    for (int i = 0; i < m; ++i) {
        for (int j = 0; j < n; ++j) {
            pat[i][j] = mp(s[i][j]);
        }
    }

    // Buffers for current pattern of intersection at each recursion level
    vector<vector<uint8_t>> buf(m + 1, vector<uint8_t>(n, 4)); // 4 means "free / '?'"

    // Precompute 4^{-k} for k = 0..n
    vector<long double> invPow4(n + 1);
    invPow4[0] = 1.0L;
    for (int k = 1; k <= n; ++k) invPow4[k] = invPow4[k - 1] / 4.0L;

    long double ans = 0.0L;

    function<void(int, int, int, uint8_t*)> dfs = [&](int idx, int sz, int freeCnt, uint8_t* state) {
        if (idx == m) {
            if (sz == 0) return; // skip empty subset
            int nonfree = n - freeCnt;
            long double prob = invPow4[nonfree];
            if (sz & 1) ans += prob;
            else ans -= prob;
            return;
        }

        // Exclude pattern idx
        dfs(idx + 1, sz, freeCnt, state);

        // Include pattern idx
        uint8_t* next = buf[idx + 1].data();
        bool conflict = false;
        int newFree = freeCnt;

        for (int j = 0; j < n; ++j) {
            uint8_t prevc = state[j];      // 0..3 letter, 4 = free
            uint8_t addc = pat[idx][j];    // 0..3 letter, 4 = '?'

            if (addc == 4) {
                next[j] = prevc;
            } else if (prevc == 4) {
                next[j] = addc;
                --newFree;
            } else if (prevc == addc) {
                next[j] = prevc;
            } else {
                conflict = true;
                break;
            }
        }

        if (!conflict) {
            dfs(idx + 1, sz + 1, newFree, next);
        }
    };

    dfs(0, 0, n, buf[0].data());

    cout.setf(ios::fixed);
    cout << setprecision(15) << (long double)ans << "\n";

    return 0;
}