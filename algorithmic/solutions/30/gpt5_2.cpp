#include <bits/stdc++.h>
using namespace std;

int n, t;
vector<vector<int>> g;
vector<int> parent_, depth_, tin, tout, euler;
int timer_;

void dfs(int u, int p) {
    parent_[u] = p;
    tin[u] = ++timer_;
    euler[timer_] = u;
    for (int v : g[u]) {
        if (v == p) continue;
        depth_[v] = depth_[u] + 1;
        dfs(v, u);
    }
    tout[u] = timer_;
}

inline bool in_subtree(int u, int x) {
    return tin[x] <= tin[u] && tin[u] <= tout[x];
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    if (!(cin >> t)) return 0;
    while (t--) {
        cin >> n;
        g.assign(n + 1, {});
        for (int i = 0; i < n - 1; ++i) {
            int u, v;
            cin >> u >> v;
            g[u].push_back(v);
            g[v].push_back(u);
        }

        parent_.assign(n + 1, 0);
        depth_.assign(n + 1, 0);
        tin.assign(n + 1, 0);
        tout.assign(n + 1, 0);
        euler.assign(n + 1, 0);
        timer_ = 0;
        dfs(1, 0);

        vector<char> present(n + 1, 1);
        int present_total = n;

        auto build_pref = [&](vector<int>& pref) {
            vector<int> arr(n + 2, 0);
            for (int u = 1; u <= n; ++u) {
                if (present[u]) arr[tin[u]] = 1;
            }
            pref.assign(n + 2, 0);
            for (int i = 1; i <= n; ++i) pref[i] = pref[i - 1] + arr[i];
        };

        auto count_in_subtree = [&](const vector<int>& pref, int x) -> int {
            return pref[tout[x]] - pref[tin[x] - 1];
        };

        auto choose_x = [&](const vector<int>& pref) -> int {
            int best = -1;
            int bestScore = INT_MAX;
            for (int x = 1; x <= n; ++x) {
                int in = count_in_subtree(pref, x);
                int out = present_total - in;
                int score = max(in, out);
                if (score < bestScore) {
                    bestScore = score;
                    best = x;
                }
            }
            return best;
        };

        while (present_total > 1) {
            vector<int> pref;
            build_pref(pref);
            int x = choose_x(pref);

            cout << "? " << x << '\n';
            cout.flush();

            int r;
            if (!(cin >> r)) return 0;

            if (r == 1) {
                // Keep only nodes in subtree(x)
                for (int u = 1; u <= n; ++u) {
                    if (present[u] && !in_subtree(u, x)) {
                        present[u] = 0;
                        --present_total;
                    }
                }
            } else {
                // Map nodes not in subtree(x) to their parent (root stays)
                vector<char> newpresent(n + 1, 0);
                int new_total = 0;
                for (int u = 1; u <= n; ++u) {
                    if (!present[u]) continue;
                    if (!in_subtree(u, x)) {
                        int v = (u == 1 ? 1 : parent_[u]);
                        if (!newpresent[v]) {
                            newpresent[v] = 1;
                            ++new_total;
                        }
                    }
                }
                present.swap(newpresent);
                present_total = new_total;
            }
        }

        int ans = 1;
        for (int u = 1; u <= n; ++u) if (present[u]) { ans = u; break; }

        cout << "! " << ans << '\n';
        cout.flush();
    }

    return 0;
}