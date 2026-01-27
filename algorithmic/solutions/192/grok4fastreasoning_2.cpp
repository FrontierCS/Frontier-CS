#include <bits/stdc++.h>
using namespace std;

vector<int> get_coloring(const vector<vector<int>>& adj, int n) {
    vector<int> side(n + 1, -1);
    for (int i = 1; i <= n; ++i) {
        if (side[i] == -1) {
            queue<int> q;
            q.push(i);
            side[i] = 0;
            while (!q.empty()) {
                int u = q.front(); q.pop();
                for (int v : adj[u]) {
                    if (side[v] == -1) {
                        side[v] = 1 - side[u];
                        q.push(v);
                    }
                }
            }
        }
    }
    return side;
}

int compute_cut(const vector<vector<int>>& adj, const vector<int>& side, int n) {
    int c = 0;
    for (int u = 1; u <= n; ++u) {
        for (int v : adj[u]) {
            if (v > u && side[u] != side[v]) ++c;
        }
    }
    return c;
}

pair<vector<int>, int> local_search(const vector<vector<int>>& adj, const vector<int>& deg, vector<int> initial_side, int n, int max_iters) {
    vector<int> side = initial_side;
    int iters = 0;
    while (iters < max_iters) {
        ++iters;
        vector<int> cut_deg(n + 1, 0);
        for (int u = 1; u <= n; ++u) {
            for (int v : adj[u]) {
                if (side[u] != side[v]) ++cut_deg[u];
            }
        }
        int max_delta = 0;
        int best_u = -1;
        for (int u = 1; u <= n; ++u) {
            int d = deg[u] - 2 * cut_deg[u];
            if (d > max_delta) {
                max_delta = d;
                best_u = u;
            }
        }
        if (max_delta <= 0) {
            break;
        }
        side[best_u] = 1 - side[best_u];
    }
    int current_cut = compute_cut(adj, side, n);
    return {side, current_cut};
}

int main() {
    int n, m;
    cin >> n >> m;
    vector<vector<int>> adj(n + 1);
    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }
    vector<int> deg(n + 1, 0);
    for (int i = 1; i <= n; ++i) {
        deg[i] = adj[i].size();
    }
    srand(time(0));
    vector<int> best_side(n + 1, 0);
    int best_c = 0;

    // Try coloring initial
    vector<int> col_side = get_coloring(adj, n);
    auto [ls_side, ls_c] = local_search(adj, deg, col_side, n, 2000);
    best_c = ls_c;
    best_side = ls_side;

    // Try 10 random initials
    for (int trial = 0; trial < 10; ++trial) {
        vector<int> side(n + 1);
        for (int i = 1; i <= n; ++i) {
            side[i] = rand() % 2;
        }
        auto [new_side, new_c] = local_search(adj, deg, side, n, 1000);
        if (new_c > best_c) {
            best_c = new_c;
            best_side = new_side;
        }
    }

    for (int i = 1; i <= n; ++i) {
        if (i > 1) cout << " ";
        cout << best_side[i];
    }
    cout << endl;
    return 0;
}