#include <bits/stdc++.h>
using namespace std;

const int INF = 1e9 + 5;

vector<vector<int>> adj, edge_id, distt, dp0, dp1, best_match_child;
vector<pair<int, int>> edge_list;

pair<int, int> compute_dp(int u, int par, const vector<vector<pair<int, pair<int, int>>>>& adj_u, vector<bool>& vis) {
    vis[u] = true;
    vector<int> children;
    vector<pair<int, int>> child_dps;
    vector<int> child_weights; // weight to this child
    int sum_max = 0;
    int max_add = -INF;
    int best_j = -1;
    for (auto& pr : adj_u[u]) {
        int v = pr.first;
        int w = pr.second.second;
        int eid = pr.second.first;
        if (v == par) continue;
        children.push_back(v);
        child_weights.push_back(w);
        auto res = compute_dp(v, u, adj_u, vis);
        dp0[v] = res.first;
        dp1[v] = res.second;
        int maxv = max(res.first, res.second);
        child_dps.push_back({res.first, res.second});
        sum_max += maxv;
        int delta = w + res.first - maxv;
        if (delta > max_add) {
            max_add = delta;
            best_j = children.size() - 1;
        }
    }
    int m0 = sum_max;
    int m1;
    if (children.empty()) {
        m1 = -INF;
    } else {
        m1 = sum_max + max_add;
        best_match_child[u] = children[best_j];
    }
    dp0[u] = m0;
    dp1[u] = m1;
    return {m0, m1};
}

void collect_sub(int u, int par, bool covered_by_parent, const vector<vector<pair<int, pair<int, int>>>>& adj_u, vector<int>& selected) {
    if (covered_by_parent) {
        // take M0
        for (auto& prr : adj_u[u]) {
            int v = prr.first;
            if (v == par) continue;
            collect_sub(v, u, false, adj_u, selected);
        }
        return;
    }
    // not covered, decide M0 or M1
    bool use_m1_here = (dp1[u] > dp0[u]);
    if (use_m1_here && dp1[u] != -INF) {
        int v = best_match_child[u];
        // find eid
        for (auto& prr : adj_u[u]) {
            if (prr.first == v) {
                selected.push_back(prr.second.first);
                break;
            }
        }
        collect_sub(v, u, true, adj_u, selected);
        for (auto& prr : adj_u[u]) {
            int w = prr.first;
            if (w != par && w != v) {
                collect_sub(w, u, false, adj_u, selected);
            }
        }
    } else {
        // take M0
        for (auto& prr : adj_u[u]) {
            int v = prr.first;
            if (v == par) continue;
            collect_sub(v, u, false, adj_u, selected);
        }
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int T;
    cin >> T;
    for (int t = 0; t < T; t++) {
        int n;
        cin >> n;
        vector<int> p(n + 1);
        for (int i = 1; i <= n; i++) {
            cin >> p[i];
        }
        adj.assign(n + 1, {});
        edge_id.assign(n + 1, vector<int>(n + 1, 0));
        edge_list.assign(n, {});
        for (int i = 1; i <= n - 1; i++) {
            int u, v;
            cin >> u >> v;
            adj[u].push_back(v);
            adj[v].push_back(u);
            edge_id[u][v] = i;
            edge_id[v][u] = i;
            edge_list[i] = {u, v};
        }
        // precompute dist
        distt.assign(n + 1, vector<int>(n + 1, -1));
        for (int s = 1; s <= n; s++) {
            queue<int> q;
            q.push(s);
            distt[s][s] = 0;
            vector<bool> vis_dist(n + 1, false);
            vis_dist[s] = true;
            while (!q.empty()) {
                int u = q.front();
                q.pop();
                for (int v : adj[u]) {
                    if (!vis_dist[v]) {
                        vis_dist[v] = true;
                        distt[s][v] = distt[s][u] + 1;
                        q.push(v);
                    }
                }
            }
        }
        // now simulate
        vector<vector<int>> ops;
        int max_steps = 4 * n; // safety
        for (int step = 0; step < max_steps; step++) {
            bool done = true;
            for (int i = 1; i <= n; i++) {
                if (p[i] != i) {
                    done = false;
                    break;
                }
            }
            if (done) break;
            // compute adj_u
            vector<vector<pair<int, pair<int, int>>>> adj_u(n + 1);
            for (int u = 1; u <= n; u++) {
                for (int v : adj[u]) {
                    if (u >= v) continue; // to add once
                    int a = p[u], b = p[v];
                    int old_da = distt[u][a];
                    int old_db = distt[v][b];
                    int new_da = distt[v][a];
                    int new_db = distt[u][b];
                    int ch = (new_da + new_db) - (old_da + old_db);
                    if (ch <= 0) {
                        int w = -ch;
                        int eid = edge_id[u][v];
                        adj_u[u].emplace_back(v, make_pair(eid, w));
                        adj_u[v].emplace_back(u, make_pair(eid, w));
                    }
                }
            }
            // now process components
            vector<bool> vis(n + 1, false);
            dp0.assign(n + 1, 0);
            dp1.assign(n + 1, 0);
            best_match_child.assign(n + 1, 0);
            vector<int> this_op;
            for (int i = 1; i <= n; i++) {
                if (!vis[i] && !adj_u[i].empty()) {
                    compute_dp(i, 0, adj_u, vis);
                    // now collect
                    vector<int> comp_sel;
                    bool use_m1_root = (dp1[i] > dp0[i]);
                    if (use_m1_root && dp1[i] != -INF) {
                        int v = best_match_child[i];
                        // find eid
                        for (auto& prr : adj_u[i]) {
                            if (prr.first == v) {
                                comp_sel.push_back(prr.second.first);
                                break;
                            }
                        }
                        collect_sub(v, i, true, adj_u, comp_sel);
                        for (auto& prr : adj_u[i]) {
                            int w = prr.first;
                            if (w != v && w != 0) {
                                collect_sub(w, i, false, adj_u, comp_sel);
                            }
                        }
                    } else {
                        for (auto& prr : adj_u[i]) {
                            int w = prr.first;
                            if (w != 0) {
                                collect_sub(w, i, false, adj_u, comp_sel);
                            }
                        }
                    }
                    for (int e : comp_sel) {
                        this_op.push_back(e);
                    }
                }
            }
            // now if this_op empty, but not done, problem, but assume not
            if (this_op.empty()) {
                // perhaps add nothing, but to prevent infinite, break
                break;
            }
            ops.push_back(this_op);
            // perform swaps
            for (int ei : this_op) {
                auto [u, v] = edge_list[ei];
                swap(p[u], p[v]);
            }
        }
        // output
        cout << ops.size() << '\n';
        for (auto& op : ops) {
            cout << op.size();
            for (int e : op) {
                cout << ' ' << e;
            }
            cout << '\n';
        }
    }
    return 0;
}