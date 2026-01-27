#include <bits/stdc++.h>
using namespace std;

static inline void flush() {
    cout << flush;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if (!(cin >> n)) return 0;

    auto ask = [&](int v, int a, int b)->int {
        cout << "? 2 " << v << " " << a << " " << b << "\n";
        flush();
        int resp;
        if (!(cin >> resp)) exit(0);
        if (resp == -1) exit(0);
        return resp;
    };

    int r = 1;
    vector<int> depth(n+1, 0);
    // Compute depth[v] = |path(r,v)| - 1
    for (int v = 1; v <= n; ++v) {
        if (v == r) { depth[v] = 0; continue; }
        int cnt = 2; // r and v are always on the path
        for (int t = 1; t <= n; ++t) {
            if (t == r || t == v) continue;
            int ans = ask(t, r, v);
            cnt += ans;
        }
        depth[v] = cnt - 1;
    }

    // Order nodes by depth descending for parent search convenience
    vector<int> order(n);
    iota(order.begin(), order.end(), 1);
    sort(order.begin(), order.end(), [&](int a, int b){
        if (depth[a] != depth[b]) return depth[a] > depth[b];
        return a < b;
    });

    vector<int> parent(n+1, -1);
    parent[r] = 0;

    // For nodes in increasing depth (skip root), find parent
    vector<int> nodes_by_inc_depth(n);
    iota(nodes_by_inc_depth.begin(), nodes_by_inc_depth.end(), 1);
    sort(nodes_by_inc_depth.begin(), nodes_by_inc_depth.end(), [&](int a, int b){
        if (depth[a] != depth[b]) return depth[a] < depth[b];
        return a < b;
    });

    for (int v : nodes_by_inc_depth) {
        if (v == r) continue;
        // Find deepest u with depth[u] < depth[v] and u lies on path r-v
        for (int u : order) {
            if (u == v) continue;
            if (depth[u] >= depth[v]) continue;
            int on = ask(u, r, v);
            if (on == 1) {
                parent[v] = u;
                break;
            }
        }
        if (parent[v] == -1) {
            // Should not happen; fallback to root
            parent[v] = r;
        }
    }

    cout << "!\n";
    for (int v = 1; v <= n; ++v) {
        if (v == r) continue;
        cout << parent[v] << " " << v << "\n";
    }
    flush();

    return 0;
}