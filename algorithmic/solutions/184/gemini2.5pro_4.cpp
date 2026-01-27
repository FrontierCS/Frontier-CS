#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <chrono>
#include <random>

// Global variables for convenience during repeated solves
int N;
std::vector<std::vector<int>> adj;
std::vector<int> initial_degree;

// State for a single run of the greedy algorithm
std::vector<bool> current_S;
int current_S_size;
std::vector<int> degree;
std::vector<bool> is_removed;

std::mt19937 rng;

void solve() {
    // Reset state for a new run
    std::fill(current_S.begin(), current_S.end(), false);
    std::fill(is_removed.begin(), is_removed.end(), false);
    degree = initial_degree;
    current_S_size = 0;

    int remaining_vertices = N;

    while (remaining_vertices > 0) {
        int min_deg = N; // Max possible degree is N-1
        
        // Find minimum degree among remaining vertices
        for (int i = 1; i <= N; ++i) {
            if (!is_removed[i]) {
                min_deg = std::min(min_deg, degree[i]);
            }
        }

        if (min_deg == N) { // All vertices processed or no vertices left
            break;
        }

        // Collect all candidates with min degree
        std::vector<int> candidates;
        for (int i = 1; i <= N; ++i) {
            if (!is_removed[i] && degree[i] == min_deg) {
                candidates.push_back(i);
            }
        }

        if (candidates.empty()) {
            break;
        }

        // Pick one candidate randomly
        int v_to_add = candidates[rng() % candidates.size()];

        current_S[v_to_add] = true;
        current_S_size++;
        
        // Collect vertices to remove: v_to_add and its neighbors
        std::vector<int> vertices_to_remove;
        if (!is_removed[v_to_add]) {
            is_removed[v_to_add] = true;
            vertices_to_remove.push_back(v_to_add);
        }
        for (int neighbor : adj[v_to_add]) {
            if (!is_removed[neighbor]) {
                is_removed[neighbor] = true;
                vertices_to_remove.push_back(neighbor);
            }
        }
        
        remaining_vertices -= vertices_to_remove.size();

        // Update degrees of affected vertices
        // These are neighbors of the just removed vertices
        for (int u : vertices_to_remove) {
            for (int neighbor : adj[u]) {
                if (!is_removed[neighbor]) {
                    degree[neighbor]--;
                }
            }
        }
    }
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    
    // Seed the random number generator
    rng.seed(std::chrono::steady_clock::now().time_since_epoch().count());
    
    int M_raw;
    std::cin >> N >> M_raw;
    
    std::vector<std::pair<int, int>> edges;
    edges.reserve(M_raw);
    for (int i = 0; i < M_raw; ++i) {
        int u, v;
        std::cin >> u >> v;
        if (u > v) std::swap(u, v);
        edges.push_back({u, v});
    }

    // Handle multiple edges and (u,v) vs (v,u)
    std::sort(edges.begin(), edges.end());
    edges.erase(std::unique(edges.begin(), edges.end()), edges.end());
    
    adj.resize(N + 1);
    for(const auto& edge : edges) {
        adj[edge.first].push_back(edge.second);
        adj[edge.second].push_back(edge.first);
    }

    // Pre-calculate initial degrees
    initial_degree.resize(N + 1);
    for(int i = 1; i <= N; ++i) {
        initial_degree[i] = adj[i].size();
    }
    
    // Allocate vectors for solver state
    current_S.resize(N + 1);
    degree.resize(N + 1);
    is_removed.resize(N + 1);
    
    std::vector<bool> best_S(N + 1, false);
    int max_S_size = 0;
    
    auto start_time = std::chrono::steady_clock::now();

    // Run the randomized greedy algorithm until time limit is approached
    while(true) {
        auto current_time = std::chrono::steady_clock::now();
        std::chrono::duration<double> elapsed_seconds = current_time - start_time;
        if (elapsed_seconds.count() > 1.95) {
            break;
        }

        solve();

        if (current_S_size > max_S_size) {
            max_S_size = current_S_size;
            best_S = current_S;
        }
    }
    
    for (int i = 1; i <= N; ++i) {
        std::cout << best_S[i] << "\n";
    }

    return 0;
}