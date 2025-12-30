#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(NULL);
    int n, m;
    cin >> n >> m;
    vector<int> a(10);
    for (int i = 0; i < 10; i++) {
        cin >> a[i];
    }
    vector<vector<int>> adj(n + 1);
    vector<int> indeg(n + 1, 0);
    vector<int> outdeg(n + 1, 0);
    for (int i = 0; i < m; i++) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
        indeg[v]++;
        outdeg[u]++;
    }
    int start = -1;
    for (int i = 1; i <= n; i++) {
        if (indeg[i] == 0) {
            start = i;
            break;
        }
    }
    if (start == -1) {
        start = 1;
    }
    // sort adj by outdeg ascending
    for (int u = 1; u <= n; u++) {
        sort(adj[u].begin(), adj[u].end(), [&](int x, int y) {
            return outdeg[x] < outdeg[y];
        });
    }
    // now backtracking
    vector<int> pathh;
    vector<char> vis(n + 1, 0);
    vector<int> best;
    int maxk = 0;
    auto dfs = [&](auto&& self, int u, int cnt) -> void {
        int num_ext = 0;
        for (int v : adj[u]) {
            if (vis[v] == 0) {
                num_ext++;
                pathh.push_back(v);
                vis[v] = 1;
                self(self, v, cnt + 1);
                pathh.pop_back();
                vis[v] = 0;
            }
        }
        if (num_ext == 0) {
            if (cnt > maxk) {
                maxk = cnt;
                best = pathh;
            }
        }
    };
    pathh.reserve(n + 1);
    pathh.push_back(start);
    vis[start] = 1;
    dfs(dfs, start, 1);
    // output
    cout << maxk << '\n';
    for (size_t i = 0; i < best.size(); i++) {
        cout << best[i];
        if (i + 1 < best.size()) cout << " ";
        else cout << '\n';
    }
    return 0;
}