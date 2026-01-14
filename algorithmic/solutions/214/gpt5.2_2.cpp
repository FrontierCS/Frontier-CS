#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    cin >> n;
    vector<int> a(n + 1), pos(n + 1);
    for (int i = 1; i <= n; i++) {
        cin >> a[i];
        pos[a[i]] = i;
    }

    int x = (n == 1 ? 2 : 3); // prefer x=3 (lengths 2 and 4); for n=1, x=2 (length 1 exists)
    vector<pair<int,int>> ops;
    ops.reserve(200000);

    auto rev2 = [&](int l) {
        int v1 = a[l], v2 = a[l + 1];
        a[l] = v2; a[l + 1] = v1;
        pos[v1] = l + 1;
        pos[v2] = l;
        ops.push_back({l, l + 1});
    };

    auto rev4 = [&](int l) {
        int v0 = a[l], v1 = a[l + 1], v2 = a[l + 2], v3 = a[l + 3];
        a[l] = v3; a[l + 1] = v2; a[l + 2] = v1; a[l + 3] = v0;
        pos[v0] = l + 3;
        pos[v1] = l + 2;
        pos[v2] = l + 1;
        pos[v3] = l;
        ops.push_back({l, l + 3});
    };

    for (int i = n; i >= 1; --i) {
        while (pos[i] + 3 <= i) {
            rev4(pos[i]);
        }
        while (pos[i] < i) {
            rev2(pos[i]);
        }
    }

    cout << x << "\n" << ops.size() << "\n";
    for (auto &op : ops) {
        cout << op.first << " " << op.second << "\n";
    }
    return 0;
}