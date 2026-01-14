#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if (!(cin >> n)) return 0;
    vector<int> a(n);
    for (int i = 0; i < n; ++i) cin >> a[i];
    
    vector<int> pos(n + 1);
    for (int i = 0; i < n; ++i) pos[a[i]] = i;

    vector<pair<int,int>> ops;
    ops.reserve((long long)n * max(1, n/2)); // rough reserve to reduce reallocs

    for (int i = 0; i < n; ++i) {
        int val = i + 1;
        int p = pos[val];
        while (p > i) {
            // swap positions p-1 and p (0-based), corresponds to reversing [p, p+1] (1-based)
            ops.emplace_back(p, p + 1); // store 1-based indices later
            int u = a[p - 1], v = a[p];
            swap(a[p - 1], a[p]);
            pos[u] = p;
            pos[v] = p - 1;
            --p;
        }
    }

    cout << 1 << "\n"; // choose x = 1 -> allowed lengths: 2 and 0 (we only use length 2)
    cout << ops.size() << "\n";
    for (auto &op : ops) {
        cout << op.first << " " << op.second << "\n";
    }
    return 0;
}