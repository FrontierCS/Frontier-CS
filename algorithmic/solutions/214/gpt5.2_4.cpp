#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;
    vector<int> a(n + 1), pos(n + 1);
    for (int i = 1; i <= n; i++) {
        cin >> a[i];
        pos[a[i]] = i;
    }

    int x = (n >= 4 ? 3 : 1);
    vector<pair<int,int>> ops;
    ops.reserve(200000);

    auto doSwap2 = [&](int l) {
        int r = l + 1;
        int u = a[l], v = a[r];
        a[l] = v; a[r] = u;
        pos[u] = r;
        pos[v] = l;
        ops.push_back({l, r});
    };

    auto doRev4 = [&](int l) {
        int r = l + 3;
        int v1 = a[l], v2 = a[l+1], v3 = a[l+2], v4 = a[l+3];
        a[l] = v4; a[l+1] = v3; a[l+2] = v2; a[l+3] = v1;
        pos[v4] = l;
        pos[v3] = l + 1;
        pos[v2] = l + 2;
        pos[v1] = l + 3;
        ops.push_back({l, r});
    };

    if (n <= 1) {
        // nothing
    } else if (x == 1) {
        for (int v = 1; v <= n; v++) {
            while (pos[v] > v) doSwap2(pos[v] - 1);
        }
    } else {
        // x = 3, allowed lengths 2 and 4
        for (int v = 1; v <= n; v++) {
            while (pos[v] - v >= 3) doRev4(pos[v] - 3);
            while (pos[v] > v) doSwap2(pos[v] - 1);
        }
    }

    cout << x << "\n" << ops.size() << "\n";
    for (auto [l, r] : ops) cout << l << " " << r << "\n";
    return 0;
}