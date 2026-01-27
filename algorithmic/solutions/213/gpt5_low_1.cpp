#include <bits/stdc++.h>
using namespace std;

struct Op {
    int l, r, dir;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if(!(cin >> n)) return 0;
    vector<int> a(n+1), pos(n+1);
    for (int i = 1; i <= n; ++i) {
        cin >> a[i];
        pos[a[i]] = i;
    }
    int x = 2;
    vector<Op> ops;
    ops.reserve(n * n / 2);
    for (int i = 1; i <= n; ++i) {
        int p = pos[i];
        while (p > i) {
            // swap positions p-1 and p using a left shift on [p-1, p]
            ops.push_back({p-1, p, 0});
            int v1 = a[p-1], v2 = a[p];
            swap(a[p-1], a[p]);
            pos[v1] = p;
            pos[v2] = p-1;
            --p;
        }
    }
    cout << x << " " << ops.size() << "\n";
    for (auto &op : ops) {
        cout << op.l << " " << op.r << " " << op.dir << "\n";
    }
    return 0;
}