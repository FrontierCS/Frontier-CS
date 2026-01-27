#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if (!(cin >> n)) return 0;
    vector<int> a(n+1), pos(n+1);
    for (int i = 1; i <= n; ++i) {
        cin >> a[i];
        pos[a[i]] = i;
    }
    
    vector<pair<int,int>> ops;
    ops.reserve(600000); // reserve large enough space for worst-case
    
    // Use adjacent swaps (length 2 reversals) to sort
    for (int val = 1; val <= n; ++val) {
        int p = pos[val];
        while (p > val) {
            // reverse segment [p-1, p] of length 2
            int u = a[p-1], v = a[p];
            swap(a[p-1], a[p]);
            pos[u] = p;
            pos[v] = p-1;
            ops.emplace_back(p-1, p);
            --p;
        }
    }
    
    // Output
    int x = 3; // allows segment lengths 2 and 4; we use length 2 reversals
    cout << x << "\n";
    cout << ops.size() << "\n";
    for (auto &op : ops) {
        cout << op.first << " " << op.second << "\n";
    }
    return 0;
}