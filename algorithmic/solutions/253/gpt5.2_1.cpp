#include <bits/stdc++.h>
using namespace std;

static void die() {
    exit(0);
}

struct Interactor {
    vector<char> blocked; // 1..m
    int m;

    Interactor(int m_) : blocked(m_ + 1, 0), m(m_) {}

    void blockEdge(int idx) {
        if (idx < 1 || idx > m) die();
        if (blocked[idx]) return;
        cout << "- " << idx << "\n";
        cout.flush();
        blocked[idx] = 1;
    }

    void unblockEdge(int idx) {
        if (idx < 1 || idx > m) die();
        if (!blocked[idx]) return;
        cout << "+ " << idx << "\n";
        cout.flush();
        blocked[idx] = 0;
    }

    int queryOne(int y) {
        cout << "? 1 " << y << "\n";
        cout.flush();
        int res;
        if (!(cin >> res)) die();
        if (res == -1) die();
        return res;
    }

    int querySet(const vector<int>& ys) {
        cout << "? " << (int)ys.size();
        for (int v : ys) cout << " " << v;
        cout << "\n";
        cout.flush();
        int res;
        if (!(cin >> res)) die();
        if (res == -1) die();
        return res;
    }

    int answer(const vector<int>& ans) { // ans 1..m
        cout << "!";
        for (int i = 1; i <= m; i++) cout << " " << ans[i];
        cout << "\n";
        cout.flush();
        int verdict;
        if (!(cin >> verdict)) return 1; // local/non-interactive
        if (verdict == -1) die();
        return verdict;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int t;
    if (!(cin >> t)) return 0;
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

        Interactor it(m);

        // Force judge to "fix" the start intersection without being able to tailor it to a single vertex.
        {
            vector<int> all;
            all.reserve(n);
            for (int i = 1; i <= n; i++) all.push_back(i);
            (void)it.querySet(all);
        }

        // Block all edges.
        for (int i = 1; i <= m; i++) it.blockEdge(i);

        // Find s: with all roads blocked, only s can reach itself.
        int s = -1;
        for (int y = 1; y <= n; y++) {
            int res = it.queryOne(y);
            if (res == 1) {
                s = y;
                break;
            }
        }
        if (s == -1) die();

        // Build a repaired spanning tree by exploring from s with all edges initially blocked.
        vector<int> ans(m + 1, -1);
        vector<char> reached(n + 1, 0);
        vector<int> parent(n + 1, 0), parentEdge(n + 1, -1), depth(n + 1, 0);
        vector<char> inTree(m + 1, 0);
        vector<vector<pair<int,int>>> treeAdj(n + 1);

        queue<int> q;
        reached[s] = 1;
        parent[s] = 0;
        parentEdge[s] = -1;
        depth[s] = 0;
        q.push(s);

        int reachedCnt = 1;

        while (!q.empty()) {
            int u = q.front(); q.pop();
            for (auto [v, idx] : adj[u]) {
                if (reached[v]) continue;

                it.unblockEdge(idx);
                int res = it.queryOne(v);

                if (res == 1) {
                    ans[idx] = 1;
                    inTree[idx] = 1;

                    reached[v] = 1;
                    reachedCnt++;
                    parent[v] = u;
                    parentEdge[v] = idx;
                    depth[v] = depth[u] + 1;

                    treeAdj[u].push_back({v, idx});
                    treeAdj[v].push_back({u, idx});

                    q.push(v);
                } else {
                    ans[idx] = 0;
                    it.blockEdge(idx);
                }
            }
        }

        if (reachedCnt != n) {
            // Should not happen if the repaired roads connect the city.
            die();
        }

        // Compute tin/tout for ancestor checks.
        vector<int> tin(n + 1, 0), tout(n + 1, 0);
        int timer = 0;
        function<void(int,int)> dfs = [&](int u, int p) {
            tin[u] = ++timer;
            for (auto [v, idx] : treeAdj[u]) {
                if (v == p) continue;
                dfs(v, u);
            }
            tout[u] = ++timer;
        };
        dfs(s, 0);

        auto isAncestor = [&](int u, int v) -> bool {
            return tin[u] <= tin[v] && tout[v] <= tout[u];
        };

        // Ensure all non-tree edges are blocked (they should be, but be safe).
        for (int i = 1; i <= m; i++) {
            if (!inTree[i]) it.blockEdge(i);
        }

        // Classify all remaining edges using one cut in the tree.
        for (int idx = 1; idx <= m; idx++) {
            if (ans[idx] != -1) continue; // already known
            int u = a[idx], v = b[idx];

            // Unblock candidate edge (only non-tree edge unblocked during the test).
            it.unblockEdge(idx);

            int node;
            if (isAncestor(u, v)) node = v;
            else if (isAncestor(v, u)) node = u;
            else node = u;

            int cutEdge = parentEdge[node];
            if (cutEdge == -1) die(); // node should not be s

            it.blockEdge(cutEdge);
            int res = it.queryOne(node);
            ans[idx] = res ? 1 : 0;
            it.unblockEdge(cutEdge);

            it.blockEdge(idx);
        }

        // Tree edges are repaired.
        for (int i = 1; i <= m; i++) {
            if (inTree[i]) ans[i] = 1;
            if (ans[i] == -1) ans[i] = 0;
        }

        int verdict = it.answer(ans);
        if (verdict == 0) die();
    }

    return 0;
}