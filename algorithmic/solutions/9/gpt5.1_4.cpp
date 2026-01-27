#include <bits/stdc++.h>
using namespace std;

const int MAXN = 1000 + 5;

vector<pair<int,int>> g[MAXN]; // adjacency: (neighbor, edge_id)
vector<pair<int,int>> edges;   // 1-based: edges[1..n-1] = (u,v)

int pArr[MAXN];        // token at vertex i
int posArr[MAXN];      // position of token i
int parentArr[MAXN];   // parent in rooted tree
int parentEdgeArr[MAXN]; // edge id to parent
int depthArr[MAXN];

vector<int> operations; // sequence of edge ids (each is a single-edge matching op)

int N;

void dfs(int u, int par) {
    for (auto &pr : g[u]) {
        int v = pr.first;
        int id = pr.second;
        if (v == par) continue;
        parentArr[v] = u;
        parentEdgeArr[v] = id;
        depthArr[v] = depthArr[u] + 1;
        dfs(v, u);
    }
}

inline void applyEdgeSwap(int eid) {
    int u = edges[eid].first;
    int v = edges[eid].second;
    int a = pArr[u];
    int b = pArr[v];
    pArr[u] = b;
    pArr[v] = a;
    posArr[a] = v;
    posArr[b] = u;
    operations.push_back(eid);
}

void star_swap(int x) {
    if (x == 1) return;
    vector<int> path;
    path.reserve(depthArr[x]);
    int v = x;
    while (v != 1) {
        path.push_back(parentEdgeArr[v]);
        v = parentArr[v];
    }
    reverse(path.begin(), path.end());
    int m = (int)path.size();
    for (int i = 0; i < m; ++i) applyEdgeSwap(path[i]);
    for (int i = m - 2; i >= 0; --i) applyEdgeSwap(path[i]);
}

void swap_vertices(int u, int v) {
    if (u == v) return;
    if (u == 1 || v == 1) {
        int k = (u == 1 ? v : u);
        star_swap(k); // performs (1, k)
    } else {
        star_swap(u);
        star_swap(v);
        star_swap(u); // (1,u)(1,v)(1,u) = (u,v)
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int T;
    if (!(cin >> T)) return 0;
    while (T--) {
        cin >> N;
        for (int i = 1; i <= N; ++i) g[i].clear();
        edges.assign(N, {0,0}); // index 0 unused

        for (int i = 1; i <= N; ++i) {
            cin >> pArr[i];
        }

        for (int i = 1; i <= N - 1; ++i) {
            int u, v;
            cin >> u >> v;
            edges[i] = {u, v};
            g[u].push_back({v, i});
            g[v].push_back({u, i});
        }

        // Build rooted tree at 1
        depthArr[1] = 0;
        parentArr[1] = 0;
        parentEdgeArr[1] = 0;
        dfs(1, 0);

        // Build position array
        for (int i = 1; i <= N; ++i) {
            posArr[pArr[i]] = i;
        }

        operations.clear();
        operations.reserve(min(6 * N * N, 6000000));

        // Sort permutation using arbitrary transpositions, implemented via tree swaps
        for (int i = 1; i <= N; ++i) {
            if (pArr[i] != i) {
                int j = posArr[i]; // position of token i
                swap_vertices(i, j);
            }
        }

        cout << operations.size() << '\n';
        for (int eid : operations) {
            cout << 1 << ' ' << eid << '\n';
        }
    }
    return 0;
}