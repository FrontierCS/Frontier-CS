#include <iostream>
#include <vector>
#include <algorithm>
#include <set>
#include <map>
#include <string>

using namespace std;

// Global variables
int n, m, t;
vector<vector<int>> adj;
vector<int> g;
vector<int> topo_order;
bool visited[1005];

// DFS for Topological Sort
void dfs(int u) {
    visited[u] = true;
    for (int v : adj[u]) {
        if (!visited[v]) dfs(v);
    }
    topo_order.push_back(u);
}

int main() {
    // optimize IO
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> n >> m >> t)) return 0;

    adj.resize(n + 1);
    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
    }

    // Topological sort
    // The problem guarantees initial graph is a DAG.
    // dfs adds to topo_order after visiting children.
    // So topo_order will be reverse topological (sinks first).
    for (int i = 1; i <= n; ++i) visited[i] = false;
    for (int i = 1; i <= n; ++i) {
        if (!visited[i]) dfs(i);
    }

    g.assign(n + 1, 0);
    vector<pair<int, int>> added_edges;
    set<int> used_values; // set of Grundy values assigned to processed nodes

    // Assign distinct Grundy values
    // Iterate through nodes in reverse topological order (starting from sinks)
    for (int i = 0; i < n; ++i) {
        int u = topo_order[i];
        
        // Calculate current Grundy value (mex of neighbors)
        set<int> neighbors_g;
        for (int v : adj[u]) neighbors_g.insert(g[v]);
        
        int mex = 0;
        while (neighbors_g.count(mex)) mex++;
        g[u] = mex;
        
        // If this value is already used by another node, we must change it.
        // We want to change g[u] to a new value X that is NOT in used_values.
        // To force g[u] = X, we need:
        // 1. All values 0..X-1 must be present in neighbors.
        // 2. Value X must NOT be present in neighbors.
        // We can add edges to nodes with values 0..X-1 to satisfy condition 1.
        // We cannot satisfy condition 2 if a neighbor already has value X.
        
        if (used_values.count(g[u])) {
            int best_X = -1;
            // Search for a suitable X
            for (int cand = 0; cand <= 2000; ++cand) {
                // We want X to be unique
                if (used_values.count(cand)) continue;
                // We cannot force X if a neighbor already has value X (since we can't remove edges)
                if (neighbors_g.count(cand)) continue;
                
                // Can we cover all gaps 0..cand-1?
                // We need to find processed nodes with these values.
                // Since used_values contains exactly the values of processed nodes,
                // if 0..cand-1 are in used_values, we can connect to them.
                // However, we check if they are missing from neighbors first.
                // If a value 'req' < cand is missing, we must be able to add an edge to a node with value 'req'.
                // Such a node exists iff 'req' is in used_values.
                
                bool possible = true;
                for (int req = 0; req < cand; ++req) {
                    if (!neighbors_g.count(req) && !used_values.count(req)) {
                        possible = false;
                        break;
                    }
                }
                
                if (possible) {
                    best_X = cand;
                    break;
                }
            }
            
            if (best_X != -1) {
                // Found a valid X. Add necessary edges.
                // We need to connect u to nodes with values 'req' for all req < best_X that are missing.
                for (int req = 0; req < best_X; ++req) {
                    if (!neighbors_g.count(req)) {
                        // Find a node v among processed nodes with g[v] == req
                        // Since N is small, linear scan is acceptable
                        for (int k = 0; k < i; ++k) {
                            int v = topo_order[k];
                            if (g[v] == req) {
                                adj[u].push_back(v);
                                added_edges.push_back({u, v});
                                break; 
                            }
                        }
                    }
                }
                g[u] = best_X;
            }
        }
        used_values.insert(g[u]);
    }

    // Output modifications
    cout << added_edges.size() << endl;
    for (auto& edge : added_edges) {
        cout << "+ " << edge.first << " " << edge.second << endl;
    }

    // Phase 2: Queries
    // Since all Grundy values are distinct, g(u) == g(v) iff u == v.
    // Query "? 1 u" puts tokens on {u, v}.
    // If u == v, tokens cancel out (XOR sum 0) -> Lose.
    // If u != v, g(u) != g(v) -> XOR sum != 0 -> Win.
    // We linearly scan candidates. 
    for (int round = 0; round < t; ++round) {
        int guessed = -1;
        // We only need to check n-1 candidates. If not them, it must be the last one.
        // We iterate 1 to n-1.
        for (int i = 1; i < n; ++i) {
            cout << "? 1 " << i << endl;
            string resp;
            cin >> resp;
            if (resp == "Lose") {
                guessed = i;
                break;
            }
        }
        if (guessed == -1) guessed = n;
        
        cout << "! " << guessed << endl;
        string verdict;
        cin >> verdict;
        if (verdict == "Wrong") return 0;
    }

    return 0;
}