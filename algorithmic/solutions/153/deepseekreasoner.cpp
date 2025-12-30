#include <bits/stdc++.h>
using namespace std;

struct UnionFind {
    vector<int> parent, rank;
    UnionFind(int n) {
        parent.resize(n);
        rank.resize(n, 0);
        for (int i = 0; i < n; ++i) parent[i] = i;
    }
    int find(int x) {
        if (parent[x] != x) parent[x] = find(parent[x]);
        return parent[x];
    }
    bool unite(int x, int y) {
        x = find(x);
        y = find(y);
        if (x == y) return false;
        if (rank[x] < rank[y]) parent[x] = y;
        else {
            parent[y] = x;
            if (rank[x] == rank[y]) ++rank[x];
        }
        return true;
    }
    bool same(int x, int y) {
        return find(x) == find(y);
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    const int N = 400;
    const int M = 1995;
    vector<int> x(N), y(N);
    for (int i = 0; i < N; ++i) {
        cin >> x[i] >> y[i];
    }

    vector<int> u(M), v(M), d(M);
    for (int i = 0; i < M; ++i) {
        cin >> u[i] >> v[i];
        double dx = x[u[i]] - x[v[i]];
        double dy = y[u[i]] - y[v[i]];
        d[i] = (int)round(sqrt(dx * dx + dy * dy));
    }

    // Minimum spanning tree on d (lower bound)
    vector<int> order(M);
    iota(order.begin(), order.end(), 0);
    sort(order.begin(), order.end(),
         [&](int i, int j) { return d[i] < d[j]; });
    UnionFind uf_mst(N);
    vector<bool> in_mst(M, false);
    for (int idx : order) {
        if (uf_mst.unite(u[idx], v[idx])) {
            in_mst[idx] = true;
        }
    }

    UnionFind uf(N);
    int adopted = 0;
    vector<bool> processed(M, false);

    for (int i = 0; i < M; ++i) {
        int l;
        cin >> l;
        processed[i] = true;

        int a = uf.find(u[i]);
        int b = uf.find(v[i]);
        if (a == b) {
            cout << 0 << endl;
            continue;
        }

        // Count remaining direct connections between the two components
        int k_others = 0;
        int d_min_others = INT_MAX;
        for (int j = 0; j < M; ++j) {
            if (processed[j]) continue;
            int ca = uf.find(u[j]);
            int cb = uf.find(v[j]);
            if ((ca == a && cb == b) || (ca == b && cb == a)) {
                ++k_others;
                if (d[j] < d_min_others) d_min_others = d[j];
            }
        }

        bool accept = false;
        if (k_others == 0) {
            accept = true;
        } else {
            // Very cheap offer
            if (l <= 1.2 * d[i]) {
                accept = true;
            } else if (in_mst[i]) {
                if (l <= 3 * d_min_others) accept = true;
            } else {
                if (l <= 2.5 * d_min_others) accept = true;
            }
            // Safety: running out of edges
            int remaining = M - i - 1;
            int needed = N - adopted - 1;
            if (!accept && remaining < needed) {
                accept = true;
            }
        }

        if (accept) {
            uf.unite(u[i], v[i]);
            ++adopted;
            cout << 1 << endl;
        } else {
            cout << 0 << endl;
        }
    }

    return 0;
}