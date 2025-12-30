#include <iostream>
#include <vector>
#include <string>
#include <numeric>
#include <algorithm>
#include <random>
#include <map>

using namespace std;

// The problem specifies 100 vertices.
const int N = 100;
int adj[105][105];

// Helper to interact with the judge
int query(int a, int b, int c) {
    cout << "? " << a + 1 << " " << b + 1 << " " << c + 1 << endl;
    int res;
    cin >> res;
    return res;
}

// Struct to hold component info for the incremental step.
// A component is a set of vertices with known XOR relations relative to a representative.
struct Component {
    int rep;
    // members.first is node index, members.second is parity relative to rep (0: same, 1: diff)
    vector<pair<int, int>> members;
};

// Solve the first 5 vertices completely using 10 queries (choose(5,3) = 10 equations for choose(5,2)=10 unknowns).
void solve_base() {
    vector<int> nodes = {0, 1, 2, 3, 4};
    // Edges order mapping
    vector<pair<int, int>> edges;
    map<pair<int, int>, int> edge_idx;
    int idx = 0;
    for (int i = 0; i < 5; ++i) {
        for (int j = i + 1; j < 5; ++j) {
            edges.push_back({i, j});
            edge_idx[{i, j}] = idx++;
        }
    }

    // Prepare system of linear equations
    // Matrix size 10x11 (last column is constant vector)
    vector<vector<double>> mat(10, vector<double>(11, 0.0));
    int row = 0;
    for (int i = 0; i < 5; ++i) {
        for (int j = i + 1; j < 5; ++j) {
            for (int k = j + 1; k < 5; ++k) {
                int q = query(i, j, k);
                mat[row][10] = (double)q;
                // Edges involved in the triplet are (i,j), (j,k), (i,k) (sorted indices)
                mat[row][edge_idx[{i, j}]] = 1.0;
                mat[row][edge_idx[{j, k}]] = 1.0;
                mat[row][edge_idx[{min(i, k), max(i, k)}]] = 1.0;
                row++;
            }
        }
    }

    // Solve using Gaussian elimination
    for (int i = 0; i < 10; ++i) {
        int pivot = i;
        while (pivot < 10 && abs(mat[pivot][i]) < 1e-9) pivot++;
        if (pivot < 10) {
            swap(mat[i], mat[pivot]);
            double div = mat[i][i];
            for (int j = i; j <= 10; ++j) mat[i][j] /= div;
            for (int k = 0; k < 10; ++k) {
                if (k != i && abs(mat[k][i]) > 1e-9) {
                    double mul = mat[k][i];
                    for (int j = i; j <= 10; ++j) mat[k][j] -= mul * mat[i][j];
                }
            }
        }
    }

    // Extract solution
    for (int i = 0; i < 10; ++i) {
        int val = (int)(mat[i][10] + 0.5);
        int u = edges[i].first;
        int v = edges[i].second;
        adj[u][v] = adj[v][u] = val;
    }
}

int main() {
    // Solve for the base set of vertices {0, 1, 2, 3, 4}
    solve_base();

    vector<int> known;
    for(int i=0; i<5; ++i) known.push_back(i);

    // Random number generator for shuffling components
    mt19937 rng(12345);

    // Incrementally solve for each new vertex y from 5 to N-1
    for (int y = 5; y < N; ++y) {
        // We want to find adj[u][y] for all u in 'known'.
        // Initially, each u is its own component with unknown value adj[u][y].
        vector<Component> comps;
        for (int u : known) {
            Component c;
            c.rep = u;
            c.members.push_back({u, 0});
            comps.push_back(c);
        }

        vector<int> resolved_vals(N, -1); // To store determined values for current y
        vector<int> resolved_nodes; // Keep track of nodes resolved in this step

        // Process components until at most 1 remains
        while (comps.size() > 1) {
            shuffle(comps.begin(), comps.end(), rng);
            vector<Component> next_comps;
            
            for (size_t i = 0; i + 1 < comps.size(); i += 2) {
                Component& c1 = comps[i];
                Component& c2 = comps[i+1];
                int u = c1.rep;
                int v = c2.rep;
                
                int q = query(u, v, y);
                // query result = E(u,v) + E(u,y) + E(v,y)
                // We know E(u,v)
                int sum_uv = q - adj[u][v]; 
                // sum_uv = x_u + x_v

                if (sum_uv == 0) { // x_u=0, x_v=0
                    // Both components resolved to 0 (and their members propagated)
                    for(auto& p : c1.members) {
                        resolved_vals[p.first] = p.second; // 0 ^ parity
                        resolved_nodes.push_back(p.first);
                    }
                    for(auto& p : c2.members) {
                        resolved_vals[p.first] = p.second; // 0 ^ parity
                        resolved_nodes.push_back(p.first);
                    }
                } else if (sum_uv == 2) { // x_u=1, x_v=1
                    // Both components resolved to 1
                    for(auto& p : c1.members) {
                        resolved_vals[p.first] = 1 ^ p.second;
                        resolved_nodes.push_back(p.first);
                    }
                    for(auto& p : c2.members) {
                        resolved_vals[p.first] = 1 ^ p.second;
                        resolved_nodes.push_back(p.first);
                    }
                } else { // sum_uv == 1 => x_u != x_v
                    // Components are linked with opposite parity. Merge c2 into c1.
                    for(auto& p : c2.members) {
                        p.second = p.second ^ 1; // flip parity since v is opposite to u
                        c1.members.push_back(p);
                    }
                    next_comps.push_back(c1);
                }
            }
            // If odd number of components, the last one carries over to next round
            if (comps.size() % 2 == 1) {
                next_comps.push_back(comps.back());
            }
            comps = next_comps;
        }

        // If one component remains, we need to determine its value
        if (!comps.empty()) {
            Component& c = comps[0];
            int rep = c.rep;
            int x_rep = -1;

            if (!resolved_nodes.empty()) {
                // Use a resolved node w to determine rep
                int w = resolved_nodes[0];
                int x_w = resolved_vals[w];
                int q = query(rep, w, y);
                // q = adj[rep][w] + x_rep + x_w
                int val = q - adj[rep][w] - x_w;
                x_rep = val;
            } else {
                // No resolved nodes available (all queries returned 1).
                // Use internal consistency within the component.
                // Split component into two sets based on relative parity.
                vector<int> P0, P1;
                for(auto& p : c.members) {
                    if(p.second == 0) P0.push_back(p.first);
                    else P1.push_back(p.first);
                }
                
                // By pigeonhole principle, since |known| >= 5, one set has >= 2 nodes.
                if (P0.size() >= 2) {
                    int u = P0[0];
                    int v = P0[1];
                    // x_u = x_v = x_rep
                    int q = query(u, v, y);
                    // q = adj[u][v] + 2 * x_rep
                    int val = q - adj[u][v];
                    x_rep = val / 2;
                } else {
                    int u = P1[0];
                    int v = P1[1];
                    // x_u = x_v = 1 ^ x_rep
                    int q = query(u, v, y);
                    int val = q - adj[u][v]; // 2 * x_u
                    int x_u = val / 2;
                    x_rep = 1 ^ x_u;
                }
            }

            // Propagate determined value to all members
            for(auto& p : c.members) {
                resolved_vals[p.first] = x_rep ^ p.second;
            }
        }

        // Store the results in the adjacency matrix
        for(int u : known) {
            adj[u][y] = adj[y][u] = resolved_vals[u];
        }
        known.push_back(y);
    }

    // Output the result
    cout << "!" << endl;
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            if (i == j) cout << "0";
            else cout << adj[i][j];
        }
        cout << endl;
    }

    return 0;
}