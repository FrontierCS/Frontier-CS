#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, m;
    if (!(cin >> n >> m)) return 0;
    vector<int> cur(n), target(n);
    for (int i = 0; i < n; ++i) cin >> cur[i];
    for (int i = 0; i < n; ++i) cin >> target[i];
    vector<vector<int>> adj(n);
    for (int i = 0; i < m; ++i) {
        int u, v; cin >> u >> v;
        --u; --v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    // Build connected components
    vector<int> comp(n, -1);
    int compCnt = 0;
    for (int i = 0; i < n; ++i) if (comp[i] == -1) {
        queue<int> q; q.push(i); comp[i] = compCnt;
        while (!q.empty()) {
            int u = q.front(); q.pop();
            for (int v : adj[u]) if (comp[v] == -1) {
                comp[v] = compCnt; q.push(v);
            }
        }
        compCnt++;
    }

    // Determine reservoirs per component for colors that appear in target of that component
    vector<int> reservoir0(compCnt, -1), reservoir1(compCnt, -1);
    for (int cId = 0; cId < compCnt; ++cId) {
        bool need0 = false, need1 = false;
        for (int i = 0; i < n; ++i) if (comp[i] == cId) {
            if (target[i] == 0) need0 = true;
            if (target[i] == 1) need1 = true;
        }
        if (need0) {
            // Prefer node with initial 0 and target 0
            int pick = -1;
            for (int i = 0; i < n; ++i) if (comp[i] == cId && cur[i] == 0 && target[i] == 0) { pick = i; break; }
            if (pick == -1) {
                for (int i = 0; i < n; ++i) if (comp[i] == cId && cur[i] == 0) { pick = i; break; }
            }
            reservoir0[cId] = pick;
        }
        if (need1) {
            int pick = -1;
            for (int i = 0; i < n; ++i) if (comp[i] == cId && cur[i] == 1 && target[i] == 1) { pick = i; break; }
            if (pick == -1) {
                for (int i = 0; i < n; ++i) if (comp[i] == cId && cur[i] == 1) { pick = i; break; }
            }
            reservoir1[cId] = pick;
        }
    }

    // Sequence of states
    vector<vector<int>> states;
    states.push_back(cur);

    auto apply_path = [&](const vector<int>& path){
        // apply step-by-step: for each edge path[i-1] -> path[i], set path[i] := cur[path[i-1]]
        for (size_t i = 1; i < path.size(); ++i) {
            vector<int> next = cur;
            int from = path[i-1], to = path[i];
            next[to] = cur[from];
            cur.swap(next);
            states.push_back(cur);
            if ((int)states.size() > 20050) return; // safety
        }
    };

    auto bfs_path = [&](int dest, int color, const vector<char>& protect, bool respect_protect) -> vector<int> {
        // Multi-source BFS from all nodes with cur[u]==color to dest
        vector<int> parent(n, -1);
        vector<char> vis(n, 0);
        queue<int> q;
        for (int i = 0; i < n; ++i) {
            if (cur[i] == color) {
                q.push(i);
                vis[i] = 1;
                parent[i] = -1;
            }
        }
        if (!vis[dest] && q.empty()) return {}; // no sources
        while (!q.empty()) {
            int u = q.front(); q.pop();
            if (u == dest) break;
            for (int v : adj[u]) if (!vis[v]) {
                bool allow = true;
                if (respect_protect) {
                    if (v != dest && protect[v] && cur[v] != color) allow = false;
                }
                if (allow) {
                    vis[v] = 1;
                    parent[v] = u;
                    q.push(v);
                }
            }
        }
        if (!vis[dest]) return {};
        vector<int> path;
        int x = dest;
        while (x != -1) {
            path.push_back(x);
            x = parent[x];
        }
        reverse(path.begin(), path.end());
        return path;
    };

    // Protect flags: reservoirs and locked nodes
    vector<char> protect(n, 0);
    for (int i = 0; i < n; ++i) {
        int cId = comp[i];
        if (reservoir0[cId] == i || reservoir1[cId] == i) protect[i] = 1;
    }
    vector<char> locked(n, 0); // nodes we consider done (match target)

    auto main_fix_loop = [&](bool use_reservoir_protect){
        // Repeatedly fix nodes to reach target, respecting protection if use_reservoir_protect==true
        // Protection array includes both reservoirs and locked nodes.
        while (true) {
            vector<int> tofix;
            for (int i = 0; i < n; ++i) if (cur[i] != target[i]) tofix.push_back(i);
            if (tofix.empty()) break;
            // mark locked as protection
            vector<char> prot = protect;
            for (int i = 0; i < n; ++i) if (locked[i]) prot[i] = 1;
            int best_v = -1;
            vector<int> best_path;
            int best_len = INT_MAX;
            // Try avoid changing protected nodes
            for (int v : tofix) {
                int c = target[v];
                auto path = bfs_path(v, c, prot, use_reservoir_protect);
                if (!path.empty() && (int)path.size() < best_len) {
                    best_len = (int)path.size();
                    best_path = path;
                    best_v = v;
                }
            }
            if (best_v == -1) {
                // Ignore protection and find any path
                for (int v : tofix) {
                    int c = target[v];
                    auto path = bfs_path(v, c, prot, false);
                    if (!path.empty() && (int)path.size() < best_len) {
                        best_len = (int)path.size();
                        best_path = path;
                        best_v = v;
                    }
                }
                if (best_v == -1) {
                    // Should not happen (guaranteed solvable)
                    break;
                }
            }
            apply_path(best_path);
            // update locks: lock destination if now matches target
            for (int i = 0; i < n; ++i) {
                if (cur[i] == target[i]) locked[i] = 1;
            }
            if ((int)states.size() > 20050) break;
        }
    };

    // Initial lock those already matching
    for (int i = 0; i < n; ++i) if (cur[i] == target[i]) locked[i] = 1;

    // Main loop with reservoir protection
    main_fix_loop(true);

    // Now recolor reservoirs if needed (may temporarily disturb others)
    for (int cId = 0; cId < compCnt; ++cId) {
        int r0 = reservoir0[cId];
        int r1 = reservoir1[cId];
        if (r0 != -1 && cur[r0] != target[r0]) {
            vector<char> prot = protect; // keep reservoirs protected (including r0), but we'll ignore protection to ensure path exists
            auto path = bfs_path(r0, target[r0], prot, false);
            if (!path.empty()) apply_path(path);
        }
        if (r1 != -1 && cur[r1] != target[r1]) {
            vector<char> prot = protect;
            auto path = bfs_path(r1, target[r1], prot, false);
            if (!path.empty()) apply_path(path);
        }
    }

    // Final repair without reservoir protection (allow changing any non-locked as needed)
    // Reset locks according to current state
    fill(locked.begin(), locked.end(), 0);
    for (int i = 0; i < n; ++i) if (cur[i] == target[i]) locked[i] = 1;
    // Do a final pass with protection applied only to already correct nodes to minimize disturbance
    main_fix_loop(false);

    // Ensure last state equals target; if not, try a final strict loop
    if (cur != target) {
        // Try once more with protection based on current locks
        fill(locked.begin(), locked.end(), 0);
        for (int i = 0; i < n; ++i) if (cur[i] == target[i]) locked[i] = 1;
        main_fix_loop(false);
    }

    // Output
    int k = (int)states.size() - 1;
    cout << k << "\n";
    for (auto &st : states) {
        for (int i = 0; i < n; ++i) {
            if (i) cout << ' ';
            cout << st[i];
        }
        cout << "\n";
    }

    return 0;
}