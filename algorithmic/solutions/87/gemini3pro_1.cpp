#include <iostream>
#include <vector>
#include <queue>
#include <algorithm>
#include <random>
#include <map>

using namespace std;

const int INF = 1e9;

int n, m;
vector<int> initial_colors;
vector<int> target_colors;
vector<vector<int>> adj;
vector<int> dist0, dist1;

// BFS to compute distances to nearest node of specific color
void bfs(int color, vector<int>& dist) {
    dist.assign(n + 1, INF);
    queue<int> q;
    for (int i = 1; i <= n; ++i) {
        if (initial_colors[i - 1] == color) {
            dist[i] = 0;
            q.push(i);
        }
    }
    while (!q.empty()) {
        int u = q.front();
        q.pop();
        for (int v : adj[u]) {
            if (dist[v] == INF) {
                dist[v] = dist[u] + 1;
                q.push(v);
            }
        }
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> n >> m)) return 0;

    initial_colors.resize(n);
    for (int i = 0; i < n; ++i) cin >> initial_colors[i];

    target_colors.resize(n);
    for (int i = 0; i < n; ++i) cin >> target_colors[i];

    adj.resize(n + 1);
    for (int i = 1; i <= n; ++i) adj[i].push_back(i); // Self-loops

    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    bfs(0, dist0);
    bfs(1, dist1);

    // Particles: p[i] stores the current location of the particle originating from node i
    vector<int> p(n + 1);
    for (int i = 1; i <= n; ++i) p[i] = i;

    // We store the mapping M_t for each step.
    // M_t[u] is the node where particles currently at u move to.
    vector<vector<int>> maps;

    mt19937 rng(1337);

    int max_steps = 20000;
    
    int no_progress_count = 0;
    long long last_total_dist = -1;

    while (true) {
        // Calculate total distance to targets
        long long total_dist = 0;
        bool done = true;
        for (int i = 1; i <= n; ++i) {
            int t = target_colors[i - 1];
            int current_node = p[i];
            int d = (t == 0 ? dist0[current_node] : dist1[current_node]);
            total_dist += d;
            if (d > 0) done = false;
        }

        if (done) break;
        if (maps.size() >= max_steps) break;

        if (total_dist == last_total_dist) {
            no_progress_count++;
        } else {
            no_progress_count = 0;
            last_total_dist = total_dist;
        }

        // If stuck, try randomized moves
        bool random_kick = (no_progress_count > 20);

        // Identify currently occupied nodes and the type of particles they hold
        // 0 for target black, 1 for target white
        map<int, int> node_type;
        vector<int> occupied_nodes;
        
        for (int i = 1; i <= n; ++i) {
            int u = p[i];
            int t = target_colors[i - 1];
            if (node_type.find(u) == node_type.end()) {
                node_type[u] = t;
                occupied_nodes.push_back(u);
            }
        }

        vector<int> best_moves;
        long long best_dist_after = -1;
        
        int trials = (random_kick ? 50 : 20); // More trials if stuck
        
        for (int tr = 0; tr < trials; ++tr) {
            vector<int> current_moves(n + 1, 0); 
            vector<int> reserved(n + 1, -1); 
            bool possible = true;
            
            // Shuffle to vary the order of reservations
            shuffle(occupied_nodes.begin(), occupied_nodes.end(), rng);

            for (int u : occupied_nodes) {
                int type = node_type[u];
                vector<int> candidates = adj[u];
                
                if (!random_kick) {
                    // Greedy sort: prefer neighbors closer to target
                    sort(candidates.begin(), candidates.end(), [&](int a, int b) {
                        int da = (type == 0 ? dist0[a] : dist1[a]);
                        int db = (type == 0 ? dist0[b] : dist1[b]);
                        // Add some randomness for equal distances
                        if (da == db) return (a ^ tr) < (b ^ tr); 
                        return da < db;
                    });
                } else {
                    shuffle(candidates.begin(), candidates.end(), rng);
                }

                int chosen = -1;
                for (int v : candidates) {
                    if (reserved[v] != -1 && reserved[v] != type) continue;
                    chosen = v;
                    break;
                }

                if (chosen == -1) {
                    possible = false;
                    break;
                }
                
                current_moves[u] = chosen;
                reserved[chosen] = type;
            }

            if (possible) {
                // For unoccupied nodes, stay put (or move anywhere, doesn't matter)
                for(int i = 1; i <= n; ++i) if (current_moves[i] == 0) current_moves[i] = i;

                long long d = 0;
                for(int i = 1; i <= n; ++i) {
                    int next_pos = current_moves[p[i]];
                    int t = target_colors[i-1];
                    d += (t == 0 ? dist0[next_pos] : dist1[next_pos]);
                }

                if (best_dist_after == -1 || d < best_dist_after) {
                    best_dist_after = d;
                    best_moves = current_moves;
                }
                
                if (!random_kick && d < total_dist) break; 
            }
        }
        
        if (best_dist_after != -1) {
            maps.push_back(best_moves);
            for (int i = 1; i <= n; ++i) {
                p[i] = best_moves[p[i]];
            }
            if (random_kick && best_dist_after < total_dist) no_progress_count = 0;
        } else {
            // If all trials failed (should be rare), just count as no progress
            no_progress_count++;
        }
    }

    cout << maps.size() << "\n";
    
    // Print initial state
    for (int i = 0; i < n; ++i) cout << initial_colors[i] << (i == n - 1 ? "" : " ");
    cout << "\n";

    vector<int> current_c = initial_colors;
    
    // Apply maps in reverse order to reconstruct the sequence of colorings
    reverse(maps.begin(), maps.end());

    for (const auto& m_map : maps) {
        vector<int> next_c(n);
        for (int i = 0; i < n; ++i) {
            // Node i+1 updates its color from neighbor m_map[i+1]
            // m_map is 1-based, current_c is 0-based
            int neighbor = m_map[i + 1];
            next_c[i] = current_c[neighbor - 1];
        }
        current_c = next_c;
        for (int i = 0; i < n; ++i) cout << current_c[i] << (i == n - 1 ? "" : " ");
        cout << "\n";
    }

    return 0;
}