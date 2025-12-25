#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int T;
    cin >> T;
    for (int t = 0; t < T; ++t) {
        int n;
        cin >> n;
        vector<int> current_p(n + 1);
        for (int i = 1; i <= n; ++i) {
            cin >> current_p[i];
        }
        vector<vector<int>> adj(n + 1);
        vector<pair<int, int>> tree_edges(n - 1);
        vector<vector<int>> edge_to(n + 1, vector<int>(n + 1, 0));
        for (int i = 0; i < n - 1; ++i) {
            int u, v;
            cin >> u >> v;
            tree_edges[i] = {u, v};
            adj[u].push_back(v);
            adj[v].push_back(u);
            edge_to[u][v] = i + 1;
            edge_to[v][u] = i + 1;
        }
        
        // Build children, root at 1
        vector<vector<int>> children(n + 1);
        vector<int> parent(n + 1, -1);
        queue<int> q;
        q.push(1);
        parent[1] = 0;
        while (!q.empty()) {
            int u = q.front();
            q.pop();
            for (int v : adj[u]) {
                if (v != parent[u]) {
                    parent[v] = u;
                    children[u].push_back(v);
                    q.push(v);
                }
            }
        }
        
        // Precompute next_step and dist
        vector<vector<int>> next_step(n + 1, vector<int>(n + 1, 0));
        vector<vector<int>> distance(n + 1, vector<int>(n + 1, 0));
        for (int tt = 1; tt <= n; ++tt) {
            vector<int> par(n + 1, -1);
            vector<int> d(n + 1, -1);
            queue<int> qq;
            qq.push(tt);
            par[tt] = tt;
            d[tt] = 0;
            while (!qq.empty()) {
                int u = qq.front();
                qq.pop();
                for (int v : adj[u]) {
                    if (d[v] == -1) {
                        d[v] = d[u] + 1;
                        par[v] = u;
                        qq.push(v);
                    }
                }
            }
            for (int s = 1; s <= n; ++s) {
                distance[s][tt] = d[s];
                if (s != tt) {
                    next_step[s][tt] = par[s];
                } else {
                    next_step[s][tt] = 0;
                }
            }
        }
        
        // Now simulation
        vector<vector<int>> operations;
        vector<int> M0(n + 1), M1(n + 1, -1000000000), best_c(n + 1, -1);
        auto dfs = [&](auto&& self, int u, int p, const vector<int>& edge_typee) -> void {
            vector<int> subm;
            int sum_m0 = 0;
            int idx = 0;
            for (int c : children[u]) {
                if (c == p) continue;
                self(self, c, u, edge_typee);
                int mx = M0[c];
                if (M1[c] > mx) mx = M1[c];
                subm.push_back(mx);
                sum_m0 += mx;
                ++idx;
            }
            M0[u] = sum_m0;
            int nc = children[u].size();
            int best_size = -1000000000;
            int bestchild = -1;
            for (int i = 0; i < nc; ++i) {
                int c = children[u][i];
                if (c == p) continue;
                int eidx = edge_to[u][c];
                int typp = edge_typee[eidx];
                if (typp == 0) continue;
                int this_sum = sum_m0 - subm[i] + M0[c];
                int this_size = 1 + this_sum;
                if (this_size > best_size) {
                    best_size = this_size;
                    bestchild = c;
                }
            }
            if (bestchild != -1) {
                M1[u] = best_size;
                best_c[u] = bestchild;
            }
        };
        
        auto collect = [&](auto&& self, int u, int p, bool useM1, vector<int>& sel, const vector<int>& edge_typee) -> void {
            if (useM1) {
                int c = best_c[u];
                if (c == -1) return;
                int eidx = edge_to[u][c];
                sel.push_back(eidx);
                self(self, c, u, false, sel, edge_typee);
                for (int v : children[u]) {
                    if (v == c || v == p) continue;
                    bool ch_use = (M1[v] >= M0[v]);
                    self(self, v, u, ch_use, sel, edge_typee);
                }
            } else {
                for (int v : children[u]) {
                    if (v == p) continue;
                    bool ch_use = (M1[v] >= M0[v]);
                    self(self, v, u, ch_use, sel, edge_typee);
                }
            }
        };
        
        int max_steps = 4 * n;
        int step = 0;
        bool is_sorted = true;
        for (int i = 1; i <= n; ++i) {
            if (current_p[i] != i) {
                is_sorted = false;
                break;
            }
        }
        while (!is_sorted && step < max_steps) {
            ++step;
            is_sorted = true;
            for (int i = 1; i <= n; ++i) {
                if (current_p[i] != i) {
                    is_sorted = false;
                    break;
                }
            }
            if (is_sorted) break;
            
            // compute edge_type
            vector<int> edge_type(n);
            for (int i = 1; i <= n - 1; ++i) {
                int u = tree_edges[i - 1].first;
                int v = tree_edges[i - 1].second;
                int tu = current_p[u];
                int tv = current_p[v];
                bool wuv = (next_step[u][tu] == v);
                bool wvu = (next_step[v][tv] == u);
                edge_type[i] = (wuv ? 1 : 0) + (wvu ? 1 : 0);
            }
            
            // reset dp
            fill(M0.begin(), M0.end(), 0);
            fill(M1.begin(), M1.end(), -1000000000);
            fill(best_c.begin(), best_c.end(), -1);
            
            // dfs
            dfs(dfs, 1, -1, edge_type);
            
            int size0 = M0[1];
            int size1 = (M1[1] > -100000000 ? M1[1] : -1000000000);
            
            vector<int> chosen_sel;
            vector<int> temp_sel;
            if (size1 > size0) {
                temp_sel.clear();
                collect(collect, 1, -1, true, temp_sel, edge_type);
                chosen_sel = temp_sel;
            } else if (size0 > size1) {
                temp_sel.clear();
                collect(collect, 1, -1, false, temp_sel, edge_type);
                chosen_sel = temp_sel;
            } else {
                // equal
                temp_sel.clear();
                collect(collect, 1, -1, false, temp_sel, edge_type);
                vector<int> sel0 = temp_sel;
                int ben0 = 0;
                for (int e : sel0) ben0 += edge_type[e];
                
                vector<int> sel1;
                int ben1 = 0;
                bool can1 = (M1[1] > -100000000);
                if (can1) {
                    temp_sel.clear();
                    collect(collect, 1, -1, true, temp_sel, edge_type);
                    sel1 = temp_sel;
                    for (int e : sel1) ben1 += edge_type[e];
                }
                
                if (!can1 || ben0 > ben1) {
                    chosen_sel = sel0;
                } else {
                    chosen_sel = sel1;
                }
            }
            
            if (chosen_sel.empty()) {
                // stuck, break
                break;
            }
            
            // perform swaps
            for (int eidx : chosen_sel) {
                int u = tree_edges[eidx - 1].first;
                int v = tree_edges[eidx - 1].second;
                swap(current_p[u], current_p[v]);
            }
            
            // add to operations
            operations.push_back(chosen_sel);
        }
        
        // output
        cout << operations.size() << '\n';
        for (auto& op : operations) {
            cout << op.size();
            for (int e : op) {
                cout << ' ' << e;
            }
            cout << '\n';
        }
    }
    return 0;
}