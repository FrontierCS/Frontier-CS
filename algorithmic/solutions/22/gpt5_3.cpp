#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N;
    if (!(cin >> N)) return 0;
    vector<int> par(N+1, 0);
    vector<vector<int>> tree(N+1);
    for (int i = 2; i <= N; ++i) {
        int p; cin >> p;
        par[i] = p;
        tree[i].push_back(p);
        tree[p].push_back(i);
    }
    // Find leaves of the tree
    vector<int> leaves;
    leaves.reserve(N);
    for (int i = 1; i <= N; ++i) {
        if ((int)tree[i].size() == 1) leaves.push_back(i);
    }
    sort(leaves.begin(), leaves.end()); // order as problem defines
    
    // Build edge list (tree edges + ring edges)
    vector<pair<int,int>> edges;
    edges.reserve((N-1) + (int)leaves.size());
    for (int i = 2; i <= N; ++i) {
        int u = par[i], v = i;
        if (u > v) swap(u, v);
        edges.emplace_back(u, v);
    }
    int k = (int)leaves.size();
    if (k >= 2) {
        for (int i = 0; i < k; ++i) {
            int u = leaves[i], v = leaves[(i+1)%k];
            if (u > v) swap(u, v);
            edges.emplace_back(u, v);
        }
    }
    // Deduplicate edges to make simple graph
    sort(edges.begin(), edges.end());
    edges.erase(unique(edges.begin(), edges.end()), edges.end());
    
    // Build adjacency list g
    vector<vector<int>> g(N+1);
    g.reserve(N+1);
    for (auto &e : edges) {
        int u = e.first, v = e.second;
        g[u].push_back(v);
        g[v].push_back(u);
    }
    
    // Compute degeneracy ordering with threshold <= 3
    vector<int> deg(N+1, 0);
    vector<char> alive(N+1, 1);
    for (int i = 1; i <= N; ++i) deg[i] = (int)g[i].size();
    deque<int> dq;
    for (int i = 1; i <= N; ++i) if (deg[i] <= 3) dq.push_back(i);
    vector<int> order;
    order.reserve(N);
    while ((int)order.size() < N) {
        if (dq.empty()) {
            // Fallback: pick any alive vertex with minimal degree (should be <=3 for these graphs)
            int best = -1, bestDeg = INT_MAX;
            for (int i = 1; i <= N; ++i) if (alive[i] && deg[i] < bestDeg) {
                bestDeg = deg[i];
                best = i;
            }
            if (best == -1) break; // shouldn't happen
            dq.push_back(best);
        }
        int v = dq.front(); dq.pop_front();
        if (!alive[v]) continue;
        alive[v] = 0;
        order.push_back(v);
        for (int u : g[v]) if (alive[u]) {
            deg[u]--;
            if (deg[u] <= 3) dq.push_back(u);
        }
    }
    if ((int)order.size() != N) {
        // Should not happen for valid input; but produce trivial decomposition as fallback (not required)
        // However, as per problem guarantee, this path should never execute.
        order.clear();
        for (int i = 1; i <= N; ++i) order.push_back(i);
    }
    // pos[v] = position in order [0..N-1]
    vector<int> pos(N+1, 0);
    for (int i = 0; i < N; ++i) pos[order[i]] = i;
    
    // Build chordal completion: add fill edges among later neighbors of each vertex (in original g)
    vector<pair<int,int>> edges2 = edges;
    edges2.reserve(edges.size() + 3*N);
    for (int v = 1; v <= N; ++v) {
        // later neighbors in original graph g
        int cnt = 0;
        int ln[4];
        for (int u : g[v]) if (pos[u] > pos[v]) {
            if (cnt < 4) ln[cnt] = u;
            cnt++;
        }
        // add fill edges between all pairs among later neighbors
        // cnt is guaranteed <= 3 for these graphs (degeneracy <= 3)
        for (int i = 0; i < cnt; ++i) {
            for (int j = i+1; j < cnt; ++j) {
                int a = ln[i], b = ln[j];
                if (a > b) swap(a, b);
                edges2.emplace_back(a, b);
            }
        }
    }
    // Deduplicate edges2
    sort(edges2.begin(), edges2.end());
    edges2.erase(unique(edges2.begin(), edges2.end()), edges2.end());
    
    // Build adjacency of chordal graph g2
    vector<vector<int>> g2(N+1);
    g2.reserve(N+1);
    for (auto &e : edges2) {
        int u = e.first, v = e.second;
        g2[u].push_back(v);
        g2[v].push_back(u);
    }
    
    // Build bags Xi and parent pointers for tree decomposition
    vector<vector<int>> bags(N+1);
    vector<int> parentTD(N+1, 0);
    for (int v = 1; v <= N; ++v) {
        // later neighbors in g2
        vector<int> later;
        later.reserve(4);
        for (int u : g2[v]) if (pos[u] > pos[v]) later.push_back(u);
        // choose parent as neighbor with smallest position among later
        if (!later.empty()) {
            int p = later[0];
            for (int u : later) if (pos[u] < pos[p]) p = u;
            parentTD[v] = p;
        } else parentTD[v] = 0;
        // bag X_v = {v} ∪ later
        bags[v].reserve(1 + later.size());
        bags[v].push_back(v);
        for (int u : later) bags[v].push_back(u);
    }
    
    // Output
    int K = N;
    cout << K << "\n";
    for (int i = 1; i <= K; ++i) {
        cout << (int)bags[i].size();
        for (int x : bags[i]) cout << " " << x;
        cout << "\n";
    }
    // print edges of decomposition tree
    // one edge for each vertex with parentTD != 0
    for (int i = 1; i <= K; ++i) {
        if (parentTD[i] != 0) {
            cout << i << " " << parentTD[i] << "\n";
        }
    }
    return 0;
}