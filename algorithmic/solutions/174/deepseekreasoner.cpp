#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    cin >> n >> m;
    vector<vector<int>> adj(n + 1);
    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    // Find connected components
    vector<int> comp_id(n + 1, -1);
    vector<vector<int>> comps;
    int cur_comp = 0;
    for (int i = 1; i <= n; ++i) {
        if (comp_id[i] != -1) continue;
        queue<int> q;
        q.push(i);
        comp_id[i] = cur_comp;
        vector<int> comp;
        comp.push_back(i);
        while (!q.empty()) {
            int u = q.front(); q.pop();
            for (int v : adj[u]) {
                if (comp_id[v] == -1) {
                    comp_id[v] = cur_comp;
                    q.push(v);
                    comp.push_back(v);
                }
            }
        }
        comps.push_back(comp);
        ++cur_comp;
    }

    vector<int> color(n + 1, 0);
    vector<int> side(n + 1, -1);          // for bipartite check
    random_device rd;
    mt19937 rng(rd());
    uniform_int_distribution<int> col_dist(1, 3);

    for (const auto& comp : comps) {
        int sz = comp.size();
        if (sz == 1) {
            color[comp[0]] = 1;
            continue;
        }

        // Check bipartiteness
        bool bipartite = true;
        int start = comp[0];
        side[start] = 0;
        queue<int> q;
        q.push(start);
        while (!q.empty()) {
            int u = q.front(); q.pop();
            for (int v : adj[u]) {
                if (side[v] == -1) {
                    side[v] = 1 - side[u];
                    q.push(v);
                } else if (side[v] == side[u]) {
                    bipartite = false;
                    break;
                }
            }
            if (!bipartite) break;
        }
        // Reset side for vertices in this component
        for (int v : comp) side[v] = -1;

        if (bipartite) {
            // Assign 2-coloring (colors 1 and 2)
            side[start] = 0;
            q.push(start);
            while (!q.empty()) {
                int u = q.front(); q.pop();
                for (int v : adj[u]) {
                    if (side[v] == -1) {
                        side[v] = 1 - side[u];
                        q.push(v);
                    }
                }
            }
            for (int v : comp) color[v] = side[v] + 1;
            for (int v : comp) side[v] = -1;
            continue;
        }

        // Non‑bipartite component: local search with random restarts
        const int RESTARTS = 10;
        int best_conflicts = INT_MAX;
        vector<int> best_coloring(sz);

        for (int restart = 0; restart < RESTARTS; ++restart) {
            vector<int> cur_color(n + 1);
            for (int v : comp) cur_color[v] = col_dist(rng);

            // cnt[v][c] = number of neighbors of v with color c
            vector<array<int, 4>> cnt(n + 1);
            for (int v : comp) {
                for (int u : adj[v]) {
                    cnt[v][cur_color[u]]++;
                }
            }

            int total_conflicts = 0;
            for (int v : comp) total_conflicts += cnt[v][cur_color[v]];
            total_conflicts /= 2;

            bool improved = true;
            while (improved) {
                improved = false;
                vector<int> order = comp;
                shuffle(order.begin(), order.end(), rng);
                for (int v : order) {
                    int cur_col = cur_color[v];
                    int cur_conflicts = cnt[v][cur_col];
                    int best_delta = 0;
                    int best_new_col = cur_col;
                    for (int new_col = 1; new_col <= 3; ++new_col) {
                        if (new_col == cur_col) continue;
                        int new_conflicts = cnt[v][new_col];
                        int delta = new_conflicts - cur_conflicts;
                        if (delta < best_delta) {
                            best_delta = delta;
                            best_new_col = new_col;
                        }
                    }
                    if (best_delta < 0) {
                        improved = true;
                        total_conflicts += best_delta;
                        int old_col = cur_col;
                        int new_col = best_new_col;
                        cur_color[v] = new_col;
                        for (int u : adj[v]) {
                            cnt[u][old_col]--;
                            cnt[u][new_col]++;
                        }
                    }
                }
            }

            if (total_conflicts < best_conflicts) {
                best_conflicts = total_conflicts;
                for (int i = 0; i < sz; ++i)
                    best_coloring[i] = cur_color[comp[i]];
            }
        }

        for (int i = 0; i < sz; ++i)
            color[comp[i]] = best_coloring[i];
    }

    for (int i = 1; i <= n; ++i)
        cout << color[i] << " \n"[i == n];

    return 0;
}