#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;
    vector<int> a(n + 1);
    for (int i = 1; i <= n; ++i) cin >> a[i];

    if (n == 1) {
        cout << 1 << "\n" << 0 << "\n";
        return 0;
    }

    int x = 2; // segment length

    vector<int> pos(n + 1);
    for (int i = 1; i <= n; ++i) pos[a[i]] = i;

    vector<array<int,3>> ops;
    ops.reserve(n * n / 2);

    for (int v = 1; v <= n; ++v) {
        int p = pos[v];
        while (p > v) {
            int l = p - 1;
            int r = p;
            // rotate length-2 segment [l, r], direction 0 (left), acts as swap
            ops.push_back({l, r, 0});
            swap(a[l], a[r]);
            pos[a[l]] = l;
            pos[a[r]] = r;
            --p;
        }
    }

    cout << x << "\n";
    cout << (int)ops.size() << "\n";
    for (auto &op : ops) {
        cout << op[0] << " " << op[1] << " " << op[2] << "\n";
    }

    return 0;
}