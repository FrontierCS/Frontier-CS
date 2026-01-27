#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <chrono>
#include <random>

// A fast I/O routine
void fast_io() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
}

// A simple and fast random number generator
struct XorShift {
    unsigned int x, y, z, w;
    XorShift() : x(123456789), y(362436069), z(521288629), w(88675123) {}
    unsigned int next() {
        unsigned int t = x ^ (x << 11);
        x = y; y = z; z = w;
        return w = (w ^ (w >> 19)) ^ (t ^ (t >> 8));
    }
    unsigned int next_int(int n) {
        if (n <= 0) return 0;
        return next() % n;
    }
};

int main() {
    fast_io();
    auto start_time = std::chrono::high_resolution_clock::now();

    int n;
    int m;
    std::cin >> n >> m;

    std::vector<std::vector<int>> adj(n);
    for (int i = 0; i < m; ++i) {
        int u, v;
        std::cin >> u >> v;
        --u; --v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }
    
    // Handle multiple edges and compute initial degrees
    std::vector<int> initial_degree(n);
    for(int i=0; i<n; ++i) {
        std::sort(adj[i].begin(), adj[i].end());
        adj[i].erase(std::unique(adj[i].begin(), adj[i].end()), adj[i].end());
        initial_degree[i] = adj[i].size();
    }


    std::vector<bool> best_solution(n, false);
    int max_k = 0;

    XorShift rng;

    std::vector<int> current_degree(n);
    std::vector<std::vector<int>> D(n);
    std::vector<int> pos(n);
    std::vector<int> where(n);
    std::vector<int> ordering(n);
    std::vector<bool> selected(n);

    // Main loop: run the randomized heuristic multiple times until time limit
    while (true) {
        auto current_time = std::chrono::high_resolution_clock::now();
        std::chrono::duration<double> elapsed = current_time - start_time;
        if (elapsed.count() > 1.95) { // Leave a small margin for safety
            break;
        }

        // --- Phase 1: Randomized Degeneracy Ordering ---
        current_degree = initial_degree;
        for(int i=0; i<n; ++i) {
            if(!D[i].empty()) D[i].clear();
        }
        
        for (int i = 0; i < n; ++i) {
            D[current_degree[i]].push_back(i);
            pos[i] = D[current_degree[i]].size() - 1;
            where[i] = current_degree[i];
        }

        int min_deg = 0;
        for (int i = 0; i < n; ++i) {
            while (min_deg < n && D[min_deg].empty()) {
                min_deg++;
            }
            if(min_deg >= n) break;

            int rand_idx = rng.next_int(D[min_deg].size());
            int v = D[min_deg][rand_idx];

            // Remove v from its bucket using swap-with-back
            int last_v_in_bucket = D[min_deg].back();
            D[min_deg][rand_idx] = last_v_in_bucket;
            pos[last_v_in_bucket] = rand_idx;
            D[min_deg].pop_back();
            
            ordering[i] = v;
            where[v] = -1; // Mark as removed

            for (int u : adj[v]) {
                if (where[u] != -1) {
                    int d = where[u];
                    
                    // Remove u from its bucket D[d] using swap-with-back
                    int last_u_in_bucket = D[d].back();
                    int p_u = pos[u];
                    D[d][p_u] = last_u_in_bucket;
                    pos[last_u_in_bucket] = p_u;
                    D[d].pop_back();

                    // Add u to bucket D[d-1]
                    d--;
                    where[u] = d;
                    D[d].push_back(u);
                    pos[u] = D[d].size() - 1;

                    if (d < min_deg) {
                        min_deg = d;
                    }
                }
            }
        }

        // --- Phase 2: Construct Independent Set ---
        std::fill(selected.begin(), selected.end(), false);
        int current_k = 0;
        for (int i = n - 1; i >= 0; --i) {
            int v = ordering[i];
            bool can_select = true;
            for (int u : adj[v]) {
                if (selected[u]) {
                    can_select = false;
                    break;
                }
            }
            if (can_select) {
                selected[v] = true;
                current_k++;
            }
        }
        
        if (current_k > max_k) {
            max_k = current_k;
            best_solution = selected;
        }
    }

    // Fallback in case no solution was found (e.g., extremely short time limit).
    if (max_k == 0) {
        std::vector<int> p(n);
        std::iota(p.begin(), p.end(), 0);
        std::sort(p.begin(), p.end(), [&](int i, int j){
            return initial_degree[i] < initial_degree[j];
        });
        
        std::vector<bool> removed(n, false);
        for(int v : p) {
            if (!removed[v]) {
                best_solution[v] = true;
                removed[v] = true;
                for(int u : adj[v]) {
                    removed[u] = true;
                }
            }
        }
    }

    for (int i = 0; i < n; ++i) {
        std::cout << (best_solution[i] ? 1 : 0) << "\n";
    }

    return 0;
}