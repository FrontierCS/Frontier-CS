#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N;
    if (!(cin >> N)) return 0;
    
    vector<int> parent(N + 1, 0);
    vector<int> treeDeg(N + 1, 0);
    
    for (int i = 2; i <= N; ++i) {
        int p;
        cin >> p;
        parent[i] = p;
        treeDeg[p]++;
        treeDeg[i]++;
    }
    
    // Build initial graph: tree edges + outer ring edges between leaves.
    vector< set<int> > g(N + 1);
    
    // Add tree edges
    for (int i = 2; i <= N; ++i) {
        int u = i, v = parent[i];
        g[u].insert(v);
        g[v].insert(u);
    }
    
    // Find leaves in the original tree
    vector<int> leaves;
    leaves.reserve(N);
    for (int v = 1; v <= N; ++v) {
        if (treeDeg[v] == 1) leaves.push_back(v);
    }
    sort(leaves.begin(), leaves.end());
    int Kleaves = (int)leaves.size();
    
    // Add ring edges
    if (Kleaves >= 2) {
        for (int i = 0; i < Kleaves; ++i) {
            int u = leaves[i];
            int v = leaves[(i + 1) % Kleaves];
            if (u == v) continue;
            g[u].insert(v);
            g[v].insert(u);
        }
    }
    
    // Elimination with minimum-degree heuristic, adding fill edges to make chordal
    vector<int> degree(N + 1);
    for (int v = 1; v <= N; ++v) degree[v] = (int)g[v].size();
    
    set<pair<int,int>> pq; // (degree, vertex)
    for (int v = 1; v <= N; ++v) pq.insert({degree[v], v});
    
    vector<bool> removed(N + 1, false);
    vector<int> elimOrder;
    elimOrder.reserve(N);
    vector<vector<int>> elimNeighbors; // neighbors at elimination time
    elimNeighbors.reserve(N);
    
    int maxDeg = 0;
    
    while (!pq.empty()) {
        auto it = pq.begin();
        int v = it->second;
        pq.erase(it);
        if (removed[v]) continue;
        
        // Neighbors at elimination time (all still alive)
        vector<int> neigh;
        neigh.reserve(g[v].size());
        for (int u : g[v]) neigh.push_back(u);
        
        elimNeighbors.push_back(neigh);
        elimOrder.push_back(v);
        int t = (int)neigh.size();
        if (t > maxDeg) maxDeg = t;
        
        // Add fill edges to make neighbors a clique
        for (int i = 0; i < t; ++i) {
            int a = neigh[i];
            if (removed[a]) continue;
            for (int j = i + 1; j < t; ++j) {
                int b = neigh[j];
                if (removed[b]) continue;
                if (!g[a].count(b)) {
                    // add edge a-b
                    g[a].insert(b);
                    g[b].insert(a);
                    
                    pq.erase({degree[a], a});
                    degree[a]++;
                    pq.insert({degree[a], a});
                    
                    pq.erase({degree[b], b});
                    degree[b]++;
                    pq.insert({degree[b], b});
                }
            }
        }
        
        // Remove v from graph
        removed[v] = true;
        for (int u : neigh) {
            if (removed[u]) continue;
            g[u].erase(v);
            pq.erase({degree[u], u});
            degree[u]--;
            pq.insert({degree[u], u});
        }
        g[v].clear();
    }
    
    // We expect maxDeg <= 3 for Halin graphs
    int width = maxDeg; // treewidth = width
    // (We rely on problem's structure; no explicit check.)
    
    int K = N; // number of bags
    vector<vector<int>> bags(K + 1); // 1..K
    
    for (int i = 0; i < N; ++i) {
        int v = elimOrder[i];
        auto &neigh = elimNeighbors[i];
        auto &bag = bags[i + 1];
        bag.push_back(v);
        for (int u : neigh) bag.push_back(u);
        // bag size should be <= width+1 <= 4
    }
    
    // Build tree edges between bags using elimination tree construction
    vector<int> pos(N + 1);
    for (int i = 0; i < N; ++i) pos[elimOrder[i]] = i;
    
    vector<pair<int,int>> tedges;
    tedges.reserve(K - 1);
    for (int i = 0; i < N; ++i) {
        auto &neigh = elimNeighbors[i];
        if (!neigh.empty()) {
            // choose neighbor with largest elimination index
            int best = neigh[0];
            for (int u : neigh) {
                if (pos[u] > pos[best]) best = u;
            }
            int bi = i + 1;
            int bj = pos[best] + 1;
            tedges.emplace_back(bi, bj);
        }
    }
    // Now tedges should have K-1 edges
    
    cout << K << '\n';
    for (int i = 1; i <= K; ++i) {
        auto &bag = bags[i];
        // remove possible duplicates, though there shouldn't be any
        sort(bag.begin(), bag.end());
        bag.erase(unique(bag.begin(), bag.end()), bag.end());
        cout << bag.size();
        for (int x : bag) cout << ' ' << x;
        cout << '\n';
    }
    
    for (auto &e : tedges) {
        cout << e.first << ' ' << e.second << '\n';
    }
    
    return 0;
}