#include <iostream>
#include <vector>
#include <algorithm>
#include <set>
#include <map>
#include <queue>

// Custom struct for edges to use in set/map
// Ensures u < v for canonical representation
struct Edge {
    int u, v;

    Edge(int u_in, int v_in) {
        if (u_in < v_in) {
            u = u_in;
            v = v_in;
        } else {
            u = v_in;
            v = u_in;
        }
    }

    bool operator<(const Edge& other) const {
        if (u != other.u) return u < other.u;
        return v < other.v;
    }
};

void solve() {
    int n;
    std::cin >> n;

    std::vector<int> parent(n + 1, 0);
    std::vector<std::vector<int>> adj(n + 1);

    for (int i = 2; i <= n; ++i) {
        int p;
        std::cin >> p;
        parent[i] = p;
        adj[i].push_back(p);
        adj[p].push_back(i);
    }

    std::vector<int> leaves;
    // Root has degree >= 2. Any other node with degree 1 is a leaf.
    for (int i = 2; i <= n; ++i) {
        if (adj[i].size() == 1) {
            leaves.push_back(i);
        }
    }
    std::sort(leaves.begin(), leaves.end());
    int k = leaves.size();

    std::set<Edge> g_edges;
    for (int i = 2; i <= n; ++i) {
        g_edges.insert(Edge(i, parent[i]));
    }
    if (k > 1) { // A cycle needs at least 2 vertices
        for (int i = 0; i < k; ++i) {
            g_edges.insert(Edge(leaves[i], leaves[(i + 1) % k]));
        }
    }

    int num_g_edges = g_edges.size();
    int K = n + num_g_edges;

    std::cout << K << "\n";

    // Print bags
    // Vertex bags (nodes 1 to n)
    for (int i = 1; i <= n; ++i) {
        std::cout << 1 << " " << i << "\n";
    }
    // Edge bags (nodes n+1 to K)
    std::map<Edge, int> edge_to_id;
    int current_id = n + 1;
    for (const auto& edge : g_edges) {
        edge_to_id[edge] = current_id;
        std::cout << 2 << " " << edge.u << " " << edge.v << "\n";
        current_id++;
    }

    // Build meta-graph and find spanning tree
    std::vector<std::vector<int>> meta_adj(K + 1);
    for (const auto& edge_pair : edge_to_id) {
        const auto& edge = edge_pair.first;
        int id = edge_pair.second;
        meta_adj[edge.u].push_back(id);
        meta_adj[id].push_back(edge.u);
        meta_adj[edge.v].push_back(id);
        meta_adj[id].push_back(edge.v);
    }
    
    // Find spanning tree using BFS
    std::vector<bool> visited(K + 1, false);
    std::queue<int> q;
    
    // The meta graph is connected since the original graph G is connected.
    q.push(1);
    visited[1] = true;
    
    while(!q.empty()){
        int u = q.front();
        q.pop();

        for(int v : meta_adj[u]){
            if(!visited[v]){
                visited[v] = true;
                std::cout << u << " " << v << "\n";
                q.push(v);
            }
        }
    }
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    solve();
    return 0;
}