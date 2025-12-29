#include <iostream>
#include <vector>
#include <numeric>
#include <cmath>
#include <algorithm>
#include <random>
#include <chrono>

using namespace std;

// Problem Constants
const int N = 100;

// Struct to represent an item to be assigned to a bucket
// Each employee i produces two items: one for the 'odd' transition (a_i) and one for 'even' (b_i)
struct Item {
    int id;
    int source;
    int weight;
    int slot; // 0 corresponds to a_i, 1 corresponds to b_i
};

int T[N];
int adj[N][2]; // adj[i][0] -> a_i, adj[i][1] -> b_i
int assignment[2 * N]; // Tracks which node (bucket) each item is assigned to
long long F[N]; // Current accumulated weight in each bucket (approximate inflow)
long long C[N]; // Target capacity for each node
Item items[2 * N];

// Random number generator
mt19937 rng(12345);

// BFS structures for reachability check
bool reachable[N];
int q[N + 5];

// Calculate penalty for nodes that are unreachable from node 0
// We penalize based on the target T values of unreachable nodes
long long calculate_unreachable_penalty() {
    for (int i = 0; i < N; ++i) reachable[i] = false;
    int head = 0, tail = 0;
    
    // Start from node 0
    reachable[0] = true;
    q[tail++] = 0;
    
    while(head < tail) {
        int u = q[head++];
        // Check both outgoing edges
        int v1 = adj[u][0];
        if (!reachable[v1]) {
            reachable[v1] = true;
            q[tail++] = v1;
        }
        int v2 = adj[u][1];
        if (!reachable[v2]) {
            reachable[v2] = true;
            q[tail++] = v2;
        }
    }
    
    long long penalty = 0;
    for (int i = 0; i < N; ++i) {
        if (!reachable[i]) {
            penalty += T[i];
        }
    }
    return penalty;
}

int main() {
    // Fast I/O
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    int n_in, l_in;
    if (!(cin >> n_in >> l_in)) return 0;
    
    for (int i = 0; i < N; ++i) {
        cin >> T[i];
    }
    
    // Setup items and capacities
    for (int i = 0; i < N; ++i) {
        // Target capacity is T[i], minus 1 for node 0 because it starts with the token
        C[i] = T[i];
        if (i == 0) C[i]--; 
        
        // Item for a_i (slot 0): used on odd visits (1st, 3rd, ...)
        // It receives ceil(T_i / 2) flow
        items[2*i].id = 2*i;
        items[2*i].source = i;
        items[2*i].weight = (T[i] + 1) / 2;
        items[2*i].slot = 0;
        
        // Item for b_i (slot 1): used on even visits (2nd, 4th, ...)
        // It receives floor(T_i / 2) flow
        items[2*i+1].id = 2*i+1;
        items[2*i+1].source = i;
        items[2*i+1].weight = T[i] / 2;
        items[2*i+1].slot = 1;
    }
    
    // Initial solution using Greedy Best-Fit strategy
    // Sort items descending by weight to place largest items first
    vector<int> p(2 * N);
    iota(p.begin(), p.end(), 0);
    sort(p.begin(), p.end(), [&](int a, int b){
        return items[a].weight > items[b].weight;
    });
    
    fill(F, F + N, 0);
    
    for (int idx : p) {
        int best_j = 0;
        long long max_deficit = -1e18;
        
        // Find bucket with largest remaining capacity (Target - Current)
        for (int j = 0; j < N; ++j) {
            long long deficit = C[j] - F[j];
            if (deficit > max_deficit) {
                max_deficit = deficit;
                best_j = j;
            }
        }
        
        // Assign
        assignment[idx] = best_j;
        F[best_j] += items[idx].weight;
        adj[items[idx].source][items[idx].slot] = best_j;
    }
    
    // Calculate initial score terms
    long long current_diff = 0;
    for (int i = 0; i < N; ++i) current_diff += abs(F[i] - C[i]);
    
    long long current_penalty = calculate_unreachable_penalty();
    
    // Total score combines flow error and connectivity penalty
    // Penalty is weighted heavily to ensure connectivity is prioritized
    double current_score = current_diff + current_penalty * 2.0;
    
    // Simulated Annealing
    auto start_time = chrono::steady_clock::now();
    double time_limit = 1.8; // seconds
    double start_temp = 500.0;
    double current_temp = start_temp;
    
    const int BATCH_SIZE = 512;
    
    while (true) {
        // Run a batch of iterations
        for (int k = 0; k < BATCH_SIZE; ++k) {
            // Propose a move: pick a random item and move it to a random node
            int item_idx = uniform_int_distribution<int>(0, 2 * N - 1)(rng);
            int old_dest = assignment[item_idx];
            int new_dest = uniform_int_distribution<int>(0, N - 1)(rng);
            
            if (old_dest == new_dest) continue;
            
            int w = items[item_idx].weight;
            
            // Calculate change in flow difference (Diff)
            long long old_diff_term_old = abs(F[old_dest] - C[old_dest]);
            long long old_diff_term_new = abs(F[new_dest] - C[new_dest]);
            
            long long new_F_old = F[old_dest] - w;
            long long new_F_new = F[new_dest] + w;
            
            long long new_diff_term_old = abs(new_F_old - C[old_dest]);
            long long new_diff_term_new = abs(new_F_new - C[new_dest]);
            
            long long delta_diff = (new_diff_term_old + new_diff_term_new) - (old_diff_term_old + old_diff_term_new);
            
            // Apply tentative change to graph to check connectivity
            int src = items[item_idx].source;
            int slot = items[item_idx].slot;
            adj[src][slot] = new_dest; 
            
            // Calculate change in penalty
            long long new_penalty = calculate_unreachable_penalty();
            double delta_penalty = (new_penalty - current_penalty) * 2.0;
            
            double delta_score = delta_diff + delta_penalty;
            
            // Metropolis acceptance criterion
            if (delta_score <= 0 || bernoulli_distribution(exp(-delta_score / (current_temp + 1e-9)))(rng)) {
                // Accept move
                current_diff += delta_diff;
                current_penalty = new_penalty;
                current_score += delta_score;
                
                F[old_dest] = new_F_old;
                F[new_dest] = new_F_new;
                assignment[item_idx] = new_dest;
            } else {
                // Reject move (revert graph)
                adj[src][slot] = old_dest;
            }
        }
        
        // Time check and temperature update
        auto now = chrono::steady_clock::now();
        double elapsed = chrono::duration<double>(now - start_time).count();
        if (elapsed > time_limit) break;
        
        current_temp = start_temp * (1.0 - elapsed / time_limit);
        if (current_temp < 0) current_temp = 0;
    }
    
    // Output the resulting plan
    for (int i = 0; i < N; ++i) {
        cout << adj[i][0] << " " << adj[i][1] << "\n";
    }
    
    return 0;
}