#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N;
    if (!(cin >> N)) return 0;
    vector<int> p(N + 1, 0);
    vector<vector<int>> adj(N + 1);
    vector<int> degTree(N + 1, 0);
    for (int i = 2; i <= N; i++) {
        cin >> p[i];
        int u = p[i], v = i;
        adj[u].push_back(v);
        adj[v].push_back(u);
        degTree[u]++;
        degTree[v]++;
    }
    
    // Identify leaves in the tree
    vector<int> leaves;
    leaves.reserve(N);
    for (int i = 1; i <= N; i++) {
        if (degTree[i] == 1) leaves.push_back(i);
    }
    sort(leaves.begin(), leaves.end());
    int k = (int)leaves.size();
    
    // Add outer ring edges between leaves in increasing order, avoiding duplicate for k == 2
    if (k >= 2) {
        for (int i = 0; i + 1 < k; i++) {
            int u = leaves[i], v = leaves[i + 1];
            adj[u].push_back(v);
            adj[v].push_back(u);
        }
        if (k >= 3) {
            int u = leaves[k - 1], v = leaves[0];
            adj[u].push_back(v);
            adj[v].push_back(u);
        }
    }
    
    // Degeneracy ordering with threshold 3
    vector<int> deg(N + 1, 0), removed(N + 1, 0);
    for (int i = 1; i <= N; i++) deg[i] = (int)adj[i].size();
    deque<int> q;
    for (int i = 1; i <= N; i++) if (deg[i] <= 3) q.push_back(i);
    
    vector<int> order;
    order.reserve(N);
    vector<vector<int>> later(N + 1);
    
    while (!q.empty()) {
        int v = q.front();
        q.pop_front();
        if (removed[v]) continue;
        if (deg[v] > 3) continue; // will be reconsidered when degree decreases
        
        // Determine current alive neighbors (later neighbors)
        vector<int> L;
        L.reserve(3);
        for (int u : adj[v]) if (!removed[u]) L.push_back(u);
        // Remove v
        removed[v] = 1;
        later[v] = L;
        order.push_back(v);
        // Update degrees of alive neighbors
        for (int u : L) {
            deg[u]--;
            if (deg[u] <= 3) q.push_back(u);
        }
    }
    
    // Safety: in valid inputs (Halin-like graph) degeneracy <= 3, so all should be removed
    // Build position mapping
    vector<int> pos(N + 1, -1);
    for (int i = 0; i < N; i++) pos[order[i]] = i;
    
    // Build decomposition edges
    int K = N;
    vector<pair<int,int>> edges;
    edges.reserve(K - 1);
    vector<int> parent(K, -1);
    for (int i = 0; i < K; i++) {
        int v = order[i];
        if (!later[v].empty()) {
            int best = pos[later[v][0]];
            for (int u : later[v]) {
                int pu = pos[u];
                if (pu < best) best = pu;
            }
            parent[i] = best;
            edges.emplace_back(i + 1, best + 1);
        }
    }
    int rootIndex = K - 1; // last eliminated vertex is always a root
    for (int i = 0; i < K; i++) {
        if (parent[i] == -1 && i != rootIndex) {
            edges.emplace_back(i + 1, rootIndex + 1);
        }
    }
    
    // Output
    cout << K << '\n';
    for (int i = 0; i < K; i++) {
        int v = order[i];
        int sz = 1 + (int)later[v].size();
        cout << sz << ' ' << v;
        for (int u : later[v]) cout << ' ' << u;
        cout << '\n';
    }
    for (auto &e : edges) {
        cout << e.first << ' ' << e.second << '\n';
    }
    return 0;
}