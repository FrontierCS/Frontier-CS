#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>

using namespace std;

// Data structures
struct Point {
    int id;
    long long x, y;
};

// Global variables
int N;
vector<Point> cities;
vector<int> tour;
vector<bool> is_prime;

// Euclidean distance calculation
inline double dist(int i, int j) {
    long long dx = cities[i].x - cities[j].x;
    long long dy = cities[i].y - cities[j].y;
    return std::sqrt(dx * dx + dy * dy);
}

// Sieve of Eratosthenes to mark primes
void sieve(int n) {
    is_prime.assign(n + 1, true);
    if (n >= 0) is_prime[0] = false;
    if (n >= 1) is_prime[1] = false;
    for (int p = 2; p * p <= n; p++) {
        if (is_prime[p]) {
            for (int i = p * p; i <= n; i += p)
                is_prime[i] = false;
        }
    }
}

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> N)) return 0;
    cities.resize(N);
    for (int i = 0; i < N; ++i) {
        cities[i].id = i;
        cin >> cities[i].x >> cities[i].y;
    }

    // Precompute primes
    sieve(N);

    // Initial construction: Bitonic-like tour based on sorted X coordinates
    // Visit evens in increasing order, then odds in decreasing order
    tour.reserve(N + 1);
    tour.push_back(0);
    for (int i = 2; i < N; i += 2) {
        tour.push_back(i);
    }
    for (int i = N - 1; i >= 1; --i) {
        if (i % 2 != 0) tour.push_back(i);
    }
    tour.push_back(0);

    // Optimization Phase: Windowed 2-opt with penalty awareness
    // We limit the window size to keep complexity linear O(N * W * Passes)
    int W = 50; 
    int max_passes = 6; 
    int passes = 0;
    bool improved = true;

    while (improved && passes < max_passes) {
        improved = false;
        passes++;

        // Iterate through all possible start points of the segment
        for (int i = 1; i < N - 1; ++i) {
            int max_j = min(N - 1, i + W);
            // Try reversing segment tour[i...j]
            for (int j = i + 1; j <= max_j; ++j) {
                
                double delta = 0.0;

                // 1. Calculate change for boundary edges
                
                // Entry edge: Step i. Source P[i-1] (fixed). Target P[i] becomes P[j].
                // Step index: i
                bool pen_entry = (i % 10 == 0 && !is_prime[tour[i-1]]);
                double mult_entry = pen_entry ? 1.1 : 1.0;
                double d_entry_old = dist(tour[i-1], tour[i]);
                double d_entry_new = dist(tour[i-1], tour[j]);
                delta += (d_entry_new - d_entry_old) * mult_entry;

                // Exit edge: Step j+1. Source P[j] becomes P[i]. Target P[j+1] (fixed).
                // Step index: j+1
                bool step_exit_is_10 = ((j + 1) % 10 == 0);
                double d_exit_old = dist(tour[j], tour[j+1]);
                double d_exit_new = dist(tour[i], tour[j+1]);
                
                if (step_exit_is_10) {
                    double mult_old = (!is_prime[tour[j]]) ? 1.1 : 1.0;
                    double mult_new = (!is_prime[tour[i]]) ? 1.1 : 1.0;
                    delta -= d_exit_old * mult_old;
                    delta += d_exit_new * mult_new;
                } else {
                    delta += (d_exit_new - d_exit_old);
                }

                // 2. Calculate change for internal steps
                // The set of edges is preserved (reversed), so base distances are same.
                // We only need to account for multiplier changes on these edges.
                // Steps affected: t from i+1 to j.
                // Check only multiples of 10.
                int start_t = ((i + 1 + 9) / 10) * 10;
                for (int t = start_t; t <= j; t += 10) {
                    // Original edge at step t: P[t-1] -> P[t]
                    int u_old = tour[t-1];
                    int v_old = tour[t];
                    double d_edge = dist(u_old, v_old);
                    
                    // In reversed segment, P_new[t-1] comes from P_old[i+j-(t-1)]
                    int u_new = tour[i + j - (t - 1)];
                    
                    double m_old = (!is_prime[u_old]) ? 1.1 : 1.0;
                    double m_new = (!is_prime[u_new]) ? 1.1 : 1.0;
                    
                    if (m_new != m_old) {
                        delta += d_edge * (m_new - m_old);
                    }
                }

                // If improvement found, apply move
                if (delta < -1e-7) {
                    reverse(tour.begin() + i, tour.begin() + j + 1);
                    improved = true;
                }
            }
        }
    }

    // Output result
    cout << tour.size() << "\n";
    for (size_t i = 0; i < tour.size(); ++i) {
        cout << tour[i] << "\n";
    }

    return 0;
}