#include <iostream>
#include <vector>
#include <string>
#include <tuple>
#include <cassert>
#include <algorithm>

using namespace std;

int adj[105][105];
int N = 100;

int query(int u, int v, int w) {
    cout << "? " << u << " " << v << " " << w << endl;
    int res;
    cin >> res;
    return res;
}

// Solve the subgraph for the first k vertices using brute force
void solve_base(int k) {
    vector<tuple<int, int, int, int>> constraints;
    // Collect all triplet queries within the base set
    for (int i = 1; i <= k; ++i) {
        for (int j = i + 1; j <= k; ++j) {
            for (int l = j + 1; l <= k; ++l) {
                constraints.emplace_back(i, j, l, query(i, j, l));
            }
        }
    }
    
    vector<pair<int, int>> edges;
    for (int i = 1; i <= k; ++i) {
        for (int j = i + 1; j <= k; ++j) {
            edges.push_back({i, j});
        }
    }
    
    // Backtracking to find consistent adjacency matrix
    auto solve = [&](auto&& self, int idx) -> bool {
        if (idx == edges.size()) {
            return true;
        }
        
        auto [u, v] = edges[idx];
        
        for (int val = 0; val <= 1; ++val) {
            adj[u][v] = adj[v][u] = val;
            
            bool ok = true;
            // Check constraints where (u, v) completes the triplet (a, u, v)
            // Triplet is (a, u, v) with a < u < v.
            for (int a = 1; a < u; ++a) {
                int target = -1;
                // Find constraint matching (a, u, v)
                // Since k is small (7), linear scan is fine
                for(auto& t : constraints) {
                    if (get<0>(t)==a && get<1>(t)==u && get<2>(t)==v) {
                        target = get<3>(t);
                        break;
                    }
                }
                if (target != -1) {
                    if (adj[a][u] + adj[u][v] + adj[a][v] != target) {
                        ok = false;
                        break;
                    }
                }
            }

            if (ok) {
                if (self(self, idx + 1)) return true;
            }
        }
        return false;
    };
    
    solve(solve, 0);
}

struct Component {
    vector<pair<int, int>> nodes; // node_idx, parity_relative_to_component_leader
};

void solve() {
    int BASE = 7;
    solve_base(BASE);
    
    // Incrementally add vertices
    for (int i = BASE + 1; i <= N; ++i) {
        // Initially each previous vertex is its own component
        vector<Component> comps;
        for (int j = 1; j < i; ++j) {
            comps.push_back({{{j, 0}}});
        }
        
        vector<int> solved; // nodes u where E(i, u) is determined
        
        // Tournament strategy to merge or solve components
        while (comps.size() > 1) {
            vector<Component> next_comps;
            // Pair up components
            for (size_t k = 0; k + 1 < comps.size(); k += 2) {
                auto& c1 = comps[k];
                auto& c2 = comps[k+1];
                int u = c1.nodes[0].first;
                int v = c2.nodes[0].first;
                
                // Query edge sums E(i, u) + E(i, v)
                int q = query(i, u, v); 
                int sum = q - adj[u][v]; // = E(i, u) + E(i, v)
                
                if (sum == 0 || sum == 2) {
                    // Strong information: E(i, u) == E(i, v) == sum/2
                    int val = sum / 2;
                    // Solve c1
                    for (auto& p : c1.nodes) {
                        adj[i][p.first] = adj[p.first][i] = (p.second ^ val); // p.second is relative to u (0)
                        solved.push_back(p.first);
                    }
                    // Solve c2
                    // v has same value as u
                    for (auto& p : c2.nodes) {
                        adj[i][p.first] = adj[p.first][i] = (p.second ^ val);
                        solved.push_back(p.first);
                    }
                } else {
                    // Weak information: E(i, u) != E(i, v)
                    // Merge c2 into c1
                    // u is leader of c1 (parity 0).
                    // v has value != u. So relative to u, v has parity 1.
                    for (auto& p : c2.nodes) {
                        c1.nodes.push_back({p.first, p.second ^ 1});
                    }
                    next_comps.push_back(c1);
                }
            }
            // If odd number of components, carry over the last one
            if (comps.size() % 2 == 1) {
                next_comps.push_back(comps.back());
            }
            comps = next_comps;
        }
        
        // Final cleanup
        if (!comps.empty()) {
            auto& c = comps[0];
            // If we have any solved vertex, use it to solve the component cheaply
            if (!solved.empty()) {
                int z = solved[0];
                int u = c.nodes[0].first;
                int q = query(i, u, z);
                int val_u = q - adj[u][z] - adj[i][z];
                // val_u is E(i, u)
                for (auto& p : c.nodes) {
                    adj[i][p.first] = adj[p.first][i] = (p.second ^ val_u);
                }
            } else {
                // Must solve internally using a pair with same relative parity
                vector<int> p0, p1;
                for(auto& p : c.nodes) {
                    if(p.second == 0) p0.push_back(p.first);
                    else p1.push_back(p.first);
                }
                int u = -1, v = -1;
                // Since BASE=7, component size is at least 7, so one partition has size >= 4
                if (p0.size() >= 2) { u = p0[0]; v = p0[1]; }
                else if (p1.size() >= 2) { u = p1[0]; v = p1[1]; }
                
                int q = query(i, u, v);
                int sum = q - adj[u][v]; // = 2 * E(i, u) -> must be 0 or 2
                int val = sum / 2;
                
                // If we used p0, val is for leader. If p1, val is for leader^1.
                int leader_val = (u == (p0.empty() ? -1 : p0[0])) ? val : (val ^ 1);
                
                for (auto& p : c.nodes) {
                    adj[i][p.first] = adj[p.first][i] = (p.second ^ leader_val);
                }
            }
        }
    }
    
    cout << "!" << endl;
    for(int i=1; i<=N; ++i) {
        for(int j=1; j<=N; ++j) {
            cout << (i == j ? 0 : adj[i][j]);
        }
        cout << endl;
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    solve();
    return 0;
}