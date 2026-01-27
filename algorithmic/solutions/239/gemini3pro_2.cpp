#include <iostream>
#include <vector>
#include <algorithm>
#include <tuple>

using namespace std;

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    int n;
    if (!(cin >> n)) return 0;

    if (n == 0) {
        cout << 0 << endl;
        return 0;
    }

    // Identify layers based on Base 16 mixed radix strategy
    // We need S0 = {1..15}, S1 = {16, 32... 240}, S2 = {256...}
    // Base 16 is suitable for 4096 (16^3).
    // For smaller N, we use a greedy approach to minimize edges.

    if (n <= 48) {
        // Adjacency matrix for small N
        vector<vector<int>> dist(n + 1, vector<int>(n + 1, 1000));
        vector<pair<int, int>> edges;
        for (int i = 0; i <= n; ++i) dist[i][i] = 0;
        for (int i = 0; i < n; ++i) {
            dist[i][i + 1] = 1;
            edges.push_back({i, i + 1});
        }
        
        // Compute initial distances
        for (int k = 0; k <= n; ++k)
            for (int i = 0; i <= n; ++i)
                for (int j = 0; j <= n; ++j)
                    dist[i][j] = min(dist[i][j], dist[i][k] + dist[k][j]);

        struct AddedEdge {
            int u, c, v;
        };
        vector<AddedEdge> added_edges;

        while (true) {
            // Count bad pairs
            vector<pair<int, int>> bad_pairs;
            for (int i = 0; i <= n; ++i) {
                for (int j = i + 1; j <= n; ++j) {
                    if (dist[i][j] > 3) {
                        bad_pairs.push_back({i, j});
                    }
                }
            }
            if (bad_pairs.empty()) break;

            int best_score = -1;
            AddedEdge best_move = {-1, -1, -1};
            
            // Build adjacency list/matrix for constructible check
            vector<vector<bool>> adj(n + 1, vector<bool>(n + 1, false));
            for(auto& e : edges) adj[e.first][e.second] = true;

            // Generate candidates: constructible edges not in G
            vector<tuple<int, int, int>> candidates;
            for (int u = 0; u <= n; ++u) {
                for (int c = u + 1; c <= n; ++c) {
                    if (adj[u][c]) {
                        for (int v = c + 1; v <= n; ++v) {
                            if (adj[c][v] && !adj[u][v]) {
                                candidates.emplace_back(u, c, v);
                            }
                        }
                    }
                }
            }

            // Evaluate candidates
            for (auto& cand : candidates) {
                int u = get<0>(cand);
                int v = get<2>(cand);
                
                int score = 0;
                // Heuristic score: number of bad pairs that become good
                for (auto& p : bad_pairs) {
                    int i = p.first;
                    int j = p.second;
                    // Check if new edge improves i->j to <= 3
                    // Path using u->v: i -> ... -> u -> v -> ... -> j
                    // Length: dist[i][u] + 1 + dist[v][j]
                    if (dist[i][u] + 1 + dist[v][j] <= 3) {
                        score++;
                    }
                }

                if (score > best_score) {
                    best_score = score;
                    best_move = {u, get<1>(cand), v};
                }
            }
            
            if (best_score <= 0) break; 

            // Apply best move
            added_edges.push_back(best_move);
            edges.push_back({best_move.u, best_move.v});
            int u = best_move.u;
            int v = best_move.v;
            
            // Update dist
            for (int i = 0; i <= n; ++i) {
                for (int j = 0; j <= n; ++j) {
                    dist[i][j] = min(dist[i][j], dist[i][u] + 1 + dist[v][j]);
                }
            }
        }

        cout << added_edges.size() << endl;
        for (auto& e : added_edges) {
            cout << e.u << " " << e.c << " " << e.v << endl;
        }

    } else {
        // Large N solution: Structured layers (Base 16)
        vector<int> targets;
        // Layers for digits 2..15
        for (int i = 2; i <= 15; ++i) if (i <= n) targets.push_back(i);
        // Layers for 16..240 (multiples of 16)
        for (int i = 16; i <= 240; i += 16) if (i <= n) targets.push_back(i);
        // Layers for 256..3840 (multiples of 256)
        for (int i = 256; i <= 3840; i += 256) if (i <= n) targets.push_back(i);
        
        sort(targets.begin(), targets.end());
        targets.erase(unique(targets.begin(), targets.end()), targets.end());
        
        struct Edge {
            int u, c, v;
        };
        vector<Edge> result;
        
        vector<int> available = {1};
        for (int t : targets) {
            int best_a = -1, best_b = -1;
            bool found = false;
            
            // Find constructible sum t = a + b
            for (int i = available.size() - 1; i >= 0; --i) {
                int a = available[i];
                int b = t - a;
                if (binary_search(available.begin(), available.end(), b)) {
                    best_a = b; best_b = a; 
                    found = true;
                    break;
                }
            }
            
            if (found) {
                int a = best_a;
                for (int u = 0; u <= n - t; ++u) {
                    result.push_back({u, u + a, u + t});
                }
                available.push_back(t);
                sort(available.begin(), available.end());
            }
        }
        
        cout << result.size() << endl;
        for (const auto& e : result) {
            cout << e.u << " " << e.c << " " << e.v << "\n";
        }
    }

    return 0;
}