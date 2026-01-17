#include <bits/stdc++.h>
using namespace std;

struct Edge {
    int u, v;
};

vector<vector<int>> adj; // tree adjacency
vector<Edge> edges; // edges indexed from 1

// DFS to mark component of 'start' avoiding 'forbid'
void dfs(int start, int parent, int forbid, vector<bool>& vis) {
    vis[start] = true;
    for (int nb : adj[start]) {
        if (nb == parent || nb == forbid) continue;
        dfs(nb, start, forbid, vis);
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);

    int T;
    cin >> T;
    while (T--) {
        int n;
        cin >> n;
        vector<int> p(n + 1);
        for (int i = 1; i <= n; ++i) cin >> p[i];

        adj.assign(n + 1, {});
        edges.resize(n); // we use indices 1..n-1
        vector<vector<int>> edge_id(n + 1, vector<int>(n + 1, 0));

        for (int i = 1; i <= n - 1; ++i) {
            int u, v;
            cin >> u >> v;
            edges[i] = {u, v};
            adj[u].push_back(v);
            adj[v].push_back(u);
            edge_id[u][v] = edge_id[v][u] = i;
        }

        // precompute for each edge e and each vertex x which side x is on
        // side[e][x] = 0 if x is in component of u, 1 if in component of v
        vector<vector<int>> side(n, vector<int>(n + 1)); // use only 1..n-1 for e
        for (int idx = 1; idx <= n - 1; ++idx) {
            int u = edges[idx].u, v = edges[idx].v;
            vector<bool> vis(n + 1, false);
            dfs(u, -1, v, vis);
            for (int x = 1; x <= n; ++x) {
                side[idx][x] = vis[x] ? 0 : 1;
            }
        }

        vector<int> cur = p;
        vector<vector<int>> operations;

        while (true) {
            // check if sorted
            bool sorted = true;
            for (int i = 1; i <= n; ++i) {
                if (cur[i] != i) {
                    sorted = false;
                    break;
                }
            }
            if (sorted) break;

            // find active edges
            vector<int> active_edges;
            for (int idx = 1; idx <= n - 1; ++idx) {
                int u = edges[idx].u, v = edges[idx].v;
                int a = cur[u], b = cur[v];
                // both tokens want to cross the edge?
                if (side[idx][a] == 1 && side[idx][b] == 0) {
                    active_edges.push_back(idx);
                }
            }

            // According to the reasoning, there should be at least one active edge.
            // But just in case, break to avoid infinite loop.
            if (active_edges.empty()) break;

            // build subgraph of active edges
            vector<vector<int>> act_adj(n + 1);
            vector<int> deg(n + 1, 0);
            for (int idx : active_edges) {
                int u = edges[idx].u, v = edges[idx].v;
                act_adj[u].push_back(v);
                act_adj[v].push_back(u);
                deg[u]++;
                deg[v]++;
            }

            // greedy maximum matching on forest (leaf removal)
            vector<bool> removed(n + 1, false);
            vector<int> matching;
            queue<int> leaf_q;
            for (int i = 1; i <= n; ++i) {
                if (deg[i] == 1) leaf_q.push(i);
            }

            while (!leaf_q.empty()) {
                int u = leaf_q.front(); leaf_q.pop();
                if (removed[u] || deg[u] == 0) continue;
                int v = -1;
                for (int w : act_adj[u]) {
                    if (!removed[w]) {
                        v = w;
                        break;
                    }
                }
                if (v == -1) continue; // should not happen

                int eid = edge_id[u][v];
                matching.push_back(eid);
                removed[u] = removed[v] = true;

                // decrease degrees of neighbors of u and v
                for (int w : act_adj[u]) {
                    if (!removed[w]) {
                        deg[w]--;
                        if (deg[w] == 1) leaf_q.push(w);
                    }
                }
                for (int w : act_adj[v]) {
                    if (!removed[w]) {
                        deg[w]--;
                        if (deg[w] == 1) leaf_q.push(w);
                    }
                }
            }

            // perform the swaps
            for (int eid : matching) {
                int u = edges[eid].u, v = edges[eid].v;
                swap(cur[u], cur[v]);
            }

            operations.push_back(matching);
        }

        // output
        cout << operations.size() << "\n";
        for (const vector<int>& op : operations) {
            cout << op.size();
            for (int eid : op) cout << " " << eid;
            cout << "\n";
        }
    }
    return 0;
}