#include <bits/stdc++.h>
using namespace std;

static const int MAX_STEPS = 20000;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    cin >> n >> m;
    vector<int> cur(n), target(n);
    for (int i = 0; i < n; i++) cin >> cur[i];
    for (int i = 0; i < n; i++) cin >> target[i];

    vector<vector<int>> adj(n);
    for (int i = 0; i < m; i++) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    vector<int> compId(n, -1);
    vector<vector<int>> comps;
    {
        int cid = 0;
        for (int i = 0; i < n; i++) {
            if (compId[i] != -1) continue;
            queue<int> q;
            q.push(i);
            compId[i] = cid;
            vector<int> comp;
            while (!q.empty()) {
                int u = q.front(); q.pop();
                comp.push_back(u);
                for (int v : adj[u]) if (compId[v] == -1) {
                    compId[v] = cid;
                    q.push(v);
                }
            }
            comps.push_back(move(comp));
            cid++;
        }
    }

    vector<vector<int>> hist;
    hist.reserve(MAX_STEPS + 1);
    hist.push_back(cur);

    auto push_state = [&](vector<int> &next) {
        cur.swap(next);
        hist.push_back(cur);
        if ((int)hist.size() - 1 > MAX_STEPS) {
            // Should not happen with this construction; but keep within limits.
            // If it happens, truncate by exiting early (still must output something valid),
            // though correctness is not guaranteed. Given constraints, this won't trigger.
        }
    };

    auto do_swap = [&](int u, int v) {
        vector<int> next = cur;
        next[u] = cur[v];
        next[v] = cur[u];
        push_state(next);
    };

    auto do_copy = [&](int from, int to) { // to copies from, from stays
        vector<int> next = cur;
        next[to] = cur[from];
        push_state(next);
    };

    auto bfs_dist = [&](int start, int cid) {
        vector<int> dist(n, -1);
        queue<int> q;
        dist[start] = 0;
        q.push(start);
        while (!q.empty()) {
            int u = q.front(); q.pop();
            for (int v : adj[u]) {
                if (compId[v] != cid) continue;
                if (dist[v] != -1) continue;
                dist[v] = dist[u] + 1;
                q.push(v);
            }
        }
        return dist;
    };

    auto choose_center = [&](const vector<int>& comp, int cid) {
        int best = comp[0];
        int bestEcc = INT_MAX;
        for (int s : comp) {
            auto dist = bfs_dist(s, cid);
            int ecc = 0;
            for (int v : comp) ecc = max(ecc, dist[v]);
            if (ecc < bestEcc) {
                bestEcc = ecc;
                best = s;
            }
        }
        return best;
    };

    auto choose_best_source_color = [&](const vector<int>& comp, int cid, int color) {
        int best = -1;
        int bestEcc = INT_MAX;
        for (int s : comp) {
            if (cur[s] != color) continue;
            auto dist = bfs_dist(s, cid);
            int ecc = 0;
            for (int v : comp) ecc = max(ecc, dist[v]);
            if (ecc < bestEcc) {
                bestEcc = ecc;
                best = s;
            }
        }
        return best;
    };

    auto build_bfs_tree = [&](int root, int cid, vector<int>& parent, vector<int>& depth) {
        parent.assign(n, -2);
        depth.assign(n, -1);
        queue<int> q;
        parent[root] = -1;
        depth[root] = 0;
        q.push(root);
        while (!q.empty()) {
            int u = q.front(); q.pop();
            for (int v : adj[u]) {
                if (compId[v] != cid) continue;
                if (depth[v] != -1) continue;
                depth[v] = depth[u] + 1;
                parent[v] = u;
                q.push(v);
            }
        }
    };

    auto lca_tree = [&](int a, int b, const vector<int>& parent) {
        vector<char> seen(n, 0);
        int x = a;
        while (x != -1) {
            seen[x] = 1;
            x = parent[x];
        }
        x = b;
        while (x != -1 && !seen[x]) x = parent[x];
        return x; // assumes connected within component
    };

    auto tree_dist = [&](int a, int b, const vector<int>& parent, const vector<int>& depth) {
        int c = lca_tree(a, b, parent);
        return depth[a] + depth[b] - 2 * depth[c];
    };

    auto get_path = [&](int a, int b, const vector<int>& parent) {
        int c = lca_tree(a, b, parent);
        vector<int> p1, p2;
        int x = a;
        while (x != c) {
            p1.push_back(x);
            x = parent[x];
        }
        p1.push_back(c);
        x = b;
        while (x != c) {
            p2.push_back(x);
            x = parent[x];
        }
        reverse(p2.begin(), p2.end());
        for (int v : p2) p1.push_back(v);
        return p1; // a -> b
    };

    auto solve_component_uniform = [&](const vector<int>& comp, int cid) {
        int c = target[comp[0]];
        for (int v : comp) if (target[v] != c) return false;
        bool already = true;
        for (int v : comp) if (cur[v] != c) { already = false; break; }
        if (already) return true;

        int src = choose_best_source_color(comp, cid, c);
        // src must exist due to solvability
        auto dist = bfs_dist(src, cid);
        int maxD = 0;
        for (int v : comp) maxD = max(maxD, dist[v]);

        // build BFS parent for layers
        vector<int> par(n, -1);
        queue<int> q;
        vector<char> vis(n, 0);
        q.push(src);
        vis[src] = 1;
        while (!q.empty()) {
            int u = q.front(); q.pop();
            for (int v : adj[u]) {
                if (compId[v] != cid) continue;
                if (vis[v]) continue;
                vis[v] = 1;
                par[v] = u;
                q.push(v);
            }
        }

        for (int d = 1; d <= maxD; d++) {
            vector<int> next = cur;
            for (int v : comp) {
                if (dist[v] == d) {
                    int p = par[v];
                    if (p != -1) next[v] = cur[p];
                }
            }
            push_state(next);
        }
        return true;
    };

    auto solve_component_mixed = [&](const vector<int>& comp, int cid) {
        int onesCur = 0, onesTar = 0;
        for (int v : comp) {
            onesCur += cur[v];
            onesTar += target[v];
        }

        // Adjust number of ones
        auto find_boundary_edge = [&]() -> pair<int,int> {
            for (int u : comp) {
                if (cur[u] != 1) continue;
                for (int v : adj[u]) {
                    if (compId[v] != cid) continue;
                    if (cur[v] == 0) return {u, v};
                }
            }
            return {-1, -1};
        };

        while (onesCur < onesTar) {
            auto [u, v] = find_boundary_edge(); // u=1, v=0
            if (u == -1) break; // should not
            do_copy(u, v); // duplicate 1 into v
            onesCur++;
        }
        while (onesCur > onesTar) {
            auto [u, v] = find_boundary_edge(); // u=1, v=0
            if (u == -1) break; // should not
            do_copy(v, u); // u copies 0 from v => delete one
            onesCur--;
        }

        // Reposition ones to match target using swaps on a BFS spanning tree
        int root = choose_center(comp, cid);
        vector<int> parent, depth;
        build_bfs_tree(root, cid, parent, depth);

        vector<int> order;
        order.reserve((int)comp.size() - 1);
        for (int v : comp) if (v != root) order.push_back(v);
        sort(order.begin(), order.end(), [&](int a, int b) {
            return depth[a] > depth[b];
        });

        vector<char> alive(n, 0);
        for (int v : comp) alive[v] = 1;

        for (int v : order) {
            if (!alive[v]) continue;
            int p = parent[v];
            int b = target[v];

            if (cur[v] == b) {
                alive[v] = 0;
                continue;
            }

            // Find closest q (alive, q != v) with cur[q] == b to minimize swaps
            int bestQ = -1;
            int bestD = INT_MAX;
            for (int x : comp) {
                if (!alive[x] || x == v) continue;
                if (cur[x] != b) continue;
                int d = tree_dist(p, x, parent, depth);
                if (d < bestD) {
                    bestD = d;
                    bestQ = x;
                }
            }
            // must exist
            int q = bestQ;
            if (q == -1) {
                // Fallback (should not happen)
                for (int x : comp) if (alive[x] && x != v && cur[x] == b) { q = x; break; }
            }

            if (cur[p] != b) {
                auto path = get_path(p, q, parent); // p -> q
                for (int i = (int)path.size() - 1; i >= 1; i--) {
                    do_swap(path[i], path[i - 1]);
                }
            }
            // Now swap p-v to set v=b
            do_swap(p, v);
            alive[v] = 0;
        }
    };

    for (int cid = 0; cid < (int)comps.size(); cid++) {
        const auto& comp = comps[cid];
        // If component is size 1, nothing special
        if ((int)comp.size() <= 1) continue;

        bool uniform = true;
        for (int v : comp) if (target[v] != target[comp[0]]) { uniform = false; break; }

        if (uniform) {
            solve_component_uniform(comp, cid);
        } else {
            solve_component_mixed(comp, cid);
        }

        // Ensure nodes in this component equal target; if not, fix by flooding each color as last resort (shouldn't trigger)
        bool ok = true;
        for (int v : comp) if (cur[v] != target[v]) { ok = false; break; }
        if (!ok) {
            // Last resort: try to reach target by count adjust + mixed solver again
            solve_component_mixed(comp, cid);
        }
    }

    // Final check: if still not equal, do nothing (guaranteed solvable; above should succeed)
    int k = (int)hist.size() - 1;
    if (k > MAX_STEPS) k = MAX_STEPS; // Should not happen

    cout << k << "\n";
    for (int t = 0; t <= k; t++) {
        for (int i = 0; i < n; i++) {
            if (i) cout << ' ';
            cout << hist[t][i];
        }
        cout << "\n";
    }
    return 0;
}