#include <bits/stdc++.h>
using namespace std;

static inline void die() {
    exit(0);
}

struct Interactor {
    int n = 0, m = 0;
    vector<char> blocked; // 1..m

    void init(int n_, int m_) {
        n = n_;
        m = m_;
        blocked.assign(m + 1, 0);
    }

    void blockRoad(int id) {
        if (id < 1 || id > m) die();
        if (blocked[id]) return;
        cout << "- " << id << "\n";
        cout.flush();
        blocked[id] = 1;
    }

    void unblockRoad(int id) {
        if (id < 1 || id > m) die();
        if (!blocked[id]) return;
        cout << "+ " << id << "\n";
        cout.flush();
        blocked[id] = 0;
    }

    int queryVertex(int v) {
        cout << "? 1 " << v << "\n";
        cout.flush();
        int r;
        if (!(cin >> r)) die();
        if (r == -1) die();
        return r;
    }

    int answer(const vector<int>& ans) {
        cout << "!";
        for (int i = 1; i <= m; i++) cout << " " << ans[i];
        cout << "\n";
        cout.flush();
        int r;
        if (!(cin >> r)) die();
        if (r == -1) die();
        return r;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int t;
    if (!(cin >> t)) return 0;

    Interactor it;

    while (t--) {
        int n, m;
        cin >> n >> m;

        vector<int> a(m + 1), b(m + 1);
        vector<vector<pair<int,int>>> adj(n + 1);
        for (int i = 1; i <= m; i++) {
            cin >> a[i] >> b[i];
            adj[a[i]].push_back({b[i], i});
            adj[b[i]].push_back({a[i], i});
        }

        it.init(n, m);

        // Block all roads.
        for (int i = 1; i <= m; i++) it.blockRoad(i);

        // Find starting intersection s with all roads blocked.
        int s = 1;
        bool foundS = false;
        for (int v = 1; v <= n; v++) {
            int r = it.queryVertex(v);
            if (r == 1) {
                s = v;
                foundS = true;
                break;
            }
        }
        if (!foundS) s = 1;

        vector<int> repaired(m + 1, 0);

        vector<char> reached(n + 1, 0);
        vector<int> parent(n + 1, 0), parentEdge(n + 1, 0), depth(n + 1, 0);

        reached[s] = 1;
        parent[s] = s;
        parentEdge[s] = 0;
        depth[s] = 0;

        queue<int> q;
        q.push(s);

        // Discover a repaired spanning tree: keep only tree edges unblocked.
        while (!q.empty()) {
            int u = q.front();
            q.pop();
            for (auto [v, id] : adj[u]) {
                if (reached[v]) continue;
                // id should be blocked currently
                it.unblockRoad(id);
                int r = it.queryVertex(v);
                if (r == 1) {
                    repaired[id] = 1; // tree edge repaired
                    reached[v] = 1;
                    parent[v] = u;
                    parentEdge[v] = id;
                    depth[v] = depth[u] + 1;
                    q.push(v);
                    // keep edge unblocked
                } else {
                    it.blockRoad(id);
                }
            }
        }

        // If something went wrong, try to finish by scanning edges until all reached (safety).
        bool progress = true;
        while (progress) {
            progress = false;
            for (int id = 1; id <= m; id++) {
                int u = a[id], v = b[id];
                if (reached[u] && !reached[v]) {
                    it.unblockRoad(id);
                    int r = it.queryVertex(v);
                    if (r == 1) {
                        repaired[id] = 1;
                        reached[v] = 1;
                        parent[v] = u;
                        parentEdge[v] = id;
                        depth[v] = depth[u] + 1;
                        q.push(v);
                        progress = true;
                    } else {
                        it.blockRoad(id);
                    }
                } else if (reached[v] && !reached[u]) {
                    it.unblockRoad(id);
                    int r = it.queryVertex(u);
                    if (r == 1) {
                        repaired[id] = 1;
                        reached[u] = 1;
                        parent[u] = v;
                        parentEdge[u] = id;
                        depth[u] = depth[v] + 1;
                        q.push(u);
                        progress = true;
                    } else {
                        it.blockRoad(id);
                    }
                }
            }
            while (!q.empty()) {
                int u = q.front(); q.pop();
                for (auto [v, id] : adj[u]) {
                    if (reached[v]) continue;
                    it.unblockRoad(id);
                    int r = it.queryVertex(v);
                    if (r == 1) {
                        repaired[id] = 1;
                        reached[v] = 1;
                        parent[v] = u;
                        parentEdge[v] = id;
                        depth[v] = depth[u] + 1;
                        q.push(v);
                        progress = true;
                    } else {
                        it.blockRoad(id);
                    }
                }
            }
        }

        // Build LCA structure on the discovered tree.
        int LOG = 1;
        while ((1 << LOG) <= n) LOG++;
        vector<vector<int>> up(LOG, vector<int>(n + 1, 0));
        for (int v = 1; v <= n; v++) {
            if (!reached[v]) {
                // If unreachable due to unexpected interaction behavior, default parent to itself.
                parent[v] = v;
                parentEdge[v] = 0;
                depth[v] = 0;
                reached[v] = 1;
            }
            up[0][v] = parent[v];
            if (up[0][v] == 0) up[0][v] = v;
        }
        for (int j = 1; j < LOG; j++) {
            for (int v = 1; v <= n; v++) {
                up[j][v] = up[j - 1][ up[j - 1][v] ];
            }
        }

        auto lca = [&](int u, int v) {
            if (depth[u] < depth[v]) swap(u, v);
            int diff = depth[u] - depth[v];
            for (int j = 0; j < LOG; j++) if (diff & (1 << j)) u = up[j][u];
            if (u == v) return u;
            for (int j = LOG - 1; j >= 0; j--) {
                if (up[j][u] != up[j][v]) {
                    u = up[j][u];
                    v = up[j][v];
                }
            }
            return up[0][u];
        };

        // Determine non-tree edges.
        for (int id = 1; id <= m; id++) {
            if (repaired[id]) continue; // already known repaired (tree edge)

            int u = a[id], v = b[id];
            int w = lca(u, v);

            int child = -1;
            int cutEdge = -1;

            if (w != u) {
                child = u;
                cutEdge = parentEdge[u];
            } else {
                child = v;
                cutEdge = parentEdge[v];
            }

            if (cutEdge <= 0) {
                // Shouldn't happen; conservatively mark as not repaired.
                repaired[id] = 0;
                continue;
            }

            // Test id by removing a tree edge on the path and adding this edge as the only extra.
            it.unblockRoad(id);     // enable candidate
            it.blockRoad(cutEdge);  // cut the tree

            int r = it.queryVertex(child);
            if (r == 1) repaired[id] = 1;

            it.unblockRoad(cutEdge); // restore tree edge
            it.blockRoad(id);        // block candidate again
        }

        int verdict = it.answer(repaired);
        if (verdict != 1) die();
    }

    return 0;
}