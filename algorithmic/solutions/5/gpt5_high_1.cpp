#include <bits/stdc++.h>
using namespace std;

struct DSU {
    int n;
    vector<int> p, sz, head, tail;
    DSU(int n=0): n(n), p(n+1), sz(n+1,1), head(n+1), tail(n+1) {
        for (int i = 1; i <= n; ++i) {
            p[i] = i;
            head[i] = i;
            tail[i] = i;
        }
    }
    int find(int x) {
        while (p[x] != x) {
            p[x] = p[p[x]];
            x = p[x];
        }
        return x;
    }
    int unify(int a, int b, int newHead, int newTail) {
        a = find(a); b = find(b);
        if (a == b) return a;
        if (sz[a] < sz[b]) swap(a, b);
        p[b] = a;
        sz[a] += sz[b];
        head[a] = newHead;
        tail[a] = newTail;
        return a;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n, m;
    if (!(cin >> n >> m)) return 0;
    vector<int> a(10);
    for (int i = 0; i < 10; ++i) cin >> a[i];

    vector<vector<int>> g(n+1), gr(n+1);
    g.shrink_to_fit(); gr.shrink_to_fit();
    g.resize(n+1); gr.resize(n+1);

    vector<pair<int,int>> edges;
    edges.reserve(m);
    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        g[u].push_back(v);
        gr[v].push_back(u);
        edges.emplace_back(u, v);
    }

    for (int u = 1; u <= n; ++u) {
        sort(g[u].begin(), g[u].end());
        // gr not needed to be sorted
    }

    // Path representation
    vector<int> nxt(n+1, 0), prv(n+1, 0);
    vector<char> used(n+1, 0);

    DSU dsu(n);

    auto edgeExists = [&](int u, int v)->bool {
        const auto &vec = g[u];
        return binary_search(vec.begin(), vec.end(), v);
    };

    // Build initial maximal paths by greedy two-ended extension for each vertex
    for (int i = 1; i <= n; ++i) {
        if (used[i]) continue;
        used[i] = 1;
        int root = i; // component representative identifier
        // dsu already initialized
        bool progress = true;
        while (true) {
            bool did = false;
            // Extend tail forward
            while (true) {
                int r = dsu.find(root);
                int t = dsu.tail[r];
                int wFound = 0;
                for (int w : g[t]) {
                    if (!used[w]) { wFound = w; break; }
                }
                if (!wFound) break;
                // link t -> wFound
                nxt[t] = wFound;
                prv[wFound] = t;
                used[wFound] = 1;
                // unify
                root = dsu.unify(r, wFound, dsu.head[r], wFound);
                did = true;
            }
            // Extend head backward
            while (true) {
                int r = dsu.find(root);
                int h = dsu.head[r];
                int wFound = 0;
                for (int w : gr[h]) {
                    if (!used[w]) { wFound = w; break; }
                }
                if (!wFound) break;
                // link wFound -> h
                nxt[wFound] = h;
                prv[h] = wFound;
                used[wFound] = 1;
                root = dsu.unify(r, wFound, wFound, dsu.tail[r]);
                did = true;
            }
            if (!did) break;
        }
    }

    // Merge components using tail->head edges and insertion between edges
    vector<int> outPos(n+1, 0);
    queue<int> q;
    for (int i = 1; i <= n; ++i) {
        if (dsu.find(i) == i) q.push(i);
    }

    while (!q.empty()) {
        int x = q.front(); q.pop();
        int r = dsu.find(x);

        while (true) {
            int t = dsu.tail[r];
            auto &adj = g[t];
            int &pos = outPos[t];

            bool mergedNow = false;

            while (pos < (int)adj.size()) {
                int v = adj[pos++];
                int c2 = dsu.find(v);
                if (c2 == r) continue;

                if (dsu.head[c2] == v) {
                    // Direct merge r -> c2
                    nxt[t] = v;
                    prv[v] = t;
                    int nr = dsu.unify(r, c2, dsu.head[r], dsu.tail[c2]);
                    r = nr;
                    q.push(r);
                    mergedNow = true;
                    break;
                } else {
                    int u = prv[v];
                    if (u != 0) {
                        if (edgeExists(u, dsu.head[r])) {
                            // Insert component r between u and v
                            // cut u->v
                            // (sanity not necessary but safe)
                            // link u -> head[r] and tail[r] -> v
                            nxt[u] = 0;
                            prv[v] = 0;

                            int hr = dsu.head[r];
                            int tr = dsu.tail[r];

                            nxt[u] = hr;
                            prv[hr] = u;

                            nxt[tr] = v;
                            prv[v] = tr;

                            int nr = dsu.unify(r, c2, dsu.head[c2], dsu.tail[c2]);
                            r = nr;
                            q.push(r);
                            mergedNow = true;
                            break;
                        }
                    }
                }
            }
            if (!mergedNow) break;
        }
    }

    // Find the largest component
    int bestRoot = dsu.find(1);
    long long bestSize = 0;
    vector<int> compSizeRoot(n+1, 0);
    for (int i = 1; i <= n; ++i) {
        if (dsu.find(i) == i) {
            compSizeRoot[i] = dsu.sz[i];
            if (dsu.sz[i] > bestSize) {
                bestSize = dsu.sz[i];
                bestRoot = i;
            }
        }
    }

    // Reconstruct the path from head to tail
    vector<int> res;
    res.reserve(bestSize);
    int start = dsu.head[bestRoot];
    // Safety to avoid infinite loops
    vector<char> seen(n+1, 0);
    int cur = start;
    while (cur != 0 && !seen[cur] && (int)res.size() < n) {
        res.push_back(cur);
        seen[cur] = 1;
        cur = nxt[cur];
    }

    cout << (int)res.size() << "\n";
    for (size_t i = 0; i < res.size(); ++i) {
        if (i) cout << ' ';
        cout << res[i];
    }
    cout << "\n";
    return 0;
}