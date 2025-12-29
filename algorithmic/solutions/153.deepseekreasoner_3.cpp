#include <iostream>
#include <vector>
#include <algorithm>
#include <cmath>
#include <numeric>
using namespace std;

struct DSU {
    vector<int> parent, rank;
    DSU(int n) : parent(n), rank(n, 1) {
        iota(parent.begin(), parent.end(), 0);
    }
    int find(int x) {
        if (parent[x] != x) parent[x] = find(parent[x]);
        return parent[x];
    }
    bool unite(int x, int y) {
        x = find(x); y = find(y);
        if (x == y) return false;
        if (rank[x] < rank[y]) swap(x, y);
        parent[y] = x;
        if (rank[x] == rank[y]) rank[x]++;
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
    for (int i = 0; i < N; i++) {
        cin >> x[i] >> y[i];
    }
    vector<int> u(M), v(M);
    for (int i = 0; i < M; i++) {
        cin >> u[i] >> v[i];
    }
    vector<int> d(M);
    for (int i = 0; i < M; i++) {
        double dx = x[u[i]] - x[v[i]];
        double dy = y[u[i]] - y[v[i]];
        d[i] = (int)round(sqrt(dx*dx + dy*dy));
    }
    vector<int> tree(M, 0);
    vector<int> order(M);
    iota(order.begin(), order.end(), 0);
    sort(order.begin(), order.end(), [&](int a, int b) {
        return d[a] < d[b];
    });
    for (int tree_idx = 1; tree_idx <= 5; tree_idx++) {
        DSU dsu(N);
        for (int idx : order) {
            if (tree[idx] == 0 && dsu.unite(u[idx], v[idx])) {
                tree[idx] = tree_idx;
            }
        }
    }
    DSU dsu_current(N);
    int comp = N;
    int taken = 0;
    for (int i = 0; i < M; i++) {
        int l;
        cin >> l;
        if (taken == N-1) {
            cout << 0 << endl;
            continue;
        }
        if (dsu_current.same(u[i], v[i])) {
            cout << 0 << endl;
            continue;
        }
        int needed = comp - 1;
        int rem_edges = M - i - 1;
        double ratio_threshold;
        if (rem_edges == 0) {
            ratio_threshold = 3.0;
        } else {
            double base_T = 1.9 - 0.1 * tree[i];
            double scale = 1.0;
            double needed_ratio = (double)needed / rem_edges;
            ratio_threshold = base_T + scale * needed_ratio;
            if (ratio_threshold > 3.0) ratio_threshold = 3.0;
        }
        double ratio = (double)l / d[i];
        if (ratio <= ratio_threshold) {
            cout << 1 << endl;
            dsu_current.unite(u[i], v[i]);
            comp--;
            taken++;
        } else {
            cout << 0 << endl;
        }
        cout.flush();
    }
    return 0;
}