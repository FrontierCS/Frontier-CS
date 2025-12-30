#include <bits/stdc++.h>
using namespace std;

static inline int sgn(long long x) { return (x > 0) ? 1 : -1; }

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int t;
    if (!(cin >> t)) return 0;

    for (int tc = 0; tc < t; tc++) {
        int n;
        cin >> n;
        for (int i = 0; i < n - 1; i++) {
            int u, v;
            cin >> u >> v;
        }

        auto query_all = [&](int n) -> long long {
            cout << "? 1 " << n;
            for (int i = 1; i <= n; i++) cout << ' ' << i;
            cout << '\n';
            cout.flush();
            long long res;
            if (!(cin >> res)) exit(0);
            return res;
        };

        auto toggle = [&](int u) {
            cout << "? 2 " << u << '\n';
            cout.flush();
        };

        vector<int> ans(n + 1, 1);

        long long S0 = query_all(n);
        long long prevS = S0;

        for (int i = 1; i <= n - 1; i++) {
            toggle(i);
            long long curS = query_all(n);
            long long diff = curS - prevS; // diff = -2 * val_before[i] * subtree_size[i]
            ans[i] = sgn(diff);            // final value after toggle
            prevS = curS;
        }

        toggle(n);
        long long diff_last = (-S0) - prevS; // since toggling all nodes makes sum become -S0
        ans[n] = sgn(diff_last);

        cout << "!";
        for (int i = 1; i <= n; i++) cout << ' ' << ans[i];
        cout << '\n';
        cout.flush();
    }

    return 0;
}