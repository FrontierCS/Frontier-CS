#include <iostream>
#include <vector>
#include <algorithm>
#include <chrono>
#include <random>

using namespace std;

// Fast I/O
void fast_io() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
}

struct Edge {
    int u, v;
};

int N, M;
vector<Edge> all_edges;
vector<vector<int>> adj;

// Global Best
vector<int> best_solution;
int best_k = 2147483647;

// Time control
auto start_time = chrono::high_resolution_clock::now();
double TIME_LIMIT = 1.90; // Leave a small buffer for safety

bool check_time() {
    auto current_time = chrono::high_resolution_clock::now();
    chrono::duration<double> elapsed = current_time - start_time;
    return elapsed.count() < TIME_LIMIT;
}

int main() {
    fast_io();

    if (!(cin >> N >> M)) return 0;

    adj.resize(N + 1);
    all_edges.reserve(M);

    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        all_edges.push_back({u, v});
        adj[u].push_back(i);
        adj[v].push_back(i);
    }

    // Initialize RNG
    mt19937 rng(1337); 
    rng.seed(chrono::steady_clock::now().time_since_epoch().count());

    // Preallocate memory for working arrays to avoid re-allocation in loop
    vector<bool> in_cover(N + 1);
    vector<bool> edge_covered(M);
    vector<int> dynamic_degree(N + 1);
    vector<int> uncovered_edges(M);
    vector<int> edge_map(M);
    vector<int> current_cover_list;
    current_cover_list.reserve(N);

    // Initial dummy solution
    best_solution.assign(N + 1, 1);
    best_k = N;

    bool first = true;
    while (first || check_time()) {
        first = false;

        // Reset state
        fill(in_cover.begin(), in_cover.end(), false);
        fill(edge_covered.begin(), edge_covered.end(), false);
        
        for (int i = 0; i < M; ++i) {
            uncovered_edges[i] = i;
            edge_map[i] = i;
        }
        int uncovered_count = M;

        for (int i = 1; i <= N; ++i) {
            dynamic_degree[i] = (int)adj[i].size();
        }

        current_cover_list.clear();
        int current_k = 0;

        // Construction Phase: Randomized Greedy with Tournament Selection
        while (uncovered_count > 0) {
            int best_v = -1;
            int max_d = -1;

            // Tournament size
            int tournament_size = 3; 
            for (int t = 0; t < tournament_size; ++t) {
                int rand_idx = rng() % uncovered_count;
                int edge_idx = uncovered_edges[rand_idx];
                int u = all_edges[edge_idx].u;
                int v = all_edges[edge_idx].v;
                
                if (dynamic_degree[u] > max_d) {
                    max_d = dynamic_degree[u];
                    best_v = u;
                }
                if (dynamic_degree[v] > max_d) {
                    max_d = dynamic_degree[v];
                    best_v = v;
                }
            }

            // Ensure we picked something
            if (best_v == -1) { 
                int edge_idx = uncovered_edges[0];
                best_v = all_edges[edge_idx].u;
            }

            // Add best_v to cover
            if (!in_cover[best_v]) {
                in_cover[best_v] = true;
                current_cover_list.push_back(best_v);
                current_k++;
            }

            // Update state: cover incident edges
            for (int e_id : adj[best_v]) {
                if (!edge_covered[e_id]) {
                    edge_covered[e_id] = true;

                    // Remove from uncovered_edges using swap with last
                    int pos = edge_map[e_id];
                    int last_eid = uncovered_edges[uncovered_count - 1];
                    uncovered_edges[pos] = last_eid;
                    edge_map[last_eid] = pos;
                    uncovered_count--;

                    // Decrement degree of the other endpoint
                    int neighbor = (all_edges[e_id].u == best_v) ? all_edges[e_id].v : all_edges[e_id].u;
                    dynamic_degree[neighbor]--;
                }
            }
            dynamic_degree[best_v] = 0; 
        }

        // Pruning Phase: Remove Redundant Vertices
        // A vertex is redundant if all its neighbors are in the cover.
        // We iterate in random order to find a Maximal Independent Set of removals.
        shuffle(current_cover_list.begin(), current_cover_list.end(), rng);

        for (int v : current_cover_list) {
            bool needed = false;
            for (int e_id : adj[v]) {
                int neighbor = (all_edges[e_id].u == v) ? all_edges[e_id].v : all_edges[e_id].u;
                if (!in_cover[neighbor]) {
                    needed = true;
                    break;
                }
            }
            if (!needed) {
                in_cover[v] = false;
                current_k--;
            }
        }

        // Update Global Best
        if (current_k < best_k) {
            best_k = current_k;
            best_solution.assign(N + 1, 0);
            for (int i = 1; i <= N; ++i) {
                if(in_cover[i]) best_solution[i] = 1;
            }
        }
    }

    // Output result
    for (int i = 1; i <= N; ++i) {
        cout << best_solution[i] << "\n";
    }

    return 0;
}