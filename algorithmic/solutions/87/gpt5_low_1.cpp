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
        int u, v; cin >> u >> v; --u; --v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }
    // Compute connected components
    vector<int> comp(n, -1);
    int comps = 0;
    for (int i = 0; i < n; ++i) if (comp[i] == -1) {
        queue<int> q; q.push(i); comp[i] = comps;
        while (!q.empty()) {
            int u = q.front(); q.pop();
            for (int v : adj[u]) if (comp[v] == -1) {
                comp[v] = comps; q.push(v);
            }
        }
        comps++;
    }

    // States output
    vector<vector<int>> states;
    states.push_back(cur);

    auto all_done = [&]() {
        for (int i = 0; i < n; ++i) if (cur[i] != target[i]) return false;
        return true;
    };

    auto recompute_counts = [&](vector<array<int,2>>& cnt_color_comp,
                                vector<array<int,2>>& remaining_need_comp) {
        cnt_color_comp.assign(comps, {0,0});
        remaining_need_comp.assign(comps, {0,0});
        for (int i = 0; i < n; ++i) {
            cnt_color_comp[comp[i]][cur[i]]++;
            if (cur[i] != target[i]) {
                remaining_need_comp[comp[i]][target[i]]++;
            }
        }
    };

    auto bfs_path = [&](int s, int t)->vector<int> {
        vector<int> par(n, -1);
        queue<int> q; q.push(s); par[s] = s;
        while (!q.empty()) {
            int u = q.front(); q.pop();
            if (u == t) break;
            for (int v : adj[u]) if (par[v] == -1) {
                par[v] = u; q.push(v);
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

    // Main loop
    int maxSteps = 20000;
    while (!all_done()) {
        vector<array<int,2>> cnt_color_comp, remaining_need_comp;
        recompute_counts(cnt_color_comp, remaining_need_comp);

        // Safety check (should not happen if problem guarantees solvable and our strategy preserves)
        bool impossible = false;
        for (int c = 0; c < comps; ++c) {
            for (int col = 0; col < 2; ++col) {
                if (remaining_need_comp[c][col] > 0 && cnt_color_comp[c][col] == 0) {
                    // Cannot create a missing color within a component
                    impossible = true;
                }
            }
        }
        if (impossible) break;

        int chosen_v = -1, chosen_s = -1, tcol = -1;

        // Priority: per-component safeguard when a color count == 1 but still needed
        bool picked = false;
        for (int cid = 0; cid < comps && !picked; ++cid) {
            for (int col = 0; col < 2 && !picked; ++col) {
                if (remaining_need_comp[cid][col] > 0 && cnt_color_comp[cid][col] == 1) {
                    // Find the sole source s in component cid with color col
                    int s = -1;
                    for (int i = 0; i < n; ++i) if (comp[i] == cid && cur[i] == col) { s = i; break; }
                    if (s == -1) continue; // shouldn't happen
                    // Find nearest v in cid with target col and cur[v] != col
                    vector<int> dist(n, -1);
                    queue<int> q; q.push(s); dist[s] = 0;
                    int best_v = -1, best_d = INT_MAX;
                    while (!q.empty()) {
                        int u = q.front(); q.pop();
                        if (comp[u] != cid) continue;
                        if (target[u] == col && cur[u] != col) {
                            if (dist[u] < best_d) {
                                best_d = dist[u]; best_v = u;
                            }
                        }
                        for (int w : adj[u]) if (dist[w] == -1) {
                            dist[w] = dist[u] + 1; q.push(w);
                        }
                    }
                    if (best_v == -1) continue; // no need? but remaining_need says exists; may be unreachable? shouldn't
                    chosen_s = s; chosen_v = best_v; tcol = col; picked = true;
                }
            }
        }

        if (!picked) {
            // Pick any vertex not matching
            int v = -1;
            for (int i = 0; i < n; ++i) if (cur[i] != target[i]) { v = i; break; }
            if (v == -1) break; // done
            tcol = target[v];
            int cid = comp[v];
            // choose nearest source s in same component with color tcol
            vector<int> dist(n, -1);
            queue<int> q; q.push(v); dist[v] = 0;
            int best_s = -1, best_d = INT_MAX;
            // BFS from v to find nearest s with cur==tcol
            while (!q.empty()) {
                int u = q.front(); q.pop();
                if (comp[u] != cid) continue;
                if (cur[u] == tcol) {
                    best_s = u; best_d = dist[u]; break;
                }
                for (int w : adj[u]) if (dist[w] == -1) {
                    dist[w] = dist[u] + 1; q.push(w);
                }
            }
            if (best_s == -1) {
                // no source in this component; should not happen if solvable and preserved
                // try next unmatched vertex in another component
                bool found = false;
                for (int i = 0; i < n && !found; ++i) if (cur[i] != target[i]) {
                    int vv = i; int cc = target[vv]; int cid2 = comp[vv];
                    vector<int> dist2(n, -1);
                    queue<int> q2; q2.push(vv); dist2[vv] = 0;
                    int bs = -1;
                    while (!q2.empty()) {
                        int u = q2.front(); q2.pop();
                        if (comp[u] != cid2) continue;
                        if (cur[u] == cc) { bs = u; break; }
                        for (int w : adj[u]) if (dist2[w] == -1) {
                            dist2[w] = dist2[u] + 1; q2.push(w);
                        }
                    }
                    if (bs != -1) {
                        v = vv; tcol = cc; best_s = bs; found = true;
                    }
                }
            }
            chosen_v = v; chosen_s = (int) (best_s == -1 ? v : best_s);
        }

        if (chosen_v == -1 || chosen_s == -1) break;

        // Build path from chosen_s to chosen_v
        vector<int> path = bfs_path(chosen_s, chosen_v);
        if (path.empty()) {
            // Shouldn't happen in connected component
            break;
        }

        // Recolor along path: for each next node, if it's not already tcol, set it and record state.
        for (size_t i = 1; i < path.size(); ++i) {
            int u = path[i];
            if (cur[u] == tcol) continue;
            cur[u] = tcol;
            states.push_back(cur);
            if ((int)states.size()-1 > maxSteps) break;
        }
        if ((int)states.size()-1 > maxSteps) break;
    }

    int k = (int)states.size() - 1;
    if (k < 0) k = 0;
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