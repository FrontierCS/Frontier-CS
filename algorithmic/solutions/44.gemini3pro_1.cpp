#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <ctime>
#include <iomanip>

using namespace std;

// Data structures
struct Point {
    int x, y;
    int id;
};

int N;
vector<Point> cities;
vector<bool> is_prime;
vector<int> tour;

// Sieve of Eratosthenes to identify prime city IDs
void sieve(int max_n) {
    is_prime.assign(max_n + 1, true);
    if (max_n >= 0) is_prime[0] = false;
    if (max_n >= 1) is_prime[1] = false;
    for (int p = 2; p * p <= max_n; p++) {
        if (is_prime[p]) {
            for (int i = p * p; i <= max_n; i += p)
                is_prime[i] = false;
        }
    }
}

// Squared Euclidean distance
inline long long dist_sq(int i, int j) {
    long long dx = cities[i].x - cities[j].x;
    long long dy = cities[i].y - cities[j].y;
    return dx * dx + dy * dy;
}

// Euclidean distance
inline double dist(int i, int j) {
    return sqrt((double)dist_sq(i, j));
}

// Striped initialization heuristic
// Since input is sorted by X, this pattern (0 -> 1 -> 3 -> ... -> last_odd -> last_even -> ... -> 4 -> 2 -> 0)
// minimizes the long return edge often found in naive sorted tours.
void init_tour_striped() {
    tour.resize(N + 1);
    tour[0] = 0;
    tour[N] = 0;
    
    int current = 1;
    // Odd indices from input (1, 3, 5...)
    for (int i = 1; i < N; i += 2) {
        tour[current++] = i;
    }
    // Even indices from input, backwards (..., 4, 2)
    int start_even = ((N - 1) % 2 == 0) ? (N - 1) : (N - 2);
    for (int i = start_even; i >= 2; i -= 2) {
        tour[current++] = i;
    }
}

// Calculate distance change for 2-opt move (reversing segment P[i...j])
// Neighbors: A=P[i-1], B=P[i], C=P[j], D=P[j+1]
// Old edges: (A,B), (C,D)
// New edges: (A,C), (B,D)
inline double delta_dist(int i, int j) {
    int A = tour[i-1];
    int B = tour[i];
    int C = tour[j];
    int D = tour[j+1];
    // We ignore penalty here for speed, assuming pure geometry dominates the large structure
    return (dist(A, C) + dist(B, D)) - (dist(A, B) + dist(C, D));
}

// Reverse segment in tour
void reverse_segment(int i, int j) {
    reverse(tour.begin() + i, tour.begin() + j + 1);
}

// Phase 1: Geometry Optimization (2-opt with spatial window)
void optimize_geometry(double time_limit) {
    int window = 150; // Window size for local search
    clock_t start_t = clock();
    bool improved = true;
    
    // Repeat 2-opt passes until time limit or local optimum
    while (improved) {
        if ((double)(clock() - start_t) / CLOCKS_PER_SEC > time_limit) break;
        improved = false;
        
        for (int i = 1; i < N - 1; ++i) {
            int limit = min(N - 1, i + window);
            for (int j = i + 1; j < limit; ++j) {
                if (delta_dist(i, j) < -1e-6) {
                    reverse_segment(i, j);
                    improved = true;
                }
            }
        }
    }
}

// Phase 2: Carrot Constraint Optimization
// Ensure P[k] is prime for k in {9, 19, 29...} where possible
void optimize_carrot(double time_limit) {
    clock_t start_t = clock();
    
    // Check every 10th position (index 9, 19...)
    // Index 9 is the source of step 10.
    for (int i = 9; i < N; i += 10) {
        if ((double)(clock() - start_t) / CLOCKS_PER_SEC > time_limit) break;
        
        // If already prime, no penalty for step i+1
        if (is_prime[tour[i]]) continue;

        // Try to swap tour[i] with a nearby prime tour[j]
        int best_j = -1;
        double best_delta = 0.0;
        
        int search_radius = 80;
        int start_search = max(1, i - search_radius);
        int end_search = min(N - 1, i + search_radius);
        
        for (int j = start_search; j <= end_search; ++j) {
            if (i == j) continue;
            // Target must be prime to remove penalty at step i+1
            if (!is_prime[tour[j]]) continue;
            
            // Calculate change in weighted length including penalties
            // Affected steps: i, i+1, j, j+1 (1-based indices)
            
            double current_cost = 0;
            double new_cost = 0;
            
            // Unique step indices to evaluate
            vector<int> steps = {i, i+1, j, j+1};
            sort(steps.begin(), steps.end());
            steps.erase(unique(steps.begin(), steps.end()), steps.end());
            
            // Helper to calc cost of specific steps
            auto calc_partial = [&](const vector<int>& pts) {
                double c = 0;
                for (int step : pts) {
                    if (step > N) continue; // Boundary check
                    int u = tour[step-1];
                    int v = tour[step];
                    double d = dist(u, v);
                    // Penalty check: step t is penalized if t%10==0 and source u is not prime
                    if (step % 10 == 0 && !is_prime[u]) d *= 1.1;
                    c += d;
                }
                return c;
            };
            
            current_cost = calc_partial(steps);
            
            // Perform swap
            swap(tour[i], tour[j]);
            
            new_cost = calc_partial(steps);
            
            double delta = new_cost - current_cost;
            if (delta < best_delta) { // Only accept strict improvement
                best_delta = delta;
                best_j = j;
            }
            
            // Revert swap for next iteration
            swap(tour[i], tour[j]);
        }
        
        if (best_j != -1) {
            swap(tour[i], tour[best_j]);
        }
    }
}

int main() {
    // Fast IO
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> N)) return 0;
    
    cities.resize(N);
    for (int i = 0; i < N; ++i) {
        cin >> cities[i].x >> cities[i].y;
        cities[i].id = i;
    }

    // Precompute primes
    sieve(N + 50);

    // Initial solution using striped heuristic
    init_tour_striped();

    // Optimization passes
    // Phase 1: Pure geometry (Euclidean TSP)
    optimize_geometry(1.6);
    
    // Phase 2: Carrot constraint (Prime positioning)
    optimize_carrot(1.95);

    // Output
    cout << tour.size() << "\n";
    for (int id : tour) {
        cout << id << "\n";
    }

    return 0;
}