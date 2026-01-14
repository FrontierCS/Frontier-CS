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
        int u, v; cin >> u >> v;
        --u; --v;
        g[u].push_back(v);
        g[v].push_back(u);
    }

    // Compute connected components
    vector<int> comp_id(n, -1);
    vector<vector<int>> comp_nodes;
    int comp_cnt = 0;
    for (int i = 0; i < n; ++i) {
        if (comp_id[i] != -1) continue;
        queue<int> q;
        q.push(i);
        comp_id[i] = comp_cnt;
        comp_nodes.push_back({});
        comp_nodes.back().push_back(i);
        while (!q.empty()) {
            int u = q.front(); q.pop();
            for (int v : g[u]) {
                if (comp_id[v] == -1) {
                    comp_id[v] = comp_cnt;
                    comp_nodes.back().push_back(v);
                    q.push(v);
                }
            }
        }
        comp_cnt++;
    }

    // For each component, check if target has both colors
    vector<array<bool,2>> comp_target_has(comp_cnt, {false, false});
    for (int i = 0; i < n; ++i) {
        comp_target_has[comp_id[i]][target[i]] = true;
    }

    const int MAX_STEPS = 20000;

    vector<vector<int>> states;
    vector<int> cur = init;
    states.push_back(cur);

    auto bfs_from_color = [&](int color, vector<int>& dist, vector<int>& par) {
        const int INF = 1e9;
        dist.assign(n, INF);
        par.assign(n, -1);
        queue<int> q;
        for (int i = 0; i < n; ++i) {
            if (cur[i] == color) {
                dist[i] = 0;
                par[i] = -1;
                q.push(i);
            }
        }
        while (!q.empty()) {
            int u = q.front(); q.pop();
            for (int v : g[u]) {
                if (dist[v] > dist[u] + 1) {
                    dist[v] = dist[u] + 1;
                    par[v] = u;
                    q.push(v);
                }
            }
        }
    };

    auto reconstruct_path = [&](int u, const vector<int>& par) {
        vector<int> path;
        int x = u;
        while (x != -1) {
            path.push_back(x);
            x = par[x];
        }
        reverse(path.begin(), path.end()); // from source to u
        return path;
    };

    auto equal_state = [&](const vector<int>& a, const vector<int>& b) {
        for (int i = 0; i < n; ++i) if (a[i] != b[i]) return false;
        return true;
    };

    int steps = 0;
    while (!equal_state(cur, target) && steps < MAX_STEPS) {
        vector<int> dist0, par0, dist1, par1;
        bfs_from_color(0, dist0, par0);
        bfs_from_color(1, dist1, par1);

        // Count colors per component
        vector<array<int,2>> comp_count(comp_cnt);
        for (int c = 0; c < comp_cnt; ++c) comp_count[c] = {0, 0};
        for (int i = 0; i < n; ++i) comp_count[comp_id[i]][cur[i]]++;

        const int INF = 1e9;
        int bestDist = INF;
        int bestColor = -1;
        vector<int> bestPath;

        // Try to find a safe candidate with minimal distance
        for (int i = 0; i < n; ++i) {
            if (cur[i] == target[i]) continue;
            int c = target[i];
            int d = (c == 0 ? dist0[i] : dist1[i]);
            if (d >= INF) continue;
            const vector<int>& par = (c == 0 ? par0 : par1);
            vector<int> path = reconstruct_path(i, par);
            int comp = comp_id[i];
            bool requireBoth = comp_target_has[comp][0] && comp_target_has[comp][1];

            bool safe = true;
            if (requireBoth) {
                int opp = 1 - c;
                int countOppInComp = comp_count[comp][opp];
                if (countOppInComp > 0) {
                    int countOppOnPath = 0;
                    for (int v : path) if (cur[v] == opp) countOppOnPath++;
                    if (countOppOnPath == countOppInComp) safe = false;
                }
            }

            if (!safe) continue;

            if (d < bestDist) {
                bestDist = d;
                bestColor = c;
                bestPath = move(path);
            }
        }

        // If no safe candidate found, try without the safety constraint (only if it's safe to do so)
        if (bestDist >= INF) {
            for (int i = 0; i < n; ++i) {
                if (cur[i] == target[i]) continue;
                int c = target[i];
                int d = (c == 0 ? dist0[i] : dist1[i]);
                if (d >= INF) continue;
                const vector<int>& par = (c == 0 ? par0 : par1);
                vector<int> path = reconstruct_path(i, par);
                int comp = comp_id[i];
                bool requireBoth = comp_target_has[comp][0] && comp_target_has[comp][1];
                // If both colors required in this component and the opposite color count is zero,
                // we are already in an impossible situation, but proceed anyway to finish.
                // Otherwise, check if we would eliminate the last opposite color; if so, skip.
                bool unsafe_eliminate = false;
                if (requireBoth) {
                    int opp = 1 - c;
                    int countOppInComp = comp_count[comp][opp];
                    if (countOppInComp > 0) {
                        int countOppOnPath = 0;
                        for (int v : path) if (cur[v] == opp) countOppOnPath++;
                        if (countOppOnPath == countOppInComp) unsafe_eliminate = true;
                    }
                }
                if (unsafe_eliminate) continue;

                if (d < bestDist) {
                    bestDist = d;
                    bestColor = c;
                    bestPath = move(path);
                }
            }
        }

        if (bestDist >= INF || bestPath.empty()) {
            // No progress possible
            break;
        }

        // Perform the transformations along bestPath to set nodes to bestColor
        for (size_t idx = 1; idx < bestPath.size(); ++idx) {
            int v = bestPath[idx];
            if (cur[v] != bestColor) {
                vector<int> next = cur;
                next[v] = bestColor;
                states.push_back(next);
                cur.swap(next);
                steps++;
                if (steps >= MAX_STEPS) break;
            }
        }
    }

    // Output
    int k = (int)states.size() - 1;
    cout << k << "\n";
    for (const auto &st : states) {
        for (int i = 0; i < n; ++i) {
            if (i) cout << ' ';
            cout << st[i];
        }
        cout << "\n";
    }

    return 0;
}