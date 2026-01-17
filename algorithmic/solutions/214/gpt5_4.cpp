#include <bits/stdc++.h>
using namespace std;

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
    
    vector<pair<int,int>> ops;
    ops.reserve(1LL * n * (n - 1) / 2);
    
    for (int v = 1; v <= n; ++v) {
        int p = pos[v];
        while (p > v) {
            // swap positions p-1 and p
            ops.emplace_back(p - 1, p);
            int w = a[p - 1];
            swap(a[p - 1], a[p]);
            pos[v] = p - 1;
            pos[w] = p;
            --p;
        }
    }
    
    cout << 1 << "\n"; // x = 1, allowed length 2 (and 0 which we don't use)
    cout << ops.size() << "\n";
    for (auto &op : ops) {
        cout << op.first << " " << op.second << "\n";
    }
    return 0;
}