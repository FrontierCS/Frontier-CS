#include <bits/stdc++.h>
using namespace std;

static inline bool hasEdge(const vector<int>& adj, int y) {
    return binary_search(adj.begin(), adj.end(), y);
}

vector<int> build_path(const vector<vector<int>>& g, const vector<vector<int>>& gr, int start, int max_passes) {
    int n = (int)g.size() - 1;
    vector<char> inPath(n + 1, 0);
    vector<int> nxt(n + 1, -1), prv(n + 1, -1);
    vector<int> pOut(n + 1, 0), pIn(n + 1, 0);

    int head = start, tail = start;
    inPath[start] = 1;

    auto extendEnds = [&]() -> bool {
        bool changedOverall = false;
        while (true) {
            bool any = false;
            // Extend to the right as much as possible
            while (true) {
                int t = tail;
                int &p = pOut[t];
                const auto &vec = g[t];
                while (p < (int)vec.size() && inPath[vec[p]]) ++p;
                if (p < (int)vec.size()) {
                    int v = vec[p];
                    prv[v] = t; nxt[t] = v;
                    tail = v;
                    inPath[v] = 1;
                    any = true;
                } else break;
            }
            // Extend to the left as much as possible
            while (true) {
                int h = head;
                int &p = pIn[h];
                const auto &vec = gr[h];
                while (p < (int)vec.size() && inPath[vec[p]]) ++p;
                if (p < (int)vec.size()) {
                    int u = vec[p];
                    nxt[u] = h; prv[h] = u;
                    head = u;
                    inPath[u] = 1;
                    any = true;
                } else break;
            }
            if (!any) break;
            changedOverall = true;
        }
        return changedOverall;
    };

    extendEnds();

    for (int pass = 0; pass < max_passes; ++pass) {
        bool insertedAny = false;

        int x = head;
        while (x != -1 && nxt[x] != -1) {
            int y = nxt[x];
            bool insertedHere = false;
            const auto &vecX = g[x];
            for (int w : vecX) {
                if (w == y || inPath[w]) continue;
                if (hasEdge(g[w], y)) {
                    // Insert w between x and y
                    nxt[x] = w; prv[w] = x;
                    nxt[w] = y; prv[y] = w;
                    inPath[w] = 1;
                    insertedAny = true;
                    insertedHere = true;
                    x = w; // continue from (w, y)
                    break;
                }
            }
            if (!insertedHere) {
                x = y;
            }
        }

        bool changed = extendEnds();
        if (!insertedAny && !changed) break;
    }

    vector<int> res;
    res.reserve(n);
    int cur = head;
    while (cur != -1) {
        res.push_back(cur);
        cur = nxt[cur];
    }
    return res;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    if (!(cin >> n >> m)) {
        return 0;
    }
    // Read scoring parameters (unused)
    for (int i = 0; i < 10; ++i) {
        int tmp; cin >> tmp;
    }

    vector<pair<int,int>> edges;
    edges.reserve(m);
    for (int i = 0; i < m; ++i) {
        int u, v; cin >> u >> v;
        edges.emplace_back(u, v);
    }

    // Random relabeling to diversify behavior
    mt19937_64 rng(chrono::steady_clock::now().time_since_epoch().count());
    vector<int> perm(n + 1), inv(n + 1);
    for (int i = 1; i <= n; ++i) perm[i] = i;
    shuffle(perm.begin() + 1, perm.end(), rng);
    for (int i = 1; i <= n; ++i) inv[perm[i]] = i;

    vector<vector<int>> g(n + 1), gr(n + 1);
    g.shrink_to_fit(); gr.shrink_to_fit();

    for (auto &e : edges) {
        int u = perm[e.first];
        int v = perm[e.second];
        g[u].push_back(v);
        gr[v].push_back(u);
    }
    // Sort adjacency lists for binary_search
    for (int i = 1; i <= n; ++i) {
        sort(g[i].begin(), g[i].end());
        sort(gr[i].begin(), gr[i].end());
    }

    // Choose starting vertices: min indegree and a random one
    int startMinIn = 1;
    size_t bestIn = gr[1].size();
    for (int i = 2; i <= n; ++i) {
        if (gr[i].size() < bestIn) {
            bestIn = gr[i].size();
            startMinIn = i;
        }
    }
    int startRand = (int)(rng() % n) + 1;

    // Build paths with limited passes
    const int MAX_PASSES = 2;
    vector<int> bestPath = build_path(g, gr, startMinIn, MAX_PASSES);
    vector<int> path2 = build_path(g, gr, startRand, MAX_PASSES);

    if (path2.size() > bestPath.size()) bestPath.swap(path2);

    // Map back to original labels
    vector<int> ans;
    ans.reserve(bestPath.size());
    for (int v : bestPath) ans.push_back(inv[v]);

    cout << ans.size() << "\n";
    for (size_t i = 0; i < ans.size(); ++i) {
        if (i) cout << ' ';
        cout << ans[i];
    }
    cout << "\n";
    return 0;
}