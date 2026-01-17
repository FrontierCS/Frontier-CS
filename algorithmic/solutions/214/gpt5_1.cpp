#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if (!(cin >> n)) return 0;
    vector<int> a(n + 1);
    for (int i = 1; i <= n; ++i) cin >> a[i];

    int x = (n >= 2 ? 3 : 1); // allow length 2 reversals when n >= 2
    vector<pair<int,int>> ops;
    ops.reserve(600000);

    if (n >= 2) {
        vector<int> pos(n + 1);
        for (int i = 1; i <= n; ++i) pos[a[i]] = i;

        for (int target = 1; target <= n; ++target) {
            int j = pos[target];
            while (j > target) {
                // swap positions j-1 and j using a reversal of length 2
                ops.emplace_back(j - 1, j);
                int v1 = a[j - 1], v2 = a[j];
                swap(a[j - 1], a[j]);
                pos[v1] = j;
                pos[v2] = j - 1;
                --j;
            }
        }
    }

    cout << x << "\n";
    cout << (int)ops.size() << "\n";
    for (auto &op : ops) {
        cout << op.first << " " << op.second << "\n";
    }
    return 0;
}