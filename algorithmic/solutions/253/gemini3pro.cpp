#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <random>
#include <map>

using namespace std;

// Structure to represent an edge
struct Edge {
    int u, v, id;
};

// Disjoint Set Union (DSU) structure for tracking connected components
struct DSU {
    vector<int> parent;
    DSU(int n) {
        parent.resize(n + 1);
        iota(parent.begin(), parent.end(), 0);
    }
    int find(int i) {
        if (parent[i] == i)
            return i;
        return parent[i] = find(parent[i]);
    }
    void unite(int i, int j) {
        int root_i = find(i);
        int root_j = find(j);
        if (root_i != root_j) {
            parent[root_i] = root_j;
        }
    }
};

// Function to perform the connectivity query
// We use K iterations to distinguish between:
// - Connected: Probability of returning 1 is 1.0
// - Disconnected: Probability of returning 1 is 0.5 (since s can reach only one of u or v)
bool query_connectivity(int u, int v) {
    // K=12 implies error probability 0.5^12 approx 2.4e-4 per edge.
    // This balances cost and accuracy.
    int K = 12;
    for (int k = 0; k < K; ++k) {
        cout << "? 2 " << u << " " << v << "\n";
        cout.flush();
        int res;
        cin >> res;
        if (res == -1) exit(0);
        if (res == 0) return false; // If we see a 0, it's definitely disconnected
    }
    return true; // If all 1s, we assume connected
}

void solve() {
    int n, m;
    if (!(cin >> n >> m)) return;
    
    vector<Edge> edges;
    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        edges.push_back({u, v, i + 1});
    }

    // Initially block all roads
    for (int i = 1; i <= m; ++i) {
        cout << "- " << i << "\n";
    }
    cout.flush();

    vector<int> result(m + 1, 0);
    vector<Edge> tree_edges;
    vector<int> check_list; // Indices of edges to check in Phase 2
    
    // Shuffle edges to ensure random tree structure and average case performance
    vector<int> p(m);
    iota(p.begin(), p.end(), 0);
    mt19937 rng(1337);
    shuffle(p.begin(), p.end(), rng);

    DSU dsu(n);
    vector<vector<pair<int, int>>> adj(n + 1);

    // Phase 1: Build a Spanning Tree of Repaired Edges
    for (int i : p) {
        int u = edges[i].u;
        int v = edges[i].v;
        int id = edges[i].id;

        if (dsu.find(u) != dsu.find(v)) {
            // Unblock the edge to test it
            cout << "+ " << id << "\n";
            cout.flush();
            
            if (query_connectivity(u, v)) {
                // It connects the components => It is Repaired
                result[id] = 1;
                dsu.unite(u, v);
                tree_edges.push_back(edges[i]);
                adj[u].push_back({v, id});
                adj[v].push_back({u, id});
            } else {
                // It does not connect => Not Repaired
                // We leave it unblocked. Since it's not repaired, it's invisible to queries.
                // This saves the cost of blocking it back.
                result[id] = 0;
            }
        } else {
            // u and v already connected in our tree
            // This edge forms a cycle, check in Phase 2
            check_list.push_back(i);
        }
    }

    // Phase 2: Check remaining edges that form cycles with the tree
    for (int i : check_list) {
        int u = edges[i].u;
        int v = edges[i].v;
        int id = edges[i].id;

        // Unblock the candidate edge
        cout << "+ " << id << "\n";
        cout.flush();

        // Find the path in the tree between u and v to pick an edge to block
        // Since u, v are connected in tree, a simple BFS works
        vector<int> parent_edge(n + 1, 0);
        vector<bool> visited(n + 1, false);
        vector<int> q;
        q.reserve(n);
        
        q.push_back(u);
        visited[u] = true;
        
        bool found = false;
        int head = 0;
        while(head < q.size()){
            int curr = q[head++];
            if(curr == v) {
                found = true;
                break;
            }
            for(auto& edge : adj[curr]){
                int neighbor = edge.first;
                int eid = edge.second;
                if(!visited[neighbor]){
                    visited[neighbor] = true;
                    parent_edge[neighbor] = eid;
                    q.push_back(neighbor);
                }
            }
        }

        // We block one edge on the tree path. The edge incident to v is convenient.
        int f_id = parent_edge[v];
        
        // Temporarily block the tree edge
        cout << "- " << f_id << "\n";
        cout.flush();

        // Check if u and v are still connected (via the candidate edge)
        if (query_connectivity(u, v)) {
            result[id] = 1; // Connected implies candidate edge is repaired
        } else {
            result[id] = 0; // Disconnected implies candidate edge is not repaired
        }

        // Unblock the tree edge to restore the tree structure
        cout << "+ " << f_id << "\n";
        cout.flush();
    }

    // Output the result
    cout << "!";
    for (int i = 1; i <= m; ++i) {
        cout << " " << result[i];
    }
    cout << "\n";
    cout.flush();
    
    int ok;
    cin >> ok;
    if (ok == 0) exit(0);
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    int t;
    if (cin >> t) {
        while (t--) {
            solve();
        }
    }
    return 0;
}