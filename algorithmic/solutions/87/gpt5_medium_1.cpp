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
    vector<vector<int>> adj(n);
    for (int i = 0; i < m; ++i) {
        int u, v; cin >> u >> v; --u; --v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    auto bfs_path = [&](const vector<int>& cur, int v, int desired, const vector<int>& forbid)->vector<int> {
        // Find path from any node with color == desired to v avoiding forbidden nodes (forbid[x]=1 forbids)
        vector<int> src;
        vector<int> vis(n, 0), par(n, -1);
        queue<int> q;
        for (int i = 0; i < n; ++i) {
            if (cur[i] == desired && !forbid[i]) {
                q.push(i);
                vis[i] = 1;
                par[i] = -1;
            }
        }
        if (forbid[v]) return {};
        while (!q.empty()) {
            int x = q.front(); q.pop();
            if (x == v) break;
            for (int y : adj[x]) {
                if (!vis[y] && !forbid[y]) {
                    vis[y] = 1;
                    par[y] = x;
                    q.push(y);
                }
            }
        }
        if (!vis[v]) return {};
        vector<int> path;
        int x = v;
        while (x != -1) {
            path.push_back(x);
            x = par[x];
        }
        reverse(path.begin(), path.end());
        return path; // from source to v
    };

    // Simulate propagation along a path p[0..k] by k steps where at each step j, p[j] copies p[j-1].
    auto apply_path = [&](vector<vector<int>>& states, vector<int>& cur, const vector<int>& path) {
        int k = (int)path.size() - 1;
        for (int step = 1; step <= k; ++step) {
            vector<int> nxt = cur;
            for (int j = k; j >= 1; --j) {
                nxt[path[j]] = cur[path[j-1]];
            }
            // other nodes keep
            states.push_back(nxt);
            cur.swap(nxt);
        }
    };

    // Identify connected components of the graph
    vector<int> compId(n, -1);
    int comps = 0;
    for (int i = 0; i < n; ++i) if (compId[i] == -1) {
        queue<int> q;
        q.push(i); compId[i] = comps;
        while (!q.empty()) {
            int u = q.front(); q.pop();
            for (int v : adj[u]) if (compId[v] == -1) {
                compId[v] = comps;
                q.push(v);
            }
        }
        ++comps;
    }

    vector<int> cur = init;
    vector<vector<int>> states;
    states.push_back(cur);

    // Greedy iterative improvement with basic safeguards
    const int MAX_STEPS = 20000;
    int guard = 0;
    // For each component, ensure at least one node with each color if target in comp requires that color
    vector<array<int,2>> needColor(comps, {0,0});
    for (int i = 0; i < n; ++i) needColor[compId[i]][target[i]] = 1;

    auto exists_color_in_comp = [&](int cid, int color)->bool {
        for (int i = 0; i < n; ++i) if (compId[i]==cid && cur[i]==color) return true;
        return false;
    };

    // Main loop
    while (cur != target && (int)states.size() - 1 < MAX_STEPS) {
        // Pick a node to fix with shortest path from a current source of desired color.
        int best_v = -1;
        vector<int> best_path;
        int best_len = INT_MAX;
        // forbid array to preserve at least one source of opposite color per component if needed
        vector<int> forbid(n, 0);
        for (int cid = 0; cid < comps; ++cid) {
            for (int col = 0; col < 2; ++col) {
                if (needColor[cid][col]) {
                    // ensure we don't kill last of col in this component by forbidding one representative if only one exists
                    int count = 0, rep = -1;
                    for (int i = 0; i < n; ++i) if (compId[i]==cid && cur[i]==col) { ++count; rep = i; }
                    if (count == 0) {
                        // No source exists but needed later: try to re-create by random toggle - but impossible; break
                    }
                    if (count == 1) {
                        forbid[rep] = 1;
                    }
                }
            }
        }
        for (int v = 0; v < n; ++v) {
            if (cur[v] == target[v]) continue;
            int desired = target[v];
            vector<int> path = bfs_path(cur, v, desired, forbid);
            if (path.empty()) continue;
            int len = (int)path.size() - 1;
            if (len < best_len) {
                best_len = len;
                best_v = v;
                best_path = move(path);
                if (best_len == 0) break;
            }
        }
        if (best_v == -1) {
            // Relax forbids and try again
            bool progressed = false;
            for (int v = 0; v < n; ++v) {
                if (cur[v] == target[v]) continue;
                int desired = target[v];
                vector<int> emptyForbid(n,0);
                vector<int> path = bfs_path(cur, v, desired, emptyForbid);
                if (path.empty()) continue;
                apply_path(states, cur, path);
                progressed = true;
                break;
            }
            if (!progressed) break;
        } else {
            apply_path(states, cur, best_path);
        }
        if ((int)states.size() - 1 >= MAX_STEPS) break;
        guard++;
        if (guard > MAX_STEPS) break;
    }

    // If still not equal, attempt one last pass trying all nodes without forbids
    while (cur != target && (int)states.size() - 1 < MAX_STEPS) {
        bool any = false;
        for (int v = 0; v < n; ++v) {
            if (cur[v] == target[v]) continue;
            int desired = target[v];
            vector<int> forbidEmpty(n,0);
            vector<int> path = bfs_path(cur, v, desired, forbidEmpty);
            if (path.empty()) continue;
            apply_path(states, cur, path);
            any = true;
            if (cur == target || (int)states.size() - 1 >= MAX_STEPS) break;
        }
        if (!any) break;
    }

    if (cur != target) {
        // As a fallback, if we couldn't reach exact target within limit, just append target if equal to current (it won't be)
        // Ensure output has at least initial
    }

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