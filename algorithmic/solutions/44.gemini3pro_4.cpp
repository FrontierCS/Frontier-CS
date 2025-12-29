#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <numeric>
#include <ctime>
#include <iomanip>
#include <random>

using namespace std;

// Fast IO
void fast_io() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
}

// Global data
int N;
struct City {
    int id;
    int x, y;
};
vector<City> cities;
vector<bool> is_prime;

// Sieve to precompute primes up to N
void sieve(int max_n) {
    is_prime.assign(max_n + 1, true);
    is_prime[0] = is_prime[1] = false;
    for (int p = 2; p * p <= max_n; p++) {
        if (is_prime[p]) {
            for (int i = p * p; i <= max_n; i += p)
                is_prime[i] = false;
        }
    }
}

// Euclidean distance
inline double dist(int i, int j) {
    long long dx = (long long)cities[i].x - cities[j].x;
    long long dy = (long long)cities[i].y - cities[j].y;
    return std::sqrt(dx * dx + dy * dy);
}

// Check if a step gets a penalty
// k is the index in the tour array from which the step starts.
// The step is from tour[k] to tour[k+1]. This is the (k+1)-th step.
// Penalty applies if step number is multiple of 10 and starting city is not prime.
inline double get_multiplier(int k, int city_id) {
    if ((k + 1) % 10 == 0 && !is_prime[city_id]) return 1.1;
    return 1.0;
}

int main() {
    fast_io();

    if (!(cin >> N)) return 0;
    cities.resize(N);
    for (int i = 0; i < N; ++i) {
        cin >> cities[i].x >> cities[i].y;
        cities[i].id = i;
    }

    sieve(N);

    // Initial Tour Construction: Double Sweep
    // Since points are sorted by X, we visit evens increasing and odds decreasing
    // to form a bitonic-like tour which is generally efficient.
    vector<int> tour;
    tour.reserve(N + 1);
    tour.push_back(0);
    for (int i = 2; i < N; i += 2) tour.push_back(i);
    for (int i = (N % 2 == 0 ? N - 1 : N - 2); i >= 1; i -= 2) tour.push_back(i);
    tour.push_back(0);

    // Timing
    clock_t start_time = clock();
    double time_limit = 1.95; 

    // Phase 1: Windowed 2-opt for geometric optimization
    // We ignore penalties here to quickly untangle the path.
    // Limit iterations and window size for speed.
    int window = 100;
    for (int iter = 0; iter < 2; ++iter) {
        bool improved = false;
        for (int i = 1; i < N - 2; ++i) {
            int limit = min(N - 2, i + window);
            for (int j = i + 1; j <= limit; ++j) {
                int A = tour[i-1];
                int B = tour[i];
                int C = tour[j];
                int D = tour[j+1];
                
                double d_old = dist(A, B) + dist(C, D);
                double d_new = dist(A, C) + dist(B, D);
                
                if (d_new < d_old) {
                    reverse(tour.begin() + i, tour.begin() + j + 1);
                    improved = true;
                }
            }
        }
        if (!improved) break;
        if ((double)(clock() - start_time) / CLOCKS_PER_SEC > 0.8) break;
    }

    // Phase 2: Simulated Annealing with Swaps
    // Optimize for both distance and penalty constraints.
    mt19937 rng(1337);
    vector<int> penalty_indices;
    for (int k = 9; k < N; k += 10) penalty_indices.push_back(k);

    double T = 1.0;
    double cooling = 0.9999;
    
    // Helper to calculate cost of a specific step index
    auto calc_segment = [&](int idx) -> double {
        if (idx < 0 || idx >= N) return 0.0;
        return dist(tour[idx], tour[idx+1]) * get_multiplier(idx, tour[idx]);
    };

    while ((double)(clock() - start_time) / CLOCKS_PER_SEC < time_limit) {
        int i, j;
        
        // Selection Strategy
        // 50% chance: Try to fix a penalty index
        // 50% chance: Random improvement
        bool try_penalty = (!penalty_indices.empty() && (rng() % 100 < 50));
        
        if (try_penalty) {
            int idx = rng() % penalty_indices.size();
            i = penalty_indices[idx];
            // If already prime, mostly skip to save iterations for bad spots
            if (is_prime[tour[i]] && (rng() % 100 < 90)) {
                i = 1 + rng() % (N - 1);
            }
        } else {
            i = 1 + rng() % (N - 1);
        }

        // Pick j: mostly local for geometry preservation, sometimes global
        if (rng() % 100 < 95) {
            int range = 250;
            int offset = (int)(rng() % (2 * range + 1)) - range;
            j = i + offset;
            if (j < 1) j = 1;
            if (j > N - 1) j = N - 1;
        } else {
            j = 1 + rng() % (N - 1);
        }

        if (i == j) continue;
        if (i > j) swap(i, j);

        // Calculate Delta Cost
        // We only re-evaluate edges and penalties involving i and j
        double delta = 0;
        
        // Identify affected steps (start indices of steps)
        // Changing tour[i] affects steps i-1 (source fixed, dest changed) and i (source changed, dest fixed)
        // Also multiplier of step i depends on tour[i-1] (fixed)
        // Multiplier of step i+1 depends on tour[i] (changed)
        // So steps indices: i-1, i. 
        // Same for j: j-1, j.
        
        // Wait, multiplier check for step k depends on tour[k-1].
        // My get_multiplier(k, id) checks if step k+1 has penalty based on id at k.
        // So step index k uses multiplier based on tour[k].
        // Thus, changing tour[i] changes:
        // 1. Distance of step i-1 (tour[i-1]->tour[i])
        // 2. Distance of step i (tour[i]->tour[i+1])
        // 3. Multiplier of step i (based on tour[i])
        // Multiplier of step i-1 is based on tour[i-1] (unchanged).
        
        // Indices of steps to recalculate: i-1, i, j-1, j.
        vector<int> steps = {i-1, i, j-1, j};
        
        // Handle adjacency and duplicates
        sort(steps.begin(), steps.end());
        steps.erase(unique(steps.begin(), steps.end()), steps.end());
        
        // Subtract old costs
        for (int s : steps) delta -= calc_segment(s);
        
        // Apply swap
        swap(tour[i], tour[j]);
        
        // Add new costs
        for (int s : steps) delta += calc_segment(s);
        
        // Acceptance
        bool accept = (delta < 0);
        if (!accept) {
            // Metropolis criterion
            // Use multiplication to avoid small double comparison issues
            if (exp(-delta / T) * 4294967296.0 > rng()) accept = true;
        }

        if (!accept) {
            swap(tour[i], tour[j]); // Revert
        }

        T *= cooling;
        if (T < 1e-4) T = 0.5; // Reheat
    }

    // Output
    cout << N + 1 << "\n";
    for (int k = 0; k <= N; ++k) {
        cout << tour[k] << "\n";
    }

    return 0;
}