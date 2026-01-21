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
    vector<int> a(n + 1), pos(n + 1);
    for (int i = 1; i <= n; ++i) {
        cin >> a[i];
        pos[a[i]] = i;
    }

    vector<Op> ops;
    auto rotate_left = [&](int l) {
        int r = l + 1;
        // x = 2, left shift just swaps
        swap(a[l], a[r]);
        pos[a[l]] = l;
        pos[a[r]] = r;
        ops.push_back({l, r, 0});
    };

    int x = (n == 1 ? 1 : 2);

    for (int val = 1; val <= n; ++val) {
        int p = pos[val];
        while (p > val) {
            rotate_left(p - 1);
            --p;
        }
    }

    cout << x << "\n";
    cout << (int)ops.size() << "\n";
    for (auto &op : ops) {
        cout << op.l << " " << op.r << " " << op.dir << "\n";
    }
    return 0;
}