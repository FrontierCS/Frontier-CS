#include <bits/stdc++.h>
using namespace std;

struct Solver {
    int n;
    vector<vector<int>> adj;
    vector<int> parent, depth, tin, tout, euler;
    int timer;

    void dfs(int v, int p) {
        parent[v] = (p == -1 ? 1 : p);
        depth[v] = (p == -1 ? 0 : depth[p] + 1);
        tin[v] = ++timer;
        euler[timer] = v;
        for (int to : adj[v]) {
            if (to == p) continue;
            dfs(to, v);
        }
        tout[v] = timer;
    }

    bool inSubtree(int v, int x) {
        return tin[x] <= tin[v] && tin[v] <= tout[x];
    }

    int query(int x) {
        cout << "? " << x << endl;
        cout.flush();
        int ans;
        if (!(cin >> ans)) exit(0);
        return ans;
    }

    void answer(int x) {
        cout << "! " << x << endl;
        cout.flush();
    }

    void solve_case() {
        cin >> n;
        adj.assign(n + 1, {});
        for (int i = 0; i < n - 1; ++i) {
            int u, v;
            cin >> u >> v;
            adj[u].push_back(v);
            adj[v].push_back(u);
        }
        parent.assign(n + 1, 0);
        depth.assign(n + 1, 0);
        tin.assign(n + 1, 0);
        tout.assign(n + 1, 0);
        euler.assign(n + 1, 0);
        timer = 0;
        dfs(1, -1);

        vector<char> possible(n + 1, 1);
        int cur_size = n;

        auto recompute_size = [&]() {
            int s = 0;
            for (int v = 1; v <= n; ++v) if (possible[v]) ++s;
            return s;
        };

        while (cur_size > 1) {
            vector<int> arr(n + 2, 0), pref(n + 2, 0);
            for (int v = 1; v <= n; ++v) if (possible[v]) arr[tin[v]] = 1;
            for (int i = 1; i <= n; ++i) pref[i] = pref[i - 1] + arr[i];

            int bestX = -1;
            int bestVal = INT_MAX;
            int bestDepth = INT_MAX;

            for (int x = 1; x <= n; ++x) {
                int c = pref[tout[x]] - pref[tin[x] - 1];
                if (c <= 0 || c >= cur_size) continue;
                int val = max(c, cur_size - c);
                if (val < bestVal || (val == bestVal && depth[x] < bestDepth)) {
                    bestVal = val;
                    bestDepth = depth[x];
                    bestX = x;
                }
            }

            if (bestX == -1) {
                // Fallback: choose any node with c == 1 or c == cur_size - 1
                // Ensure progress anyway
                for (int x = 1; x <= n; ++x) {
                    int c = pref[tout[x]] - pref[tin[x] - 1];
                    if (c > 0 && c < cur_size) {
                        int val = max(c, cur_size - c);
                        if (val < bestVal || (val == bestVal && depth[x] < bestDepth)) {
                            bestVal = val;
                            bestDepth = depth[x];
                            bestX = x;
                        }
                    }
                }
                if (bestX == -1) {
                    // As a last resort, pick any node in possible with c == 1 (a leaf in S)
                    for (int x = 1; x <= n; ++x) {
                        int c = pref[tout[x]] - pref[tin[x] - 1];
                        if (c == 1) { bestX = x; break; }
                    }
                    if (bestX == -1) {
                        // Pick any possible node except root if possible
                        for (int v = 1; v <= n; ++v) if (possible[v] && v != 1) { bestX = v; break; }
                        if (bestX == -1) {
                            for (int v = 1; v <= n; ++v) if (possible[v]) { bestX = v; break; }
                        }
                    }
                }
            }

            int ans = query(bestX);
            if (ans == 1) {
                for (int v = 1; v <= n; ++v) {
                    if (possible[v] && !inSubtree(v, bestX)) possible[v] = 0;
                }
            } else {
                vector<char> newPossible(n + 1, 0);
                for (int v = 1; v <= n; ++v) {
                    if (possible[v] && !inSubtree(v, bestX)) {
                        int u = (v == 1 ? 1 : parent[v]);
                        newPossible[u] = 1;
                    }
                }
                possible.swap(newPossible);
            }
            cur_size = recompute_size();
        }

        int res = 1;
        for (int v = 1; v <= n; ++v) if (possible[v]) { res = v; break; }
        answer(res);
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int t;
    if (!(cin >> t)) return 0;
    while (t--) {
        Solver s;
        s.solve_case();
    }
    return 0;
}