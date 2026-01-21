#include <bits/stdc++.h>
using namespace std;

static const int STEP_LIMIT = 20000;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    cin >> n >> m;
    vector<int> cur(n), target(n);
    for (int i = 0; i < n; i++) cin >> cur[i];
    for (int i = 0; i < n; i++) cin >> target[i];

    vector<vector<int>> g(n);
    for (int i = 0; i < m; i++) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        g[u].push_back(v);
        g[v].push_back(u);
    }

    vector<vector<int>> states;
    states.push_back(cur);

    auto push_state = [&](const vector<int>& st) {
        states.push_back(st);
        if ((int)states.size() - 1 > STEP_LIMIT) {
            // Should not happen with this construction under given constraints.
            // If it does, truncate with a valid (but likely incomplete) output.
            // Still try to avoid UB by exiting.
            cout << (int)states.size() - 2 << "\n";
            for (int i = 0; i < (int)states.size() - 1; i++) {
                for (int j = 0; j < n; j++) {
                    if (j) cout << ' ';
                    cout << states[i][j];
                }
                cout << "\n";
            }
            exit(0);
        }
    };

    auto do_copy = [&](int v, int from) {
        if (cur[v] == cur[from]) return;
        vector<int> nxt = cur;
        nxt[v] = cur[from];
        cur.swap(nxt);
        push_state(cur);
    };

    auto do_swap = [&](int a, int b) {
        if (cur[a] == cur[b]) return;
        vector<int> nxt = cur;
        nxt[a] = cur[b];
        nxt[b] = cur[a];
        cur.swap(nxt);
        push_state(cur);
    };

    // Components
    vector<int> compId(n, -1);
    vector<vector<int>> comps;
    int cid = 0;
    for (int i = 0; i < n; i++) {
        if (compId[i] != -1) continue;
        queue<int> q;
        q.push(i);
        compId[i] = cid;
        comps.push_back({});
        while (!q.empty()) {
            int u = q.front(); q.pop();
            comps.back().push_back(u);
            for (int v : g[u]) {
                if (compId[v] == -1) {
                    compId[v] = cid;
                    q.push(v);
                }
            }
        }
        cid++;
    }

    vector<vector<int>> tree(n);
    vector<char> vis(n, 0);
    vector<int> parent(n, -1);

    for (int cc = 0; cc < (int)comps.size(); cc++) {
        const auto& nodes = comps[cc];
        int sz = (int)nodes.size();
        if (sz == 1) continue;

        // Build spanning tree for this component
        for (int v : nodes) {
            tree[v].clear();
            vis[v] = 0;
            parent[v] = -1;
        }
        int root = nodes[0];
        queue<int> q;
        q.push(root);
        vis[root] = 1;
        parent[root] = root;
        while (!q.empty()) {
            int u = q.front(); q.pop();
            for (int v : g[u]) {
                if (compId[v] != cc) continue;
                if (!vis[v]) {
                    vis[v] = 1;
                    parent[v] = u;
                    tree[u].push_back(v);
                    tree[v].push_back(u);
                    q.push(v);
                }
            }
        }

        // Count adjustment: make number of ones match target in this component
        auto count_ones = [&](const vector<int>& a) {
            int c = 0;
            for (int v : nodes) c += a[v];
            return c;
        };
        int c0 = count_ones(cur);
        int ct = count_ones(target);

        auto find_boundary_edge_10 = [&]() -> pair<int,int> {
            // find u=1, v=0 adjacent in component
            for (int u : nodes) {
                if (cur[u] != 1) continue;
                for (int v : g[u]) {
                    if (compId[v] != cc) continue;
                    if (cur[v] == 0) return {u, v};
                }
            }
            return {-1, -1};
        };

        while (c0 < ct) {
            auto [u, v] = find_boundary_edge_10();
            if (u == -1) break; // should not happen if solvable
            do_copy(v, u);
            c0++;
        }
        while (c0 > ct) {
            auto [u, v] = find_boundary_edge_10();
            if (u == -1) break; // should not happen if solvable
            do_copy(u, v);
            c0--;
        }

        // Swap-based leaf elimination on the spanning tree to match target exactly
        vector<char> alive(n, 0);
        vector<int> deg(n, 0);
        for (int v : nodes) alive[v] = 1;
        for (int v : nodes) {
            int d = 0;
            for (int to : tree[v]) if (alive[to]) d++;
            deg[v] = d;
        }
        int aliveCount = sz;
        int finalVertex = root;

        auto remove_leaf = [&](int leaf) {
            alive[leaf] = 0;
            aliveCount--;
            int nb = -1;
            for (int to : tree[leaf]) if (alive[to]) { nb = to; break; }
            deg[leaf] = 0;
            if (nb != -1) deg[nb]--;
        };

        auto bfs_path_alive = [&](int s, int t) -> vector<int> {
            vector<int> par(n, -1);
            queue<int> qq;
            qq.push(s);
            par[s] = s;
            while (!qq.empty()) {
                int u = qq.front(); qq.pop();
                if (u == t) break;
                for (int v : tree[u]) {
                    if (!alive[v]) continue;
                    if (par[v] != -1) continue;
                    par[v] = u;
                    qq.push(v);
                }
            }
            vector<int> path;
            if (par[t] == -1) return path;
            int x = t;
            while (x != s) {
                path.push_back(x);
                x = par[x];
            }
            path.push_back(s);
            reverse(path.begin(), path.end());
            return path;
        };

        while (aliveCount > 1) {
            int leaf = -1;
            for (int v : nodes) {
                if (alive[v] && deg[v] == 1 && v != finalVertex) { leaf = v; break; }
            }
            if (leaf == -1) {
                for (int v : nodes) {
                    if (alive[v] && deg[v] == 1) { leaf = v; break; }
                }
            }
            if (leaf == -1) break; // should not happen

            if (cur[leaf] == target[leaf]) {
                remove_leaf(leaf);
                continue;
            }

            int desired = target[leaf];
            int src = -1;
            for (int v : nodes) {
                if (alive[v] && v != leaf && cur[v] == desired) { src = v; break; }
            }
            if (src == -1) {
                // Should not happen if counts are correct; fallback: just remove if possible
                remove_leaf(leaf);
                continue;
            }

            vector<int> path = bfs_path_alive(src, leaf);
            if (path.empty()) {
                // Should not happen in a connected alive tree
                remove_leaf(leaf);
                continue;
            }

            for (int i = 0; i + 1 < (int)path.size(); i++) {
                do_swap(path[i], path[i + 1]);
            }

            // Now leaf should match desired
            remove_leaf(leaf);
        }

        // No further action; component should match target now due to invariant.
    }

    // Output
    int k = (int)states.size() - 1;
    cout << k << "\n";
    for (auto &st : states) {
        for (int i = 0; i < n; i++) {
            if (i) cout << ' ';
            cout << st[i];
        }
        cout << "\n";
    }

    return 0;
}