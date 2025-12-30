#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <iomanip>
#include <ctime>

using namespace std;

// Global constants and data structures
const int MAXN = 200005;
struct Point {
    double x, y;
};

int N;
vector<Point> cities;
bool is_prime[MAXN];
vector<int> path;

// Precompute primes using Sieve of Eratosthenes
void sieve(int n) {
    fill(is_prime, is_prime + n + 1, true);
    is_prime[0] = is_prime[1] = false;
    for (int p = 2; p * p <= n; p++) {
        if (is_prime[p]) {
            for (int i = p * p; i <= n; i += p)
                is_prime[i] = false;
        }
    }
}

// Euclidean distance between two cities by ID
inline double dist(int i, int j) {
    double dx = cities[i].x - cities[j].x;
    double dy = cities[i].y - cities[j].y;
    return sqrt(dx * dx + dy * dy);
}

// Get penalty multiplier for a step
// step_idx: 1-based index of the step (1 to N)
// source_id: ID of the city where the step starts
inline double get_multiplier(int step_idx, int source_id) {
    if (step_idx % 10 == 0 && !is_prime[source_id]) return 1.1;
    return 1.0;
}

int main() {
    // Optimize I/O operations for speed
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> N)) return 0;

    cities.resize(N);
    for (int i = 0; i < N; ++i) {
        cin >> cities[i].x >> cities[i].y;
        // City IDs are implicitly 0..N-1 based on input order
    }

    // Precompute primes up to N-1 (max city ID)
    sieve(N);

    // Initial path construction: 0, 1, 2, ..., N-1, 0
    // This leverages the problem statement's hint that input is sorted by X.
    // This provides a spatially coherent initial tour, albeit with a long return edge.
    path.resize(N + 1);
    for (int i = 0; i < N; ++i) path[i] = i;
    path[N] = 0;

    // Optimization Parameters
    // We use a restricted window for 2-opt to keep complexity manageable for N=200,000
    int window = 60; 
    if (N < 1000) window = N; // Allow larger window for small instances
    
    clock_t start_time = clock();
    double time_limit = 1.9; // Safe margin within 2.0s limit

    // Phase 1: Windowed 2-opt Local Search
    // We iterate through the path and try to reverse segments path[i...j] 
    // if it reduces the total weighted distance (including penalties).
    bool improved = true;
    while (improved && (double)(clock() - start_time) / CLOCKS_PER_SEC < time_limit) {
        improved = false;
        // i starts at 1 and goes to N-2. path[0] and path[N] (both 0) are fixed.
        for (int i = 1; i < N - 1; ++i) { 
            if ((double)(clock() - start_time) / CLOCKS_PER_SEC > time_limit) break;
            
            int limit = min(N - 1, i + window);
            for (int j = i + 1; j <= limit; ++j) {
                // Candidate move: Reverse segment path[i...j]
                
                double current_cost = 0;
                double new_cost = 0;
                
                // Calculate cost of affected edges in current configuration
                // The steps affected are i, i+1, ..., j, j+1.
                // Step k connects path[k-1] to path[k].
                for (int k = i; k <= j + 1; ++k) {
                    current_cost += dist(path[k-1], path[k]) * get_multiplier(k, path[k-1]);
                }
                
                // Calculate cost if reversed
                // After reversal, the segment indices [i, j] contain the reversed sequence.
                
                // Step i: Connects path[i-1] (unchanged) -> path[j] (new node at i)
                new_cost += dist(path[i-1], path[j]) * get_multiplier(i, path[i-1]);
                
                // Internal steps i+1 to j
                // The edge at step k connects the new node at k-1 to the new node at k.
                // In a reversed segment [i, j], the node at index k maps to original path[i+j-k].
                // So step k connects path[i+j-(k-1)] -> path[i+j-k].
                for (int k = i + 1; k <= j; ++k) {
                    int u = path[i + j - (k - 1)];
                    int v = path[i + j - k];
                    new_cost += dist(u, v) * get_multiplier(k, u);
                }
                
                // Step j+1: Connects path[i] (new node at j) -> path[j+1] (unchanged)
                new_cost += dist(path[i], path[j+1]) * get_multiplier(j+1, path[i]);
                
                // Check if improvement found
                if (new_cost < current_cost - 1e-9) {
                    reverse(path.begin() + i, path.begin() + j + 1);
                    improved = true;
                }
            }
        }
    }
    
    // Phase 2: Targeted Prime Swaps
    // Specifically target steps that incur the 10% penalty (steps 10, 20, 30...)
    // If the source city is not prime, try to swap it with a nearby prime city.
    while ((double)(clock() - start_time) / CLOCKS_PER_SEC < time_limit) {
        bool local_imp = false;
        for (int t = 10; t <= N; t += 10) {
            int u_idx = t - 1; // Index in path for source of step t
            if (is_prime[path[u_idx]]) continue; // Already optimal for this step
            
            // Look for a prime to swap with in a small radius
            int search_rad = 50; 
            int start_k = max(1, u_idx - search_rad);
            int end_k = min(N - 1, u_idx + search_rad);
            
            double best_delta = 0;
            int best_k = -1;
            
            for (int k = start_k; k <= end_k; ++k) {
                if (k == u_idx) continue;
                if (!is_prime[path[k]]) continue; // Candidate must be prime
                
                int u = u_idx;
                int v = k;
                // Ensure u < v for consistent processing
                if (u > v) swap(u, v);
                
                // Identify all steps affected by swapping path[u] and path[v]
                // These are the edges incident to u and v, and the steps where u and v are sources.
                vector<int> steps;
                steps.push_back(u);
                steps.push_back(u+1);
                steps.push_back(v);
                steps.push_back(v+1);
                
                // Remove duplicates and invalid steps
                sort(steps.begin(), steps.end());
                steps.erase(unique(steps.begin(), steps.end()), steps.end());
                
                double cur_c = 0, new_c = 0;
                
                // Calc current local cost
                for (int s : steps) {
                    if (s >= 1 && s <= N)
                        cur_c += dist(path[s-1], path[s]) * get_multiplier(s, path[s-1]);
                }
                
                // Perform Swap
                swap(path[u], path[v]);
                
                // Calc new local cost
                for (int s : steps) {
                    if (s >= 1 && s <= N)
                        new_c += dist(path[s-1], path[s]) * get_multiplier(s, path[s-1]);
                }
                
                // Swap back to restore state
                swap(path[u], path[v]); 
                
                if (new_c < cur_c - 1e-9) {
                    if (new_c - cur_c < best_delta) {
                        best_delta = new_c - cur_c;
                        best_k = (u == u_idx ? v : u); // Determine which index was the candidate
                    }
                }
            }
            
            // Apply the best swap found for this penalty location
            if (best_k != -1) {
                swap(path[u_idx], path[best_k]);
                local_imp = true;
            }
        }
        if (!local_imp) break; 
    }

    // Output result
    cout << path.size() << "\n";
    for (int i = 0; i < path.size(); ++i) {
        cout << path[i] << "\n";
    }

    return 0;
}