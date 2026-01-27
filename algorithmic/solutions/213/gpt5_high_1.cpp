#include <bits/stdc++.h>
using namespace std;

struct Op {
    int l, r, dir;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if (!(cin >> n)) return 0;
    vector<int> a(n + 1);
    for (int i = 1; i <= n; ++i) cin >> a[i];

    vector<int> pos(n + 1);
    for (int i = 1; i <= n; ++i) pos[a[i]] = i;

    vector<Op> ops;
    ops.reserve(500000);

    int x = 2;

    for (int val = 1; val <= n; ++val) {
        int p = pos[val];
        while (p > val) {
            int k = p - 1;
            ops.push_back({k, k + 1, 0});
            // swap in array and update positions
            int v1 = a[k], v2 = a[k + 1];
            swap(a[k], a[k + 1]);
            pos[v1] = k + 1;
            pos[v2] = k;
            --p;
        }
    }

    cout << x << '\n' << ops.size() << '\n';
    for (auto &op : ops) {
        cout << op.l << ' ' << op.r << ' ' << op.dir << '\n';
    }
    return 0;
}