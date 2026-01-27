#include <bits/stdc++.h>
using namespace std;

struct Edge {
    int a, b;
};

static inline void die() {
    exit(0);
}

struct Interactor {
    vector<char> blocked; // 1..m
    Interactor(int m = 0) { reset(m); }

    void reset(int m) { blocked.assign(m + 1, 0); }

    void blockEdge(int id) {
        if (!blocked[id]) {
            cout << "- " << id << '\n';
            cout.flush();
            blocked[id] = 1;
        }
    }

    void unblockEdge(int id) {
        if (blocked[id]) {
            cout << "+ " << id << '\n';
            cout.flush();
            blocked[id] = 0;
        }
    }

    int querySingle(int v) {
        cout << "? 1 " << v << '\n';
        cout.flush();
        int res;
        if (!(cin >> res)) die();
        if (res == -1) die();
        return res;
    }

    int verdict() {
        int res;
        if (!(cin >> res)) die();
        if (res == -1) die();
        return res;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int t;
    if (!(cin >> t)) return 0;

    for (int tc = 0; tc < t; tc++) {
        int n, m;
        cin >> n >> m;

        vector<Edge> edges(m + 1);
        vector<vector<pair<int,int>>> adj(n + 1);
        for (int i = 1; i <= m; i++) {
            int a, b;
            cin >> a >> b;
            edges[i] = {a, b};
            adj[a].push_back({b, i});
            adj[b].push_back({a, i});
        }

        Interactor it(m);

        // Block all edges first
        for (int i = 1; i <= m; i++) it.blockEdge(i);

        // Find s (with all edges blocked, only s can reach itself)
        int s = -1;
        for (int v = 1; v <= n; v++) {
            int ans = it.querySingle(v);
            if (ans == 1) { s = v; break; }
        }
        if (s == -1) die();

        vector<int> repaired(m + 1, -1);
        vector<char> isTreeEdge(m + 1, 0);
        vector<char> tested(m + 1, 0);

        vector<char> reached(n + 1, 0);
        vector<int> parent(n + 1, 0), parentEdge(n + 1, 0), depth(n + 1, 0);
        reached[s] = 1;

        deque<int> q;
        q.push_back(s);

        int reachedCnt = 1;

        // Build a repaired spanning tree by exploring from s
        while (!q.empty()) {
            int u = q.front();
            q.pop_front();

            for (auto [v, id] : adj[u]) {
                if (reached[v]) continue;
                if (tested[id]) continue;
                tested[id] = 1;

                it.unblockEdge(id);
                int ans = it.querySingle(v);
                if (ans == 1) {
                    repaired[id] = 1;
                    isTreeEdge[id] = 1;
                    reached[v] = 1;
                    reachedCnt++;

                    parent[v] = u;
                    parentEdge[v] = id;
                    depth[v] = depth[u] + 1;

                    q.push_back(v);
                    // keep edge unblocked
                } else {
                    repaired[id] = 0;
                    it.blockEdge(id);
                }
            }
        }

        // Should have reached all vertices
        if (reachedCnt != n) die();

        // Prepare rooted tree structure at s
        vector<vector<int>> children(n + 1);
        for (int v = 1; v <= n; v++) {
            if (v == s) continue;
            children[parent[v]].push_back(v);
        }

        // Euler tour tin/tout
        vector<int> tin(n + 1, 0), tout(n + 1, 0), idx(n + 1, 0);
        int timer = 0;
        vector<int> st;
        st.push_back(s);
        while (!st.empty()) {
            int v = st.back();
            if (idx[v] == 0) tin[v] = ++timer;
            if (idx[v] < (int)children[v].size()) {
                int to = children[v][idx[v]++];
                st.push_back(to);
            } else {
                tout[v] = timer;
                st.pop_back();
            }
        }

        auto isAncestor = [&](int u, int v) -> bool {
            return tin[u] <= tin[v] && tout[v] <= tout[u];
        };

        // All non-tree edges are currently blocked (never unblocked),
        // except those tested during tree building (re-blocked if not repaired).
        // Tree edges are currently unblocked.

        // Determine repaired status for remaining unknown edges
        for (int id = 1; id <= m; id++) {
            if (isTreeEdge[id]) continue;
            if (repaired[id] != -1) continue;

            int u = edges[id].a;
            int v = edges[id].b;

            int x;
            if (isAncestor(u, v)) x = v;
            else if (isAncestor(v, u)) x = u;
            else x = (depth[u] > depth[v] ? u : v);

            // x must not be s
            if (x == s) die();
            int cutEdge = parentEdge[x];
            if (cutEdge <= 0) die();

            it.blockEdge(cutEdge);
            it.unblockEdge(id);

            int ans = it.querySingle(x);
            repaired[id] = (ans == 1 ? 1 : 0);

            it.blockEdge(id);
            it.unblockEdge(cutEdge);
        }

        // Any still unknown edges (shouldn't happen) mark as not repaired
        for (int id = 1; id <= m; id++) if (repaired[id] == -1) repaired[id] = 0;

        cout << "!";
        for (int id = 1; id <= m; id++) cout << ' ' << repaired[id];
        cout << '\n';
        cout.flush();

        int ok = it.verdict();
        if (ok != 1) die();
    }

    return 0;
}