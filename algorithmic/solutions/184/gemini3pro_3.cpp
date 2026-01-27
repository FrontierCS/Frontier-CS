#include <iostream>
#include <vector>
#include <bitset>
#include <algorithm>
#include <random>
#include <chrono>
#include <numeric>

using namespace std;

// ----------------------
// Constants & Globals
// ----------------------
const int MAXN = 1005;
const double TIME_LIMIT = 1.95; // seconds

int N, M;
bitset<MAXN> adj[MAXN];          // Adjacency matrix (bitset for speed)
vector<int> adj_list[MAXN];      // Adjacency list (stores neighbors for iteration)
bool in_set[MAXN];               // Current solution status (true if vertex is in S)
int tightness[MAXN];             // tightness[v] = |N(v) \cap S| (number of neighbors in S)
int best_solution[MAXN];         // Best solution found so far
int max_k = 0;                   // Size of best solution

// Random Number Generator
mt19937 rng(1337);

// Time Management
auto start_time = chrono::high_resolution_clock::now();

double get_elapsed() {
    auto now = chrono::high_resolution_clock::now();
    chrono::duration<double> diff = now - start_time;
    return diff.count();
}

// ----------------------
// Core Functions
// ----------------------

// Add vertex u to S, update neighbors' tightness
void add_vertex(int u) {
    if (in_set[u]) return;
    in_set[u] = true;
    for (int v : adj_list[u]) {
        tightness[v]++;
    }
}

// Remove vertex u from S, update neighbors' tightness
void remove_vertex(int u) {
    if (!in_set[u]) return;
    in_set[u] = false;
    for (int v : adj_list[u]) {
        tightness[v]--;
    }
}

// Update the global best solution if current is better
void update_best() {
    int current_k = 0;
    for (int i = 1; i <= N; ++i) {
        if (in_set[i]) current_k++;
    }
    
    if (current_k > max_k) {
        max_k = current_k;
        for (int i = 1; i <= N; ++i) {
            best_solution[i] = in_set[i] ? 1 : 0;
        }
    }
}

// Helper: Find the unique neighbor in S for a vertex v with tightness 1
// Returns -1 if no neighbor in S (should not happen if tightness==1)
int get_single_neighbor(int v) {
    for (int u : adj_list[v]) {
        if (in_set[u]) return u;
    }
    return -1;
}

// Generate an initial solution using Randomized Greedy
void initial_greedy() {
    // Clear state
    for (int i = 1; i <= N; ++i) {
        in_set[i] = false;
        tightness[i] = 0;
    }
    
    // Order vertices randomly
    vector<int> p(N);
    iota(p.begin(), p.end(), 1);
    shuffle(p.begin(), p.end(), rng);
    
    // Greedy construction: pick valid vertices
    for (int u : p) {
        if (tightness[u] == 0) {
            add_vertex(u);
        }
    }
    update_best();
}

// ----------------------
// Main Solver (Iterated Local Search)
// ----------------------
void solve() {
    initial_greedy();
    
    // Tabu search state: tabu[u] stores the iteration number until which vertex u is locked
    vector<int> tabu(N + 1, 0);
    int iter = 0;
    int no_improve_iters = 0;
    
    // Parameters for search control
    const int TABU_TENURE_BASE = 7;
    const int MAX_NO_IMPROVE = 2500; // Threshold to trigger perturbation
    
    // Buffer for (1, 2)-swap candidates
    // candidates_for[u] stores vertices v such that v is not in S, tightness[v]=1, and neighbor of v is u
    vector<vector<int>> candidates_for(N + 1);

    while (true) {
        // Time Check
        if ((iter & 127) == 0) { // Check periodically
            if (get_elapsed() > TIME_LIMIT) break;
        }
        iter++;
        
        bool changed = false;
        
        // ------------------------------------------
        // Phase 1: Immediate Additions (Tightness 0)
        // ------------------------------------------
        // If any vertex has 0 neighbors in S, add it immediately.
        vector<int> zero_tight;
        for (int i = 1; i <= N; ++i) {
            if (!in_set[i] && tightness[i] == 0) {
                zero_tight.push_back(i);
            }
        }
        
        if (!zero_tight.empty()) {
            for (int u : zero_tight) add_vertex(u);
            update_best();
            no_improve_iters = 0;
            // If we added vertices, constraints changed, so restart loop to check new opportunities
            continue; 
        }
        
        // ------------------------------------------
        // Phase 2: (1, 2)-Swaps
        // ------------------------------------------
        // Try to replace 1 vertex u in S with 2 vertices v1, v2 not in S.
        // Requires: tightness[v1]=1, tightness[v2]=1, N(v1)nS = {u}, N(v2)nS = {u}, and v1 not adjacent to v2.
        
        vector<int> one_tight;
        for (int i = 1; i <= N; ++i) {
            if (!in_set[i] && tightness[i] == 1) {
                one_tight.push_back(i);
            }
        }
        
        // Group candidates by their single neighbor in S
        vector<int> relevant_s;
        for (int v : one_tight) {
            int u = get_single_neighbor(v);
            if (u != -1) {
                if (candidates_for[u].empty()) relevant_s.push_back(u);
                candidates_for[u].push_back(v);
            }
        }
        
        bool swap_found = false;
        for (int u : relevant_s) {
            if (candidates_for[u].size() >= 2) {
                vector<int>& cands = candidates_for[u];
                // Check all pairs in cands for independence
                for (size_t i = 0; i < cands.size(); ++i) {
                    for (size_t j = i + 1; j < cands.size(); ++j) {
                        int v1 = cands[i];
                        int v2 = cands[j];
                        // If v1 and v2 are not connected
                        if (!adj[v1][v2]) {
                            // Perform (1, 2)-swap
                            remove_vertex(u);
                            add_vertex(v1);
                            add_vertex(v2);
                            
                            // Set tabu to avoid immediate reversal
                            tabu[u] = iter + TABU_TENURE_BASE + (rng() % 5);
                            
                            swap_found = true;
                            goto end_swap_search;
                        }
                    }
                }
            }
        }
        
        end_swap_search:
        // Cleanup used vectors
        for (int u : relevant_s) candidates_for[u].clear();
        
        if (swap_found) {
            update_best();
            no_improve_iters = 0;
            continue;
        }
        
        // ------------------------------------------
        // Phase 3: (1, 1)-Swaps (Tabu Search)
        // ------------------------------------------
        // Swap u in S with v not in S (tightness[v]=1, neighbor=u) to escape local optima.
        // Size remains constant, but configuration changes.
        
        vector<int> valid_moves;
        for (int v : one_tight) {
            int u = get_single_neighbor(v);
            // Tabu check: allow move only if vertices are not tabu
            if (tabu[v] <= iter && tabu[u] <= iter) {
                valid_moves.push_back(v);
            }
        }
        
        if (!valid_moves.empty()) {
            // Pick a random valid (1,1) move
            int v = valid_moves[rng() % valid_moves.size()];
            int u = get_single_neighbor(v);
            
            remove_vertex(u);
            add_vertex(v);
            
            int tenure = TABU_TENURE_BASE + (rng() % 5);
            tabu[u] = iter + tenure;
            tabu[v] = iter + tenure;
            
            no_improve_iters++;
        } else {
            // No moves available (highly constrained state)
            no_improve_iters += 50; 
        }
        
        // ------------------------------------------
        // Phase 4: Perturbation (Kick / Soft Restart)
        // ------------------------------------------
        if (no_improve_iters > MAX_NO_IMPROVE) {
            // Stop if too close to time limit
            if (get_elapsed() > TIME_LIMIT - 0.05) break;

            // Restore best solution found so far
            for (int i = 1; i <= N; ++i) in_set[i] = false;
            for (int i = 1; i <= N; ++i) if (best_solution[i]) in_set[i] = true;
            
            // Recompute tightness for best solution state
            fill(tightness, tightness + N + 1, 0);
            for (int i = 1; i <= N; ++i) {
                if (in_set[i]) {
                    for (int nbr : adj_list[i]) tightness[nbr]++;
                }
            }
            
            // Perform Kick: Remove random K vertices from the best solution
            vector<int> s_nodes;
            for (int i = 1; i <= N; ++i) if (in_set[i]) s_nodes.push_back(i);
            
            if (!s_nodes.empty()) {
                shuffle(s_nodes.begin(), s_nodes.end(), rng);
                int remove_cnt = max(3, (int)s_nodes.size() / 15); // Remove ~6-7%
                for (int k = 0; k < remove_cnt && k < (int)s_nodes.size(); ++k) {
                    remove_vertex(s_nodes[k]);
                }
            }
            
            // Reset tabu memory and counters
            fill(tabu.begin(), tabu.end(), 0);
            no_improve_iters = 0;
            // The next loop iteration will fill holes using Phase 1 (Greedy)
        }
    }
}

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    if (!(cin >> N >> M)) return 0;
    
    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        if (u == v) continue;
        // Use bitset to handle duplicate edges efficiently
        if (!adj[u][v]) {
            adj[u][v] = 1;
            adj[v][u] = 1;
            adj_list[u].push_back(v);
            adj_list[v].push_back(u);
        }
    }
    
    solve();
    
    // Output result
    for (int i = 1; i <= N; ++i) {
        cout << best_solution[i] << "\n";
    }
    
    return 0;
}