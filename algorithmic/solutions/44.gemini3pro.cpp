#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <chrono>
#include <random>

using namespace std;

// Data structures
struct City {
    int id;
    int x, y;
};

int N;
vector<City> cities;
vector<int> path; // size N+1
vector<bool> is_prime;

// Helper for Euclidean distance
inline double get_dist(int id1, int id2) {
    long long dx = cities[id1].x - cities[id2].x;
    long long dy = cities[id1].y - cities[id2].y;
    return std::sqrt((double)dx * dx + (double)dy * dy);
}

// Helper for penalty multiplier
// step_idx is 1-based index of the step
// source_id is the ID of the city at step_idx-1
inline double get_multiplier(int step_idx, int source_id) {
    if (step_idx % 10 == 0 && !is_prime[source_id]) return 1.1;
    return 1.0;
}

int main() {
    // Fast I/O
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> N)) return 0;

    cities.resize(N);
    for (int i = 0; i < N; ++i) {
        cities[i].id = i; 
        cin >> cities[i].x >> cities[i].y;
    }

    // Precompute primes using Sieve
    is_prime.assign(N + 1, true);
    is_prime[0] = is_prime[1] = false;
    for (int p = 2; p * p <= N; p++) {
        if (is_prime[p]) {
            for (int i = p * p; i <= N; i += p)
                is_prime[i] = false;
        }
    }

    // Initial Tour: Bitonic Tour based on X-coordinates (input is sorted by X)
    path.reserve(N + 1);
    path.push_back(0);
    // Add even indices increasing
    for (int i = 2; i < N; i += 2) path.push_back(i);
    // Add odd indices decreasing
    for (int i = (N % 2 == 0 ? N - 1 : N - 2); i >= 1; i -= 2) path.push_back(i);
    path.push_back(0);

    auto start_time = chrono::steady_clock::now();
    
    // Optimization Parameters
    // We alternate between local 2-opt (windowed) and prime-fixing swaps
    int window_size = 25; 
    int prime_search_rad = 40;
    bool improved = true;
    
    // Main optimization loop
    while (true) {
        // Time check: stop if close to 2s limit (leave 150ms buffer)
        if (chrono::duration_cast<chrono::milliseconds>(chrono::steady_clock::now() - start_time).count() > 1850) break;
        
        improved = false;
        
        // 1. Windowed 2-opt
        for (int i = 1; i < N - 1; ++i) {
            // Periodic time check
            if ((i & 4095) == 0) {
                if (chrono::duration_cast<chrono::milliseconds>(chrono::steady_clock::now() - start_time).count() > 1850) goto end_loop;
            }

            int limit = min(N - 1, i + window_size);
            for (int j = i + 1; j <= limit; ++j) {
                // We consider reversing segment path[i...j]
                // This affects edges (path[i-1], path[i]) and (path[j], path[j+1])
                // And any penalties for steps k in [i, j+1]
                
                double cost_old = 0;
                double cost_new = 0;
                
                // Calculate costs for all steps k in [i, j+1]
                // For a step k, the edge connects node at k-1 to node at k
                
                for (int k = i; k <= j + 1; ++k) {
                    // Old configuration cost
                    cost_old += get_dist(path[k-1], path[k]) * get_multiplier(k, path[k-1]);
                    
                    // New configuration: determine nodes at k-1 and k
                    // Logic:
                    // If idx < i: path[idx] (unchanged)
                    // If idx > j: path[idx] (unchanged)
                    // If i <= idx <= j: path[i + j - idx] (reversed)
                    
                    int u_idx = k - 1;
                    int v_idx = k;
                    
                    int u = (u_idx < i) ? path[u_idx] : (u_idx > j ? path[u_idx] : path[i + j - u_idx]);
                    int v = (v_idx < i) ? path[v_idx] : (v_idx > j ? path[v_idx] : path[i + j - v_idx]);
                    
                    double m_new = 1.0;
                    if (k % 10 == 0 && !is_prime[u]) m_new = 1.1;
                    cost_new += get_dist(u, v) * m_new;
                }
                
                if (cost_new < cost_old - 1e-9) {
                    reverse(path.begin() + i, path.begin() + j + 1);
                    improved = true;
                }
            }
        }
        
        // 2. Prime fix pass: target steps that incur penalty
        for (int t = 10; t <= N; t += 10) {
            if ((t & 511) == 0) {
                 if (chrono::duration_cast<chrono::milliseconds>(chrono::steady_clock::now() - start_time).count() > 1850) goto end_loop;
            }

            // If this step has a penalty (source is not prime), try to fix it
            if (is_prime[path[t-1]]) continue;
            
            // Search for a prime city nearby in the tour to swap with
            int min_k = max(1, t - 1 - prime_search_rad);
            int max_k = min(N - 1, t - 1 + prime_search_rad);
            
            int idx1 = t - 1; // Index of non-prime city causing penalty
            
            for (int k = min_k; k <= max_k; ++k) {
                if (k == idx1) continue;
                if (!is_prime[path[k]]) continue; // Only swap with a prime
                
                int idx2 = k;
                int p1 = idx1;
                int p2 = idx2;
                if (p1 > p2) swap(p1, p2);
                
                // Identify steps affected by swapping path[p1] and path[p2]
                // Steps: p1, p1+1, p2, p2+1 (indices in path vector, corresponding to steps ending at p1, p1+1 etc?)
                // Actually steps are edges.
                // Step s connects path[s-1] -> path[s].
                // Affected steps are those where path[s-1] or path[s] changes.
                // Change at index p means:
                //   Step p: path[p-1] -> path[p] (dest changes)
                //   Step p+1: path[p] -> path[p+1] (source changes)
                vector<int> steps;
                steps.push_back(p1);
                steps.push_back(p1+1);
                if (p2 != p1 + 1) steps.push_back(p2); // Avoid duplicate if adjacent
                steps.push_back(p2+1);
                
                double d_old = 0;
                double d_new = 0;
                
                // Calculate old local cost
                for (int s : steps) {
                    if (s > N) continue; // Boundary check
                    d_old += get_dist(path[s-1], path[s]) * get_multiplier(s, path[s-1]);
                }
                
                // Perform swap
                swap(path[p1], path[p2]);
                
                // Calculate new local cost
                for (int s : steps) {
                    if (s > N) continue;
                    d_new += get_dist(path[s-1], path[s]) * get_multiplier(s, path[s-1]);
                }
                
                if (d_new < d_old - 1e-9) {
                    improved = true;
                    // Keep the swap and break from inner search (Greedy)
                    break;
                } else {
                    // Revert swap
                    swap(path[p1], path[p2]);
                }
            }
        }

        if (!improved) break; // Local optimum reached
    }

    end_loop:;

    cout << path.size() << "\n";
    for (int i = 0; i < path.size(); ++i) {
        cout << path[i] << "\n";
    }

    return 0;
}