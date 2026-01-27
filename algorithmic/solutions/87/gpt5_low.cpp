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
    vector<vector<int>> g(n);
    for (int i = 0; i < m; ++i) {
        int u, v; cin >> u >> v; --u; --v;
        g[u].push_back(v);
        g[v].push_back(u);
    }

    auto bfs_path = [&](int s, int t, const vector<char>& forbid)->vector<int>{
        vector<int> par(n, -1);
        queue<int> q;
        if (forbid[s]) return {};
        par[s] = s;
        q.push(s);
        while (!q.empty()) {
            int u = q.front(); q.pop();
            if (u == t) break;
            for (int v : g[u]) if (par[v] == -1 && !forbid[v]) {
                par[v] = u;
                q.push(v);
            }
        }
        if (par[t] == -1) return {};
        vector<int> path;
        int u = t;
        while (u != par[u]) {
            path.push_back(u);
            u = par[u];
        }
        path.push_back(u);
        reverse(path.begin(), path.end());
        return path;
    };

    vector<vector<int>> states;
    states.push_back(cur);

    auto move_token_along = [&](const vector<int>& path){
        for (size_t i = 1; i < path.size(); ++i) {
            vector<int> nxt = cur;
            int from = path[i-1];
            int to = path[i];
            nxt[to] = cur[from];
            // others stay
            cur.swap(nxt);
            states.push_back(cur);
        }
    };

    auto all_matched = [&]()->bool{
        for (int i = 0; i < n; ++i) if (cur[i] != target[i]) return false;
        return true;
    };

    auto count_color = [&](int col)->int{
        int c=0; for(int i=0;i<n;++i) if(cur[i]==col) ++c; return c;
    };

    // heuristic iterative fixing
    int safety_iters = 0;
    while (!all_matched() && (int)states.size() <= 20000) {
        ++safety_iters;
        if (safety_iters > 500000) break; // safety
        // find a node to fix
        int v = -1;
        for (int i = 0; i < n; ++i) if (cur[i] != target[i]) { v = i; break; }
        if (v == -1) break;
        int b = target[v];
        // build candidate sources
        vector<int> sources;
        for (int i = 0; i < n; ++i) if (cur[i] == b) sources.push_back(i);
        // If no source of needed color (shouldn't happen as per guarantee), break
        if (sources.empty()) break;

        // Build forbid set: avoid already-correct nodes of opposite color,
        // and avoid eliminating last source of opposite color if needed later.
        vector<int> needLater(2,0);
        for (int i = 0; i < n; ++i) if (cur[i] != target[i]) needLater[target[i]]++;
        int other = 1 - b;
        int otherCount = count_color(other);
        vector<int> otherNodes;
        if (otherCount == 1 && needLater[other] > 0) {
            for (int i = 0; i < n; ++i) if (cur[i] == other) otherNodes.push_back(i);
        }
        // try with increasing relaxations
        bool done = false;
        for (int relax = 0; relax < 3 && !done; ++relax) {
            for (int s : sources) {
                vector<char> forbid(n, 0);
                if (relax <= 1) {
                    // forbid passing through nodes that are already correct with opposite color
                    for (int i = 0; i < n; ++i) {
                        if (relax == 0) {
                            if (cur[i] == target[i] && target[i] != b) forbid[i] = 1;
                        } else {
                            // slightly relax: only forbid those that are correct and not v itself
                            if (i != v && cur[i] == target[i] && target[i] != b) forbid[i] = 1;
                        }
                    }
                }
                // avoid killing the last other color source if needed later
                if (!otherNodes.empty()) forbid[otherNodes[0]] = 1;
                // never forbid source or destination
                forbid[s] = 0;
                forbid[v] = 0;

                auto path = bfs_path(s, v, forbid);
                if (!path.empty()) {
                    move_token_along(path);
                    done = true;
                    break;
                }
            }
        }
        if (!done) {
            // final attempt: no forbids, just any path from nearest source
            int bestS = -1;
            vector<int> bestPath;
            for (int s : sources) {
                vector<char> forbid(n, 0);
                auto path = bfs_path(s, v, forbid);
                if (!path.empty() && (bestS == -1 || path.size() < bestPath.size())) {
                    bestS = s;
                    bestPath = path;
                }
            }
            if (bestS != -1) {
                move_token_along(bestPath);
            } else {
                // should not happen if solution exists
                break;
            }
        }
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