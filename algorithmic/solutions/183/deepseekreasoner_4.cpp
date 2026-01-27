#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <random>
#include <chrono>

using namespace std;

// Problem constants
int N, M;
vector<vector<int>> adj;
vector<int> degree;

// Time management
auto start_time = chrono::high_resolution_clock::now();
const double TIME_LIMIT = 1.95; 

double get_time() {
    auto now = chrono::high_resolution_clock::now();
    chrono::duration<double> diff = now - start_time;
    return diff.count();
}

// Random Number Generator
mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());

// Solution Structure
struct Solution {
    vector<bool> in_set;     // Is vertex i in Independent Set?
    vector<int> conflicts;   // How many neighbors of i are in Independent Set?
    int size;

    Solution(int n) : in_set(n + 1, false), conflicts(n + 1, 0), size(0) {}

    // Add vertex v to IS (Assuming safe to do so)
    void add(int v) {
        if (in_set[v]) return;
        in_set[v] = true;
        size++;
        for (int u : adj[v]) {
            conflicts[u]++;
        }
    }

    // Remove vertex v from IS
    void remove(int v) {
        if (!in_set[v]) return;
        in_set[v] = false;
        size--;
        for (int u : adj[v]) {
            conflicts[u]--;
        }
    }
};

// Construct initial solution using Randomized Min-Degree Greedy
Solution construct_greedy() {
    Solution sol(N);
    vector<int> p(N);
    iota(p.begin(), p.end(), 1);
    
    // Assign weights: lower degree -> processed earlier -> more likely to be picked
    // Add noise to randomize
    vector<float> weight(N + 1);
    uniform_real_distribution<float> dist(0.0, 1.0);
    for (int i = 1; i <= N; ++i) {
        weight[i] = (float)degree[i] + dist(rng) * 5.0f;
    }
    
    sort(p.begin(), p.end(), [&](int a, int b) {
        return weight[a] < weight[b];
    });

    for (int v : p) {
        if (sol.conflicts[v] == 0) {
            sol.add(v);
        }
    }
    return sol;
}

// Local Search / Simulated Annealing
void optimize(Solution& sol) {
    long long iter = 0;
    
    // Tabu list to prevent immediate cycling
    vector<int> tabu(N + 1, 0);
    
    // Parameters
    double temp = 1.0;
    double cooling = 0.999995;
    
    int best_size = sol.size;
    vector<bool> best_in_set = sol.in_set;
    
    uniform_int_distribution<int> rand_v(1, N);
    uniform_real_distribution<double> rand_prob(0.0, 1.0);
    uniform_int_distribution<int> rand_tabu(10, 50);

    while (true) {
        iter++;
        
        // Time check and Cooling roughly every 1024 iterations
        if ((iter & 1023) == 0) {
            if (get_time() > TIME_LIMIT) break;
            temp *= cooling;
            if (temp < 0.1) temp = 0.1;
        }

        // Periodically greedily add all free vertices
        // This ensures maximal independent set property and quick wins
        if (iter % 5000 == 0) {
            bool improved = true;
            while(improved) {
                improved = false;
                for(int i=1; i<=N; ++i) {
                    if(!sol.in_set[i] && sol.conflicts[i] == 0) {
                        sol.add(i);
                        improved = true;
                    }
                }
            }
            if (sol.size > best_size) {
                best_size = sol.size;
                best_in_set = sol.in_set;
            }
        }
        
        int v = rand_v(rng);
        
        if (sol.in_set[v]) {
            // Vertex v is IN the set.
            // Occasional force remove to escape local optima?
            // Handled implicitly by swaps mostly.
        } else {
            // Vertex v is NOT in the set.
            int c = sol.conflicts[v];
            
            if (c == 0) {
                // Free addition
                sol.add(v);
            } 
            else if (c == 1) {
                // 1-1 Swap (Plateau move)
                // Find the single neighbor u in S
                int u = -1;
                for (int neighbor : adj[v]) {
                    if (sol.in_set[neighbor]) {
                        u = neighbor;
                        break;
                    }
                }
                
                // If u is tabu, skip unless random desire?
                if (u != -1 && tabu[u] <= iter) {
                    // Try swap: Add v, Remove u
                    sol.remove(u);
                    sol.add(v);
                    
                    // Mark u as tabu
                    tabu[u] = iter + rand_tabu(rng);
                }
            } 
            else if (c == 2) {
                // 1-2 Swap (Remove 2, Add 1) => Size -1
                // Taking a step back to potentially jump forward later
                // Accept with probability based on temperature
                if (rand_prob(rng) < temp * 0.02) {
                    int u1 = -1, u2 = -1;
                    for (int neighbor : adj[v]) {
                        if (sol.in_set[neighbor]) {
                            if (u1 == -1) u1 = neighbor;
                            else { u2 = neighbor; break; }
                        }
                    }
                    if (u1 != -1 && u2 != -1 && tabu[u1] <= iter && tabu[u2] <= iter) {
                        sol.remove(u1);
                        sol.remove(u2);
                        sol.add(v);
                        int t = rand_tabu(rng);
                        tabu[u1] = iter + t;
                        tabu[u2] = iter + t;
                    }
                }
            }
        }
    }
    
    // Final check for freebies on the best solution
    sol.in_set = best_in_set;
    sol.size = best_size;
    bool improved = true;
    while(improved) {
        improved = false;
        // Recompute conflicts for the restored best_in_set
        fill(sol.conflicts.begin(), sol.conflicts.end(), 0);
        for(int i=1; i<=N; ++i) {
            if(sol.in_set[i]) {
                for(int u : adj[i]) sol.conflicts[u]++;
            }
        }
        
        for(int i=1; i<=N; ++i) {
            if(!sol.in_set[i] && sol.conflicts[i] == 0) {
                sol.add(i); // This updates conflicts incrementally
                improved = true;
            }
        }
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    if (!(cin >> N >> M)) return 0;
    
    adj.resize(N + 1);
    degree.resize(N + 1, 0);
    
    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
        degree[u]++;
        degree[v]++;
    }
    
    Solution best_sol(N);
    int best_k = -1;
    
    // Multiple Greedy Restarts (Limit to 0.4 seconds)
    while (get_time() < 0.4) {
        Solution s = construct_greedy();
        if (s.size > best_k) {
            best_k = s.size;
            best_sol = s;
        }
        // Safety break for very small instances to avoid infinite loop effectively taking all time
        // Though logical condition handles it; just ensures we enter optimize phase.
        if (M == 0) break; // Independent set is all vertices
    }
    
    // Run Optimization on the best starting point
    optimize(best_sol);
    
    // Output
    for (int i = 1; i <= N; ++i) {
        cout << (best_sol.in_set[i] ? 1 : 0) << "\n";
    }
    
    return 0;
}