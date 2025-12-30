#include <bits/stdc++.h>
using namespace std;

struct Solver {
    int n;
    vector<vector<int>> adj, children;
    vector<int> parent, depth, tin, tout, order;
    vector<vector<int>> up;
    int LOG = 13;

    int timer = 0;

    void build_rooted_tree() {
        parent.assign(n + 1, 1);
        depth.assign(n + 1, 0);
        tin.assign(n + 1, 0);
        tout.assign(n + 1, 0);
        children.assign(n + 1, {});
        order.clear();
        order.reserve(n);

        up.assign(LOG + 1, vector<int>(n + 1, 1));

        timer = 0;
        stack<pair<int,int>> st;
        st.push({1, 0});
        parent[1] = 1;
        depth[1] = 0;
        up[0][1] = 1;

        while (!st.empty()) {
            int u = st.top().first;
            int &idx = st.top().second;

            if (idx == 0) {
                tin[u] = ++timer;
                order.push_back(u);
            }
            if (idx < (int)adj[u].size()) {
                int v = adj[u][idx++];
                if (v == parent[u]) continue;
                parent[v] = u;
                depth[v] = depth[u] + 1;
                up[0][v] = u;
                children[u].push_back(v);
                st.push({v, 0});
            } else {
                tout[u] = timer;
                st.pop();
            }
        }

        for (int j = 1; j <= LOG; j++) {
            for (int v = 1; v <= n; v++) {
                up[j][v] = up[j - 1][ up[j - 1][v] ];
            }
        }
    }

    inline bool is_in_subtree(int u, int x) const {
        return tin[x] <= tin[u] && tin[u] <= tout[x];
    }

    int lca(int a, int b) const {
        if (depth[a] < depth[b]) swap(a, b);
        int diff = depth[a] - depth[b];
        for (int j = LOG; j >= 0; j--) {
            if (diff & (1 << j)) a = up[j][a];
        }
        if (a == b) return a;
        for (int j = LOG; j >= 0; j--) {
            if (up[j][a] != up[j][b]) {
                a = up[j][a];
                b = up[j][b];
            }
        }
        return parent[a];
    }

    void solve_case() {
        vector<int> cand(n);
        iota(cand.begin(), cand.end(), 1);

        vector<int> cnt(n + 1, 0), subSum(n + 1, 0);
        vector<char> groupHas(n + 1, 0);
        vector<int> groupLca(n + 1, 0), lcaCnt(n + 1, 0), goodSum(n + 1, 0);

        int queries = 0;
        while ((int)cand.size() > 1) {
            if (queries >= 160) exit(0);

            // cnt
            fill(cnt.begin(), cnt.end(), 0);
            for (int u : cand) cnt[u] = 1;

            // subSum (yes-case sizes)
            fill(subSum.begin(), subSum.end(), 0);
            for (int i = (int)order.size() - 1; i >= 0; i--) {
                int u = order[i];
                int s = cnt[u];
                for (int v : children[u]) s += subSum[v];
                subSum[u] = s;
            }

            // groups by parent and their LCA
            fill(groupHas.begin(), groupHas.end(), 0);
            int P_total = 0;
            for (int u : cand) {
                int p = (u == 1 ? 1 : parent[u]);
                if (!groupHas[p]) {
                    groupHas[p] = 1;
                    groupLca[p] = u;
                    P_total++;
                } else {
                    groupLca[p] = lca(groupLca[p], u);
                }
            }

            // lcaCnt
            fill(lcaCnt.begin(), lcaCnt.end(), 0);
            for (int p = 1; p <= n; p++) {
                if (groupHas[p]) lcaCnt[groupLca[p]]++;
            }

            // goodSum: number of groups fully contained in subtree(x)
            fill(goodSum.begin(), goodSum.end(), 0);
            for (int i = (int)order.size() - 1; i >= 0; i--) {
                int u = order[i];
                int s = lcaCnt[u];
                for (int v : children[u]) s += goodSum[v];
                goodSum[u] = s;
            }

            // choose best query node
            int best = -1;
            int bestWorst = INT_MAX;

            for (int x = 2; x <= n; x++) {
                int yes = subSum[x];
                if (yes == (int)cand.size()) continue; // would not reduce
                int no = P_total - goodSum[x];
                int worst = max(yes, no);

                if (worst < bestWorst ||
                    (worst == bestWorst && depth[x] < depth[best]) ||
                    (worst == bestWorst && depth[x] == depth[best] && x < best)) {
                    bestWorst = worst;
                    best = x;
                }
            }
            if (best == -1) {
                // fallback: pick any node not equal to 1, prefer deeper candidate if possible
                best = 2;
                for (int u : cand) if (u != 1 && depth[u] > depth[best]) best = u;
            }

            cout << "? " << best << "\n" << flush;
            int ans;
            if (!(cin >> ans)) exit(0);
            if (ans == -1) exit(0);
            queries++;

            vector<int> newCand;
            if (ans == 1) {
                newCand.reserve(subSum[best]);
                for (int u : cand) {
                    if (is_in_subtree(u, best)) newCand.push_back(u);
                }
            } else {
                vector<char> seen(n + 1, 0);
                for (int u : cand) {
                    if (!is_in_subtree(u, best)) {
                        int p = (u == 1 ? 1 : parent[u]);
                        if (!seen[p]) {
                            seen[p] = 1;
                            newCand.push_back(p);
                        }
                    }
                }
            }
            if (newCand.empty()) newCand.push_back(1);
            cand.swap(newCand);
        }

        cout << "! " << cand[0] << "\n" << flush;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int t;
    if (!(cin >> t)) return 0;
    while (t--) {
        Solver s;
        cin >> s.n;
        s.adj.assign(s.n + 1, {});
        for (int i = 0; i < s.n - 1; i++) {
            int u, v;
            cin >> u >> v;
            s.adj[u].push_back(v);
            s.adj[v].push_back(u);
        }
        s.build_rooted_tree();
        s.solve_case();
    }
    return 0;
}