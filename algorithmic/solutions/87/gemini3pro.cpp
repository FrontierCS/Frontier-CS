#include <iostream>
#include <vector>
#include <queue>
#include <algorithm>
#include <map>
#include <random>

using namespace std;

const int INF = 1e9;

int n, m;
vector<int> initial_colors;
vector<int> target_colors;
vector<vector<int>> adj;
vector<int> dist0, dist1;

// Standard BFS to compute distances from a set of source nodes
void bfs(const vector<int>& sources, vector<int>& dist) {
    fill(dist.begin(), dist.end(), INF);
    queue<int> q;
    for (int u : sources) {
        dist[u] = 0;
        q.push(u);
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
    vector<int> sources0, sources1;
    for (int i = 0; i < n; ++i) {
        cin >> initial_colors[i];
        if (initial_colors[i] == 0) sources0.push_back(i);
        else sources1.push_back(i);
    }

    target_colors.resize(n);
    // current_particles maps node_index -> required_color_type (0 or 1)
    map<int, int> current_particles; 
    for (int i = 0; i < n; ++i) {
        cin >> target_colors[i];
        current_particles[i] = target_colors[i];
    }

    adj.resize(n);
    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    dist0.resize(n);
    dist1.resize(n);
    bfs(sources0, dist0);
    bfs(sources1, dist1);

    // Stores the transformation mappings for each step.
    // history[0] is the mapping from Target state to the state 1 step before Target.
    vector<vector<int>> history;
    mt19937 rng(1337);

    int steps = 0;
    while (steps < 20000) {
        // Check if all particles are at valid sources
        bool done = true;
        for (auto const& [u, type] : current_particles) {
            int d = (type == 0) ? dist0[u] : dist1[u];
            if (d > 0) {
                done = false;
                break;
            }
        }
        if (done) break;

        steps++;
        vector<int> mapping(n); 
        // Default mapping: node stays at itself (copy from self)
        for(int i=0; i<n; ++i) mapping[i] = i;

        vector<int> nodes;
        for (auto const& [u, type] : current_particles) {
            nodes.push_back(u);
        }

        // Retry loop to resolve conflicts via random shuffling
        while (true) {
            bool success = true;
            map<int, int> next_occupied; // node -> type reserved
            map<int, int> current_moves; // u -> v

            // Shuffle active particles to vary processing order
            shuffle(nodes.begin(), nodes.end(), rng);

            // Sort roughly by distance to prioritize particles far from sources
            sort(nodes.begin(), nodes.end(), [&](int a, int b) {
                int typeA = current_particles[a];
                int distA = (typeA == 0) ? dist0[a] : dist1[a];
                int typeB = current_particles[b];
                int distB = (typeB == 0) ? dist0[b] : dist1[b];
                return distA > distB;
            });

            for (int u : nodes) {
                int type = current_particles[u];
                int best_v = -1;
                
                // Candidates: neighbors + self
                vector<int> candidates = adj[u];
                candidates.push_back(u);
                
                // Shuffle candidates for tie-breaking
                shuffle(candidates.begin(), candidates.end(), rng);

                // Find valid candidates (not occupied by opposite type)
                vector<pair<int, int>> valid_candidates;
                for (int v : candidates) {
                    if (next_occupied.count(v) && next_occupied[v] != type) continue;
                    int d = (type == 0) ? dist0[v] : dist1[v];
                    valid_candidates.push_back({d, v});
                }

                if (valid_candidates.empty()) {
                    success = false;
                    break;
                }

                // Pick best candidate (smallest distance)
                sort(valid_candidates.begin(), valid_candidates.end());
                best_v = valid_candidates[0].second;

                current_moves[u] = best_v;
                next_occupied[best_v] = type;
            }

            if (success) {
                map<int, int> next_particles;
                for (auto const& [u, v] : current_moves) {
                    mapping[u] = v;
                    next_particles[v] = current_particles[u];
                }
                current_particles = next_particles;
                history.push_back(mapping);
                break;
            }
            // If failed, loop continues and reshuffles
        }
    }

    // Output solution
    cout << history.size() << "\n";
    
    // Print Initial State
    for (int i = 0; i < n; ++i) cout << initial_colors[i] << (i == n-1 ? "" : " ");
    cout << "\n";

    // Reconstruct states from Initial to Target
    vector<int> current_state = initial_colors;
    int K = history.size();
    for (int t = 1; t <= K; ++t) {
        vector<int> next_state(n);
        // We apply mappings in reverse order of history generation
        const vector<int>& P = history[K - t];
        for (int i = 0; i < n; ++i) {
            next_state[i] = current_state[P[i]];
        }
        for (int i = 0; i < n; ++i) cout << next_state[i] << (i == n-1 ? "" : " ");
        cout << "\n";
        current_state = next_state;
    }

    return 0;
}