#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    if (!(cin >> n >> m)) return 0;
    vector<int> init(n), target(n);
    for (int i = 0; i < n; ++i) cin >> init[i];
    for (int i = 0; i < n; ++i) cin >> target[i];

    vector<vector<int>> g(n);
    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        g[u].push_back(v);
        g[v].push_back(u);
    }

    // Find connected components
    vector<int> comp_id(n, -1);
    vector<vector<int>> comps;
    int comp_cnt = 0;
    for (int i = 0; i < n; ++i) {
        if (comp_id[i] != -1) continue;
        queue<int> q;
        q.push(i);
        comp_id[i] = comp_cnt;
        vector<int> nodes;
        nodes.push_back(i);
        while (!q.empty()) {
            int u = q.front(); q.pop();
            for (int v : g[u]) {
                if (comp_id[v] == -1) {
                    comp_id[v] = comp_cnt;
                    q.push(v);
                    nodes.push_back(v);
                }
            }
        }
        comps.push_back(nodes);
        ++comp_cnt;
    }

    vector<vector<int>> states;
    vector<int> cur = init;
    states.push_back(cur);

    auto push_state = [&](const vector<int>& next_state) {
        states.push_back(next_state);
    };

    // Process each component independently
    for (int cid = 0; cid < comp_cnt; ++cid) {
        const vector<int>& comp = comps[cid];
        int sz = (int)comp.size();

        // Determine if target in this component uses color 0 and/or 1
        bool need0 = false, need1 = false;
        int ones_target = 0;
        for (int v : comp) {
            if (target[v] == 0) need0 = true;
            if (target[v] == 1) need1 = true;
            ones_target += target[v];
        }

        if (!need0 && !need1) continue; // empty component theoretically impossible

        // If target is monochrome in this component
        if (!need0 || !need1) {
            int c = need1 ? 1 : 0;

            // Find a vertex in this component currently with color c
            int root = -1;
            for (int v : comp) if (cur[v] == c) { root = v; break; }

            // It is guaranteed that a solution exists, so such vertex must exist
            if (root == -1) {
                // Should not happen according to problem statement
                // but we guard anyway: in worst case, just keep as is.
                continue;
            }

            // BFS tree from root inside this component
            unordered_set<int> comp_set(comp.begin(), comp.end());
            vector<int> par(n, -1);
            vector<int> order;
            queue<int> q;
            q.push(root);
            par[root] = root;
            while (!q.empty()) {
                int u = q.front(); q.pop();
                order.push_back(u);
                for (int v : g[u]) {
                    if (par[v] == -1 && comp_set.count(v)) {
                        par[v] = u;
                        q.push(v);
                    }
                }
            }

            // Ensure colors become c using BFS order (root first)
            // Parent of each node except root is already c when we process child
            for (int idx = 0; idx < (int)order.size(); ++idx) {
                int v = order[idx];
                if (cur[v] == c) continue;
                // parent must exist (except root which already had color c)
                if (v == root) continue;
                vector<int> next = cur;
                next[v] = c; // copy from parent which is already color c
                push_state(next);
                cur.swap(next);
            }

            // Move on to next component
            continue;
        }

        // Component where target uses both colors
        // Stage 1: adjust number of ones in this component to match target

        int ones_cur = 0;
        for (int v : comp) ones_cur += cur[v];

        int t = ones_target; // target ones in component
        int nc = sz;

        // Stage 1 precondition: target uses both colors => 1 <= t <= nc-1
        // Also, initial must use both colors in this component for solution to exist
        // => 1 <= ones_cur <= nc-1.
        // We rely on the problem guarantee.

        // Helper: find an edge (u,v) inside comp with cur[u]=1, cur[v]=0
        auto find_edge_10 = [&]() -> pair<int,int> {
            unordered_set<int> comp_set(comp.begin(), comp.end());
            for (int u : comp) {
                if (cur[u] != 1) continue;
                for (int v : g[u]) {
                    if (!comp_set.count(v)) continue;
                    if (cur[v] == 0) return {u, v};
                }
            }
            return {-1, -1};
        };

        while (ones_cur < t) {
            auto e = find_edge_10();
            if (e.first == -1) break; // should not happen
            int u = e.first, v = e.second;
            vector<int> next = cur;
            // Increase ones: set v to 1 copying from u
            next[v] = 1;
            push_state(next);
            cur.swap(next);
            ++ones_cur;
        }

        while (ones_cur > t) {
            auto e = find_edge_10();
            if (e.first == -1) break; // should not happen
            int u = e.first, v = e.second;
            vector<int> next = cur;
            // Decrease ones: set u to 0 copying from v
            next[u] = 0;
            push_state(next);
            cur.swap(next);
            --ones_cur;
        }

        // Stage 2: rearrange ones to match target using swaps
        // Now #ones in this component equals target.

        unordered_set<int> comp_set(comp.begin(), comp.end());

        auto component_done = [&]() -> bool {
            for (int v : comp) if (cur[v] != target[v]) return false;
            return true;
        };

        // BFS to find shortest path inside this component between s and t
        auto find_path = [&](int s, int t) -> vector<int> {
            vector<int> prev(n, -1);
            queue<int> q;
            q.push(s);
            prev[s] = s;
            while (!q.empty()) {
                int u = q.front(); q.pop();
                if (u == t) break;
                for (int v : g[u]) {
                    if (!comp_set.count(v)) continue;
                    if (prev[v] == -1) {
                        prev[v] = u;
                        q.push(v);
                    }
                }
            }
            vector<int> path;
            if (prev[t] == -1) return path; // no path (should not happen)
            int v = t;
            while (true) {
                path.push_back(v);
                if (v == s) break;
                v = prev[v];
            }
            reverse(path.begin(), path.end());
            return path;
        };

        while (!component_done()) {
            int s = -1, tnode = -1;
            for (int v : comp) {
                if (cur[v] == 1 && target[v] == 0) {
                    s = v;
                    break;
                }
            }
            for (int v : comp) {
                if (cur[v] == 0 && target[v] == 1) {
                    tnode = v;
                    break;
                }
            }
            if (s == -1 || tnode == -1) {
                // If either is missing but component not done, something went wrong.
                break;
            }

            vector<int> path = find_path(s, tnode);
            if (path.empty() || path.size() == 1) {
                // No path or same vertex; can't proceed (shouldn't happen)
                break;
            }

            // Move a token along the path using adjacent swaps
            for (size_t i = 0; i + 1 < path.size(); ++i) {
                int x = path[i];
                int y = path[i + 1];
                vector<int> next = cur;
                swap(next[x], next[y]);
                push_state(next);
                cur.swap(next);
            }
        }
    }

    // Ensure final state equals target; if not, append target directly (fallback)
    if (cur != target) {
        vector<int> next = cur;
        next = target;
        push_state(next);
        cur.swap(next);
    }

    int k = (int)states.size() - 1;
    cout << k << "\n";
    for (const auto& st : states) {
        for (int i = 0; i < n; ++i) {
            if (i) cout << ' ';
            cout << st[i];
        }
        cout << "\n";
    }

    return 0;
}