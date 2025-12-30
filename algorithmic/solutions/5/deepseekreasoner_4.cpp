#include <bits/stdc++.h>
using namespace std;

const int MAXN = 500005;

int parent[MAXN];
int sz[MAXN];
int nxt[MAXN];
int prv[MAXN];
int comp_start[MAXN];
int comp_end[MAXN];

int find(int x) {
    if (parent[x] != x)
        parent[x] = find(parent[x]);
    return parent[x];
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    
    int n, m;
    cin >> n >> m;
    
    vector<int> a(10);
    for (int i = 0; i < 10; ++i)
        cin >> a[i];
    
    vector<pair<int, int>> edges;
    edges.reserve(m);
    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        edges.emplace_back(u, v);
    }
    
    // Initialize DSU and path data
    for (int i = 0; i < n; ++i) {
        parent[i] = i;
        sz[i] = 1;
        comp_start[i] = i;
        comp_end[i] = i;
        nxt[i] = -1;
        prv[i] = -1;
    }
    
    // Random shuffle of edges to improve merging chances
    random_device rd;
    mt19937 g(rd());
    shuffle(edges.begin(), edges.end(), g);
    
    // Process each edge once, merging when possible
    for (auto &e : edges) {
        int u = e.first, v = e.second;
        int pu = find(u);
        int pv = find(v);
        if (pu == pv) continue;
        if (u == comp_end[pu] && v == comp_start[pv]) {
            if (sz[pu] < sz[pv]) {
                // attach pu (smaller) to pv (larger)
                parent[pu] = pv;
                sz[pv] += sz[pu];
                comp_start[pv] = comp_start[pu]; // new start
                nxt[u] = v;
                prv[v] = u;
            } else {
                // attach pv to pu
                parent[pv] = pu;
                sz[pu] += sz[pv];
                comp_end[pu] = comp_end[pv]; // new end
                nxt[u] = v;
                prv[v] = u;
            }
        }
    }
    
    // Find the component with the largest size
    int best_root = -1, max_size = 0;
    for (int i = 0; i < n; ++i) {
        int root = find(i);
        if (sz[root] > max_size) {
            max_size = sz[root];
            best_root = root;
        }
    }
    
    // Reconstruct the path from start to end
    vector<int> path;
    int cur = comp_start[best_root];
    while (cur != -1) {
        path.push_back(cur);
        cur = nxt[cur];
    }
    
    // Output
    cout << path.size() << '\n';
    for (size_t i = 0; i < path.size(); ++i) {
        if (i > 0) cout << ' ';
        cout << path[i] + 1;
    }
    cout << '\n';
    
    return 0;
}