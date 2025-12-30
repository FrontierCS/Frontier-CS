#include <bits/stdc++.h>
using namespace std;

static inline void die() {
    exit(0);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int t;
    if (!(cin >> t)) return 0;
    while (t--) {
        int n;
        cin >> n;
        for (int i = 0; i < n - 1; i++) {
            int u, v;
            cin >> u >> v;
        }

        string nodesList;
        nodesList.reserve(n * 5);
        for (int i = 1; i <= n; i++) {
            nodesList += to_string(i);
            if (i < n) nodesList.push_back(' ');
        }

        auto toggle = [&](int u) {
            cout << "? 2 " << u << '\n';
            cout.flush();
        };

        auto queryTotal = [&]() -> long long {
            cout << "? 1 " << n << ' ' << nodesList << '\n';
            cout.flush();
            long long res;
            if (!(cin >> res)) die();
            if (res == -1) die();
            return res;
        };

        vector<long long> tot(n + 1, 0);
        for (int i = 1; i <= n; i++) {
            toggle(i);
            tot[i] = queryTotal();
        }

        vector<int> ans(n + 1, 1);

        auto signToVal = [&](long long x) -> int {
            if (x > 0) return 1;
            if (x < 0) return -1;
            return 1;
        };

        long long Tn = tot[n];
        long long delta1 = tot[1] + Tn; // T0 = -Tn
        ans[1] = signToVal(delta1);

        for (int i = 2; i <= n; i++) {
            long long delta = tot[i] - tot[i - 1];
            ans[i] = signToVal(delta);
        }

        cout << "!";
        for (int i = 1; i <= n; i++) cout << ' ' << ans[i];
        cout << '\n';
        cout.flush();
    }

    return 0;
}