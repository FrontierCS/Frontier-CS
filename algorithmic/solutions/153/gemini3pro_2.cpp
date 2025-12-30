#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <random>
#include <numeric>

using namespace std;

// Disjoint Set Union (DSU) structure to manage connected components
struct DSU {
    vector<int> parent;
    DSU(int n) : parent(n) {
        iota(parent.begin(), parent.end(), 0);
    }
    int find(int x) {
        if (parent[x] == x) return x;
        return parent[x] = find(parent[x]);
    }
    bool unite(int x, int y) {
        int rootX = find(x);
        int rootY = find(y);
        if (rootX != rootY) {
            parent[rootX] = rootY;
            return true;
        }
        return false;
    }
    bool same(int x, int y) {
        return find(x) == find(y);
    }
};

struct Edge {
    int u, v, id;
};

const int N_VAL = 400;
const int M_VAL = 1995;
int X[N_VAL], Y[N_VAL];
vector<Edge> edges;
vector<int> d_val;

// Random number generator
mt19937 rng(12345);

// Precomputed scenarios
// Each scenario contains a list of future edges (weight, index) sorted by weight.
const int K_SCENARIOS = 800; 
vector<pair<int, int>> scenarios[K_SCENARIOS];

int dist_sq(int i, int j) {
    return (X[i] - X[j]) * (X[i] - X[j]) + (Y[i] - Y[j]) * (Y[i] - Y[j]);
}

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    // Read vertex coordinates
    for (int i = 0; i < N_VAL; ++i) {
        cin >> X[i] >> Y[i];
    }

    edges.reserve(M_VAL);
    d_val.reserve(M_VAL);

    // Read edges and precompute rounded Euclidean distances
    for (int i = 0; i < M_VAL; ++i) {
        int u, v;
        cin >> u >> v;
        int d = (int)(round(sqrt(dist_sq(u, v))));
        d_val.push_back(d);
        edges.push_back({u, v, i});
    }

    // Precompute K scenarios of future edge weights
    // Weights are uniform in [d, 3d]
    for (int k = 0; k < K_SCENARIOS; ++k) {
        scenarios[k].reserve(M_VAL);
        for (int i = 0; i < M_VAL; ++i) {
            int d = d_val[i];
            int w = uniform_int_distribution<int>(d, 3 * d)(rng);
            scenarios[k].push_back({w, i});
        }
        // Sort edges by weight for efficient MST simulation
        sort(scenarios[k].begin(), scenarios[k].end());
    }

    DSU dsu(N_VAL);
    
    // Reusable structures for BFS to avoid frequent allocations
    vector<int> adj[N_VAL];
    vector<int> q(N_VAL);
    vector<int> visited(N_VAL, 0);
    int visited_token = 0;
    vector<int> nodes_touched;
    nodes_touched.reserve(2 * M_VAL);

    // Process edges one by one
    for (int i = 0; i < M_VAL; ++i) {
        int l_i;
        cin >> l_i;
        
        int u = edges[i].u;
        int v = edges[i].v;

        // If vertices are already connected, we don't need this edge
        if (dsu.same(u, v)) {
            cout << 0 << endl;
            continue;
        }

        int votes = 0;
        int remaining_votes = K_SCENARIOS;
        int threshold = K_SCENARIOS / 2;

        // Run Monte Carlo simulations
        for (int k = 0; k < K_SCENARIOS; ++k) {
            int root_u = dsu.find(u);
            int root_v = dsu.find(v);
            
            // Build temporary graph on component representatives
            // Add edges from scenario k that are available (index > i) and strictly cheaper than l_i
            // If u and v can be connected by such edges, then edge i is NOT necessary in this scenario (for MST)
            
            for (const auto& p : scenarios[k]) {
                if (p.first >= l_i) break; // Optimization: stop if weights exceed l_i
                if (p.second <= i) continue; // Skip past edges
                
                int eu = edges[p.second].u;
                int ev = edges[p.second].v;
                int ru = dsu.find(eu);
                int rv = dsu.find(ev);
                if (ru != rv) {
                    adj[ru].push_back(rv);
                    adj[rv].push_back(ru);
                    nodes_touched.push_back(ru);
                    nodes_touched.push_back(rv);
                }
            }

            // BFS to check connectivity between root_u and root_v using cheaper edges
            bool connected = false;
            visited_token++;
            int head = 0, tail = 0;
            
            if (!adj[root_u].empty()) {
                q[tail++] = root_u;
                visited[root_u] = visited_token;
                
                while(head < tail) {
                    int curr = q[head++];
                    if (curr == root_v) {
                        connected = true;
                        break;
                    }
                    for (int neighbor : adj[curr]) {
                        if (visited[neighbor] != visited_token) {
                            visited[neighbor] = visited_token;
                            q[tail++] = neighbor;
                        }
                    }
                }
            }
            
            // Cleanup adjacency list for next iteration
            for (int node : nodes_touched) {
                adj[node].clear();
            }
            nodes_touched.clear();

            // If not connected by cheaper edges, edge i is required
            if (!connected) {
                votes++;
            }
            
            // Early exit if result is determined
            remaining_votes--;
            if (votes > threshold) break;
            if (votes + remaining_votes <= threshold) break;
        }

        // If edge i is required in majority of scenarios, adopt it
        if (votes > threshold) {
            cout << 1 << endl;
            dsu.unite(u, v);
        } else {
            cout << 0 << endl;
        }
    }

    return 0;
}