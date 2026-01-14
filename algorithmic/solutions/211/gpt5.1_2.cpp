#include <bits/stdc++.h>
using namespace std;

struct Node {
    int id;
    int x, y;
    char type;
};

struct DSU {
    vector<int> p, r;
    DSU(int n = 0) { init(n); }
    void init(int n) {
        p.resize(n);
        r.assign(n, 0);
        iota(p.begin(), p.end(), 0);
    }
    int find(int x) { return p[x] == x ? x : p[x] = find(p[x]); }
    bool unite(int a, int b) {
        a = find(a);
        b = find(b);
        if (a == b) return false;
        if (r[a] < r[b]) swap(a, b);
        p[b] = a;
        if (r[a] == r[b]) r[a]++;
        return true;
    }
};

struct Edge {
    int u, v;
    unsigned long long w;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, K;
    if (!(cin >> N >> K)) return 0;
    int total = N + K;
    vector<Node> nodes;
    nodes.reserve(total);
    for (int i = 0; i < total; ++i) {
        Node nd;
        cin >> nd.id >> nd.x >> nd.y >> nd.type;
        nodes.push_back(nd);
    }

    vector<int> robots;
    robots.reserve(N);
    for (int i = 0; i < total; ++i) {
        if (nodes[i].type != 'C') robots.push_back(i);
    }

    int Rcnt = (int)robots.size();
    if (Rcnt == 0) {
        cout << "#\n\n";
        return 0;
    }

    vector<Edge> edges;
    long long maxEdges = 1LL * Rcnt * (Rcnt - 1) / 2;
    edges.reserve((size_t)maxEdges);

    for (int i = 0; i < Rcnt; ++i) {
        int idx_i = robots[i];
        int xi = nodes[idx_i].x, yi = nodes[idx_i].y;
        char ti = nodes[idx_i].type;
        for (int j = i + 1; j < Rcnt; ++j) {
            int idx_j = robots[j];
            int dx = xi - nodes[idx_j].x;
            int dy = yi - nodes[idx_j].y;
            long long dist2 = 1LL * dx * dx + 1LL * dy * dy;
            int factor = (ti == 'R' && nodes[idx_j].type == 'R') ? 5 : 4;
            unsigned long long w = dist2 * (unsigned long long)factor;
            edges.push_back({i, j, w});
        }
    }

    sort(edges.begin(), edges.end(),
         [](const Edge &a, const Edge &b) { return a.w < b.w; });

    DSU dsu(Rcnt);
    vector<pair<int, int>> used;
    used.reserve(Rcnt - 1);
    int components = Rcnt;
    for (const auto &e : edges) {
        if (dsu.unite(e.u, e.v)) {
            used.push_back({e.u, e.v});
            if (--components == 1) break;
        }
    }

    // Selected relay stations: none
    cout << "#\n";

    // Communication links
    for (size_t i = 0; i < used.size(); ++i) {
        int u_idx = robots[used[i].first];
        int v_idx = robots[used[i].second];
        int id1 = nodes[u_idx].id;
        int id2 = nodes[v_idx].id;
        if (id1 > id2) swap(id1, id2);
        cout << id1 << "-" << id2;
        if (i + 1 < used.size()) cout << "#";
    }
    cout << "\n";

    return 0;
}