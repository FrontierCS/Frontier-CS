#include <bits/stdc++.h>
using namespace std;

struct Edge {
    int u, v;
};

static inline void die() {
    exit(0);
}

struct Interactor {
    vector<char> blocked; // 1 if blocked
    Interactor(int m = 0) : blocked(m + 1, 0) {}

    void sendLine(const string& s) {
        cout << s << '\n' << flush;
    }

    int readInt() {
        int x;
        if (!(cin >> x)) die();
        if (x == -1) die();
        return x;
    }

    void blockEdge(int idx) {
        if (blocked[idx]) return; // avoid invalid request
        sendLine("- " + to_string(idx));
        blocked[idx] = 1;
    }

    void unblockEdge(int idx) {
        if (!blocked[idx]) return; // avoid invalid request
        sendLine("+ " + to_string(idx));
        blocked[idx] = 0;
    }

    int queryVertex(int v) {
        sendLine("? 1 " + to_string(v));
        return readInt();
    }

    int submit(const vector<int>& ans) {
        string out = "!";
        for (size_t i = 1; i < ans.size(); i++) {
            out.push_back(' ');
            out += to_string(ans[i]);
        }
        sendLine(out);
        return readInt();
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

        vector<Edge> edges(m + 1);
        vector<vector<int>> adj(n + 1);
        for (int i = 1; i <= m; i++) {
            int a, b;
            cin >> a >> b;
            edges[i] = {a, b};
            adj[a].push_back(i);
            adj[b].push_back(i);
        }

        Interactor it(m);

        // Block all edges
        for (int i = 1; i <= m; i++) it.blockEdge(i);

        // Find s with all edges blocked (only s is reachable from itself)
        int s = -1;
        for (int v = 1; v <= n; v++) {
            int r = it.queryVertex(v);
            if (r == 1) {
                s = v;
                break;
            }
        }
        if (s == -1) die();

        vector<int> status(m + 1, -1); // -1 unknown, 0 not repaired, 1 repaired
        vector<int> parent(n + 1, -1), parentEdge(n + 1, -1), depth(n + 1, 0);
        vector<char> reached(n + 1, 0);

        // Build a repaired spanning tree from s with only tree edges unblocked
        queue<int> q;
        reached[s] = 1;
        q.push(s);

        int reachedCnt = 1;
        while (!q.empty()) {
            int u = q.front();
            q.pop();
            for (int ei : adj[u]) {
                int a = edges[ei].u, b = edges[ei].v;
                int v = (a == u ? b : a);
                if (reached[v]) continue;
                if (!it.blocked[ei]) continue;

                it.unblockEdge(ei);
                int r = it.queryVertex(v);
                if (r == 1) {
                    status[ei] = 1;
                    reached[v] = 1;
                    parent[v] = u;
                    parentEdge[v] = ei;
                    depth[v] = depth[u] + 1;
                    q.push(v);
                    reachedCnt++;
                    if (reachedCnt == n) break;
                } else {
                    status[ei] = 0;
                    it.blockEdge(ei);
                }
            }
            if (reachedCnt == n) break;
        }
        if (reachedCnt != n) die();

        // Ensure all non-tree edges are blocked (they should be from the start)
        // status for tree edges already 1, for tested non-tree edges already 0.

        // Classify remaining edges
        for (int i = 1; i <= m; i++) {
            if (status[i] != -1) continue;

            int u = edges[i].u, v = edges[i].v;
            if (depth[u] > depth[v]) swap(u, v); // v is deeper or equal

            int pe = parentEdge[v];
            if (pe == -1) {
                // v is root; then u must be root too, but u!=v for an edge, impossible
                status[i] = 0;
                continue;
            }

            it.blockEdge(pe);
            it.unblockEdge(i);
            int r = it.queryVertex(v);
            status[i] = (r == 1 ? 1 : 0);
            it.blockEdge(i);
            it.unblockEdge(pe);
        }

        vector<int> ans(m + 1, 0);
        for (int i = 1; i <= m; i++) ans[i] = (status[i] == 1 ? 1 : 0);

        int ok = it.submit(ans);
        if (ok != 1) die();
    }

    return 0;
}