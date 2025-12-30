#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N;
    if (!(cin >> N)) return 0;
    vector<vector<int>> adj(N + 1);
    vector<int> treeDeg(N + 1, 0);
    // Read tree edges
    for (int i = 2; i <= N; ++i) {
        int p;
        cin >> p;
        adj[p].push_back(i);
        adj[i].push_back(p);
        treeDeg[p]++;
        treeDeg[i]++;
    }
    // Find leaves in the tree
    vector<int> leaves;
    leaves.reserve(N);
    for (int v = 1; v <= N; ++v) {
        if (treeDeg[v] == 1) leaves.push_back(v);
    }
    sort(leaves.begin(), leaves.end());
    int k = (int)leaves.size();
    // Add outer ring edges between consecutive leaves (in increasing order)
    if (k >= 2) {
        for (int i = 0; i + 1 < k; ++i) {
            int u = leaves[i], v = leaves[i + 1];
            adj[u].push_back(v);
            adj[v].push_back(u);
        }
        // connect last to first
        int u = leaves.back(), v = leaves.front();
        adj[u].push_back(v);
        adj[v].push_back(u);
    }
    
    // Degeneracy ordering with maximum degree <= 3 at removal time
    vector<int> deg(N + 1, 0);
    vector<char> alive(N + 1, 1);
    for (int v = 1; v <= N; ++v) deg[v] = (int)adj[v].size();
    
    vector<vector<int>> buckets(4);
    for (int v = 1; v <= N; ++v) {
        if (deg[v] <= 3) buckets[deg[v]].push_back(v);
    }
    
    vector<int> order;
    order.reserve(N);
    vector<vector<int>> laterNeighbors(N + 1);
    int aliveCount = N;
    while (aliveCount > 0) {
        int chosen = -1;
        int chosenBucket = -1;
        // Prefer deg 1..3 over 0 to keep connectivity when possible
        for (int d = 1; d <= 3; ++d) {
            while (!buckets[d].empty()) {
                int v = buckets[d].back();
                buckets[d].pop_back();
                if (alive[v] && deg[v] == d) {
                    chosen = v;
                    chosenBucket = d;
                    break;
                }
            }
            if (chosen != -1) break;
        }
        if (chosen == -1) {
            // pick from deg 0 if needed
            while (!buckets[0].empty()) {
                int v = buckets[0].back();
                buckets[0].pop_back();
                if (alive[v] && deg[v] == 0) {
                    chosen = v;
                    chosenBucket = 0;
                    break;
                }
            }
        }
        // As a fallback (shouldn't happen for Halin graphs), scan for any alive with deg<=3
        if (chosen == -1) {
            for (int v = 1; v <= N; ++v) {
                if (alive[v] && deg[v] <= 3) {
                    chosen = v;
                    chosenBucket = deg[v];
                    break;
                }
            }
        }
        // At this point, chosen must be valid
        if (chosen == -1) {
            // Should not happen
            // But to avoid infinite loop, pick any alive vertex (this may violate constraints, but input guarantees existence)
            for (int v = 1; v <= N; ++v) {
                if (alive[v]) { chosen = v; break; }
            }
        }
        
        // Record later neighbors (alive neighbors at removal time)
        vector<int> ln;
        ln.reserve(3);
        for (int u : adj[chosen]) {
            if (alive[u]) ln.push_back(u);
        }
        if ((int)ln.size() > 3) {
            // Should not happen for Halin graphs
            ln.resize(3);
        }
        laterNeighbors[chosen] = move(ln);
        
        // Remove chosen
        alive[chosen] = 0;
        order.push_back(chosen);
        --aliveCount;
        // Update neighbors
        for (int u : adj[chosen]) {
            if (alive[u]) {
                --deg[u];
                if (deg[u] <= 3 && deg[u] >= 0) {
                    buckets[deg[u]].push_back(u);
                }
            }
        }
    }
    
    // Map vertex to its elimination index (1..N)
    vector<int> ord(N + 1, 0);
    for (int i = 0; i < N; ++i) ord[order[i]] = i + 1;
    
    int K = N;
    cout << K << '\n';
    // Print bags in elimination order: bag i corresponds to vertex order[i-1]
    for (int i = 1; i <= N; ++i) {
        int v = order[i - 1];
        const auto &ln = laterNeighbors[v];
        int sz = 1 + (int)ln.size();
        cout << sz;
        cout << ' ' << v;
        for (int u : ln) cout << ' ' << u;
        cout << '\n';
    }
    
    // Build edges between bags: connect i to minimal later neighbor's bag
    vector<pair<int,int>> edges;
    edges.reserve(K - 1);
    vector<int> roots; roots.reserve(N);
    for (int i = 1; i <= N; ++i) {
        int v = order[i - 1];
        const auto &ln = laterNeighbors[v];
        if (!ln.empty()) {
            int best = -1;
            int bestOrd = INT_MAX;
            for (int u : ln) {
                int ou = ord[u];
                if (ou < bestOrd) {
                    bestOrd = ou;
                    best = ou;
                }
            }
            // i connects to best
            edges.emplace_back(i, best);
        } else {
            roots.push_back(i);
        }
    }
    // Connect multiple roots to form a tree (if needed)
    for (size_t i = 1; i < roots.size(); ++i) {
        edges.emplace_back(roots[i - 1], roots[i]);
    }
    
    // Output edges
    for (auto &e : edges) {
        cout << e.first << ' ' << e.second << '\n';
    }
    
    return 0;
}