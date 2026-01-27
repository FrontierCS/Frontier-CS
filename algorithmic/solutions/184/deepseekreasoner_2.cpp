#include <iostream>
#include <vector>
#include <algorithm>
#include <random>
#include <chrono>

using namespace std;

const double TIME_LIMIT = 1.95; 
int N, M;
vector<vector<int>> adj;

// Global RNG
mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());

// Greedy Construction Algorithm
// Builds a maximal independent set using randomized min-degree heuristic
vector<int> construct_greedy() {
    vector<int> solution(N, 0);
    vector<bool> active(N, true);
    vector<int> degree(N);
    
    for(int i = 0; i < N; ++i) {
        degree[i] = adj[i].size();
    }
    
    int active_count = N;
    
    while(active_count > 0) {
        int min_deg = 1000000000;
        vector<int> candidates;
        
        // Find vertices with minimum degree in the current subgraph
        for(int i = 0; i < N; ++i) {
            if(active[i]) {
                if(degree[i] < min_deg) {
                    min_deg = degree[i];
                    candidates.clear();
                    candidates.push_back(i);
                } else if(degree[i] == min_deg) {
                    candidates.push_back(i);
                }
            }
        }
        
        if (candidates.empty()) break;
        
        // Randomly select one candidate to break ties
        int selected = candidates[0];
        if(candidates.size() > 1) {
            uniform_int_distribution<int> dist(0, (int)candidates.size() - 1);
            selected = candidates[dist(rng)];
        }
        
        // Add to independent set
        solution[selected] = 1;
        active[selected] = false;
        active_count--;
        
        // Identify neighbors to remove (must be excluded)
        vector<int> to_remove;
        for(int neighbor : adj[selected]) {
            if(active[neighbor]) {
                active[neighbor] = false;
                active_count--;
                to_remove.push_back(neighbor);
            }
        }
        
        // Update degrees of remaining active nodes
        // Only valid active neighbors of the removed vertices need updates
        for(int r : to_remove) {
            for(int w : adj[r]) {
                if(active[w]) {
                    degree[w]--;
                }
            }
        }
    }
    return solution;
}

// Local Search Optimization
// Attempts to improve the solution via 1-opt (fill) and (1,1)-swaps
int optimize(vector<int>& sol, chrono::steady_clock::time_point start_time) {
    int k = 0;
    for(int x : sol) k += x;
    
    // Conflict count: number of neighbors in IS for each vertex
    vector<int> conflicts(N, 0);
    for(int i = 0; i < N; ++i) {
        if(sol[i]) {
            for(int neighbor : adj[i]) {
                conflicts[neighbor]++;
            }
        }
    }
    
    long long iter = 0;
    // Limit continuous swaps without improvement to avoid cycles/wasting time
    int no_improve_iters = 0;
    const int MAX_NO_IMPROVE = 8 * N; 

    while(no_improve_iters < MAX_NO_IMPROVE) {
        iter++;
        if((iter & 63) == 0) {
            chrono::duration<double> elapsed = chrono::steady_clock::now() - start_time;
            if(elapsed.count() > TIME_LIMIT) break;
        }
        
        bool improvement = false;
        
        // Step 1: Fill (1-opt) - Add any valid vertex
        vector<int> candidates;
        for(int i = 0; i < N; ++i) {
            if(!sol[i] && conflicts[i] == 0) {
                candidates.push_back(i);
            }
        }
        
        if(!candidates.empty()) {
            if (candidates.size() > 1) shuffle(candidates.begin(), candidates.end(), rng);
            for(int v : candidates) {
                if(conflicts[v] == 0) {
                    sol[v] = 1;
                    k++;
                    for(int u : adj[v]) conflicts[u]++;
                    improvement = true;
                }
            }
        }
        
        if(improvement) {
            no_improve_iters = 0;
            continue; 
        }
        
        // Step 2: Swap (1,1) - Swap a vertex in for a vertex out
        vector<int> swap_candidates;
        for(int i = 0; i < N; ++i) {
            if(!sol[i] && conflicts[i] == 1) {
                swap_candidates.push_back(i);
            }
        }
        
        if(swap_candidates.empty()) break; 
        
        uniform_int_distribution<int> dist(0, (int)swap_candidates.size() - 1);
        int v_in = swap_candidates[dist(rng)];
        
        int u_out = -1;
        for(int neighbor : adj[v_in]) {
            if(sol[neighbor]) {
                u_out = neighbor;
                break;
            }
        }
        
        if(u_out != -1) {
            sol[u_out] = 0;
            for(int w : adj[u_out]) conflicts[w]--;
            
            sol[v_in] = 1;
            for(int w : adj[v_in]) conflicts[w]++;
        }
        
        no_improve_iters++;
    }
    
    return k;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    auto start_time = chrono::steady_clock::now();
    
    if (!(cin >> N >> M)) return 0;
    
    adj.resize(N);
    for(int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }
    
    vector<int> best_sol(N, 0);
    int max_k = -1;
    
    // Repeatedly generate solutions and optimize them (GRASP metaheuristic)
    while(true) {
        chrono::duration<double> elapsed = chrono::steady_clock::now() - start_time;
        if(elapsed.count() > TIME_LIMIT) break;
        
        vector<int> sol = construct_greedy();
        int k = optimize(sol, start_time);
        
        if(k > max_k) {
            max_k = k;
            best_sol = sol;
        }
    }
    
    for(int i = 0; i < N; ++i) {
        cout << best_sol[i] << "\n";
    }
    
    return 0;
}