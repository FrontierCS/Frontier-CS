#include <iostream>
#include <vector>
#include <string>
#include <numeric>
#include <algorithm>
#include <map>
#include <cstdlib>
#include <ctime>
#include <random>

using namespace std;

// Adjacency matrix to store the graph
int adj[105][105];
// Permutation array to randomize vertex processing order
int p[105];
int N = 100;

// Function to perform a query
int query(int a, int b, int c) {
    cout << "? " << a << " " << b << " " << c << endl;
    int res;
    cin >> res;
    return res;
}

// Structure to represent a component of vertices with known relative values
struct Component {
    vector<int> p0; // Vertices that have value 'v'
    vector<int> p1; // Vertices that have value '1-v'
};

void solve() {
    // Randomize the order of vertices to avoid worst-case scenarios
    mt19937 rng(time(NULL));
    for (int i = 1; i <= N; ++i) p[i] = i;
    shuffle(p + 1, p + N + 1, rng);

    // Base case: solve for the first 6 vertices by brute force
    // 6 vertices allow 20 queries, which is enough to determine 15 edges uniquely
    int B = 6;
    if (N < 6) B = N; 

    struct QRes {
        int u, v, w;
        int res;
    };
    vector<QRes> base_queries;
    // Perform all triplet queries for the base set
    for (int i = 1; i <= B; ++i) {
        for (int j = i + 1; j <= B; ++j) {
            for (int k = j + 1; k <= B; ++k) {
                base_queries.push_back({p[i], p[j], p[k], query(p[i], p[j], p[k])});
            }
        }
    }

    // List all edges in the base set
    vector<pair<int, int>> edges;
    for (int i = 1; i <= B; ++i) {
        for (int j = i + 1; j <= B; ++j) {
            edges.push_back({p[i], p[j]});
        }
    }
    int num_edges = edges.size();
    int limit = 1 << num_edges;
    
    // Brute force all possible graphs on B vertices
    for (int mask = 0; mask < limit; ++mask) {
        // Set edges based on current mask
        for (int k = 0; k < num_edges; ++k) {
            int u = edges[k].first;
            int v = edges[k].second;
            int val = (mask >> k) & 1;
            adj[u][v] = adj[v][u] = val;
        }

        // Check if this graph matches all query results
        bool ok = true;
        for (auto &q : base_queries) {
            int cur = adj[q.u][q.v] + adj[q.v][q.w] + adj[q.w][q.u];
            if (cur != q.res) {
                ok = false;
                break;
            }
        }

        if (ok) break; // Found the valid configuration
    }

    // Incrementally add remaining vertices
    for (int k = B; k < N; ++k) {
        int target = p[k + 1]; // The new vertex being added
        vector<int> V;
        for (int i = 1; i <= k; ++i) V.push_back(p[i]);

        // Initially, each previous vertex is an independent component
        vector<Component> comps;
        for (int u : V) {
            Component c;
            c.p0.push_back(u);
            comps.push_back(c);
        }

        vector<int> known; // List of vertices u for which E(u, target) is determined

        while (!comps.empty()) {
            if (!known.empty()) {
                // If we have a resolved vertex, use it to resolve an entire component
                int r = known.back();
                Component &C = comps.back();
                int u = C.p0[0];
                
                int q = query(r, u, target);
                // q = E(r, u) + E(r, target) + E(u, target)
                // We know E(r, u) from previous steps and E(r, target) since r is in 'known'
                int val_u = q - adj[r][u] - adj[r][target];
                
                // Resolve all vertices in the component
                for (int node : C.p0) {
                    adj[node][target] = adj[target][node] = val_u;
                    known.push_back(node);
                }
                for (int node : C.p1) {
                    adj[node][target] = adj[target][node] = 1 - val_u;
                    known.push_back(node);
                }
                comps.pop_back();
            } else {
                if (comps.size() >= 2) {
                    // No resolved vertices, try to merge or resolve two components
                    Component CA = comps.back(); comps.pop_back();
                    Component CB = comps.back(); comps.pop_back();
                    int u = CA.p0[0];
                    int v = CB.p0[0];
                    
                    int q = query(u, v, target);
                    // q = E(u, v) + E(u, target) + E(v, target)
                    // sum = x_u + x_v
                    int sum = q - adj[u][v];
                    
                    if (sum == 0) { // x_u=0, x_v=0
                        for (int node : CA.p0) { adj[node][target] = adj[target][node] = 0; known.push_back(node); }
                        for (int node : CA.p1) { adj[node][target] = adj[target][node] = 1; known.push_back(node); }
                        for (int node : CB.p0) { adj[node][target] = adj[target][node] = 0; known.push_back(node); }
                        for (int node : CB.p1) { adj[node][target] = adj[target][node] = 1; known.push_back(node); }
                    } else if (sum == 2) { // x_u=1, x_v=1
                        for (int node : CA.p0) { adj[node][target] = adj[target][node] = 1; known.push_back(node); }
                        for (int node : CA.p1) { adj[node][target] = adj[target][node] = 0; known.push_back(node); }
                        for (int node : CB.p0) { adj[node][target] = adj[target][node] = 1; known.push_back(node); }
                        for (int node : CB.p1) { adj[node][target] = adj[target][node] = 0; known.push_back(node); }
                    } else { 
                        // sum == 1 implies x_u != x_v
                        // Merge components. CA.p0 matches CB.p1, CA.p1 matches CB.p0
                        Component NewC;
                        NewC.p0 = CA.p0;
                        NewC.p0.insert(NewC.p0.end(), CB.p1.begin(), CB.p1.end());
                        NewC.p1 = CA.p1;
                        NewC.p1.insert(NewC.p1.end(), CB.p0.begin(), CB.p0.end());
                        comps.push_back(NewC);
                    }
                } else {
                    // Only one huge component left and no known values
                    // Query internally within the component between two nodes expected to have same value
                    Component &C = comps.back();
                    if (C.p0.size() < 2) swap(C.p0, C.p1);
                    int u = C.p0[0];
                    int v = C.p0[1];
                    
                    int q = query(u, v, target);
                    int sum = q - adj[u][v];
                    // Since x_u = x_v, sum must be 0 or 2
                    int val = sum / 2; 
                    
                    for (int node : C.p0) {
                        adj[node][target] = adj[target][node] = val;
                        known.push_back(node);
                    }
                    for (int node : C.p1) {
                        adj[node][target] = adj[target][node] = 1 - val;
                        known.push_back(node);
                    }
                    comps.pop_back();
                }
            }
        }
    }

    // Output result
    cout << "!" << endl;
    for (int i = 1; i <= N; ++i) {
        for (int j = 1; j <= N; ++j) {
            if (i == j) cout << "0";
            else cout << adj[i][j];
        }
        cout << endl;
    }
}

int main() {
    solve();
    return 0;
}