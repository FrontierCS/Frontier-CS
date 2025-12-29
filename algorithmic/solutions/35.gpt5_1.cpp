#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int t;
    if (!(cin >> t)) return 0;
    for (int tc = 0; tc < t; ++tc) {
        int n;
        if (!(cin >> n)) return 0;
        int check;
        if (!(cin >> check)) return 0;
        if (check == -1) return 0;

        int tot = 2 * n - 1;
        const int k = 12;
        const int d = 6;

        vector<uint16_t> codes;
        codes.reserve(tot);
        for (int mask = 0; mask < (1 << k) && (int)codes.size() < tot; ++mask) {
            if (__builtin_popcount(mask) == d) {
                codes.push_back((uint16_t)mask);
            }
        }

        vector<vector<int>> sets(k);
        for (int i = 0; i < tot; ++i) {
            for (int j = 0; j < k; ++j) {
                if ((codes[i] >> j) & 1) {
                    sets[j].push_back(i + 1);
                }
            }
        }

        vector<uint16_t> vecs(n, 0);

        for (int j = 0; j < k; ++j) {
            vector<int> &S = sets[j];
            for (int x = 1; x <= n; ++x) {
                cout << "? " << x << " " << (int)S.size();
                for (int v : S) {
                    cout << " " << v;
                }
                cout << endl;
                cout.flush();
                int ret;
                if (!(cin >> ret)) return 0;
                if (ret == -1) return 0;
                if (ret == 1) {
                    vecs[x - 1] |= (1u << j);
                }
            }
        }

        int ans = -1;
        for (int x = 1; x <= n; ++x) {
            if (__builtin_popcount((unsigned)vecs[x - 1]) == d) {
                ans = x;
                break;
            }
        }
        if (ans == -1) ans = 1;

        cout << "! " << ans << endl;
        cout.flush();
    }
    return 0;
}