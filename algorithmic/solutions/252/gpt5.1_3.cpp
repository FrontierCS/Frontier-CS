#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;
    vector<int> a(n + 1);
    for (int i = 1; i <= n; ++i) {
        if (!(cin >> a[i])) a[i] = 1;
        if (a[i] < 1 || a[i] > n) a[i] = 1; // safety
    }

    vector<int> root(n + 1, 0), idx(n + 1, -1);

    for (int i = 1; i <= n; ++i) {
        if (root[i] != 0) continue;
        vector<int> path;
        int v = i;
        while (root[v] == 0 && idx[v] == -1) {
            idx[v] = (int)path.size();
            path.push_back(v);
            v = a[v];
        }
        int rid;
        if (v >= 1 && v <= n && root[v] != 0) {
            rid = root[v];
        } else if (v >= 1 && v <= n && idx[v] != -1) {
            int cycStartIdx = idx[v];
            rid = path[cycStartIdx];
            for (int j = cycStartIdx; j < (int)path.size(); ++j)
                root[path[j]] = rid;
        } else {
            // In case of invalid a[v], treat as its own root
            rid = path.back();
        }
        for (int u : path) {
            if (root[u] == 0) root[u] = rid;
            idx[u] = -1;
        }
    }

    int r1 = root[1];
    vector<int> ans;
    for (int i = 1; i <= n; ++i) {
        if (root[i] == r1) ans.push_back(i);
    }

    cout << ans.size() << '\n';
    for (int i = 0; i < (int)ans.size(); ++i) {
        if (i) cout << ' ';
        cout << ans[i];
    }
    cout << '\n';

    return 0;
}