#include <bits/stdc++.h>
using namespace std;

int main() {
    vector<vector<int>> grid(30);
    for (int x = 0; x < 30; x++) {
        grid[x].resize(x + 1);
        for (int y = 0; y <= x; y++) {
            cin >> grid[x][y];
        }
    }
    vector<int> prefix(31, 0);
    for (int x = 1; x <= 30; x++) {
        prefix[x] = prefix[x - 1] + x;
    }
    auto idx = [&](int x, int y) { return prefix[x] + y; };
    vector<vector<int>> adj(465);
    for (int x = 0; x < 30; x++) {
        for (int y = 0; y < x; y++) {
            int i1 = idx(x, y), i2 = idx(x, y + 1);
            adj[i1].push_back(i2);
            adj[i2].push_back(i1);
        }
    }
    for (int x = 0; x < 29; x++) {
        for (int yy = 0; yy <= x + 1; yy++) {
            int i2 = idx(x + 1, yy);
            if (yy <= x) {
                int i1 = idx(x, yy);
                adj[i1].push_back(i2);
                adj[i2].push_back(i1);
            }
            if (yy > 0) {
                int yy1 = yy - 1;
                int i1 = idx(x, yy1);
                adj[i1].push_back(i2);
                adj[i2].push_back(i1);
            }
        }
    }
    vector<int> current(465);
    vector<int> whereis(465);
    for (int x = 0; x < 30; x++) {
        for (int y = 0; y <= x; y++) {
            int pos = idx(x, y);
            int num = grid[x][y];
            current[pos] = num;
            whereis[num] = pos;
        }
    }
    auto get_xy = [&](int id) -> pair<int, int> {
        for (int xx = 0; xx < 30; xx++) {
            int start = prefix[xx];
            int len = xx + 1;
            if (id >= start && id < start + len) {
                int yy = id - start;
                return {xx, yy};
            }
        }
        assert(false);
        return {-1, -1};
    };
    vector<array<int, 4>> operations;
    for (int t = 0; t < 465; t++) {
        int q = whereis[t];
        if (q == t) continue;
        vector<int> parent(465, -1);
        vector<bool> vis(465, false);
        queue<int> qu;
        qu.push(q);
        vis[q] = true;
        parent[q] = -1;
        while (!qu.empty()) {
            int u = qu.front(); qu.pop();
            for (int v : adj[u]) {
                if (v >= t && !vis[v]) {
                    vis[v] = true;
                    parent[v] = u;
                    qu.push(v);
                }
            }
        }
        vector<int> path;
        for (int at = t;; at = parent[at]) {
            path.push_back(at);
            if (at == q) break;
        }
        reverse(path.begin(), path.end());
        for (size_t i = path.size() - 1; i > 0; i--) {
            int a = path[i - 1];
            int b = path[i];
            int n1 = current[a], n2 = current[b];
            current[a] = n2;
            current[b] = n1;
            whereis[n1] = b;
            whereis[n2] = a;
            auto [x1, y1] = get_xy(a);
            auto [x2, y2] = get_xy(b);
            operations.push_back({x1, y1, x2, y2});
        }
    }
    cout << operations.size() << endl;
    for (auto& op : operations) {
        cout << op[0] << " " << op[1] << " " << op[2] << " " << op[3] << endl;
    }
    return 0;
}