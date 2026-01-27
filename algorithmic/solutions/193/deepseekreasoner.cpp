#include <iostream>
#include <vector>
#include <algorithm>
#include <ctime>
#include <random>

using namespace std;

// Improves I/O performance
void fast_io() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
}

// Struct to hold clause information
struct Clause {
    int l1, l2; // Literals in raw format: 2*k for x_k, 2*k+1 for ¬x_k
    int v1, v2; // Variable indices (0 to n-1)
};

int n, m;
vector<Clause> clauses;
vector<vector<int>> adj; // Maps variable index to list of clause indices it appears in
vector<int> assignment; // Current boolean assignment 0 or 1
vector<int> sat_count;  // sat_count[i] = number of true literals in clause i
vector<int> score_diff; // score_diff[v] = change in total satisfied clauses if v is flipped
vector<int> best_assignment;
vector<int> unsat_list; // List of indices of currently unsatisfied clauses
vector<int> pos_in_unsat; // Map clause index -> position in unsat_list (-1 if satisfied)

int best_sat = -1;
int current_sat = 0;

// Returns the boolean value of a literal based on current assignment
inline int lit_val(int lit) {
    int var = lit >> 1;
    int val = assignment[var];
    return (lit & 1) ? !val : val;
}

// Calculates the gain in satisfied clauses if variable 'var' is flipped
// Does not modify state, purely hypothetical based on current state
inline int calc_gain(int c_idx, int var) {
    int s = sat_count[c_idx];
    int l1 = clauses[c_idx].l1;
    int l2 = clauses[c_idx].l2;
    int v1 = clauses[c_idx].v1;
    int v2 = clauses[c_idx].v2;
    
    int val1 = lit_val(l1);
    int val2 = lit_val(l2);
    
    // Values after flipping 'var'
    int n_val1 = (v1 == var) ? !val1 : val1;
    int n_val2 = (v2 == var) ? !val2 : val2;
    
    int new_s = n_val1 + n_val2;
    // value is 1 if clause becomes SAT from UNSAT, -1 if SAT to UNSAT, 0 otherwise
    return (new_s > 0) - (s > 0);
}

// Initialize data structures based on current assignment
void build() {
    current_sat = 0;
    fill(sat_count.begin(), sat_count.end(), 0);
    fill(score_diff.begin(), score_diff.end(), 0);
    unsat_list.clear();
    fill(pos_in_unsat.begin(), pos_in_unsat.end(), -1);
    
    for (int i = 0; i < m; ++i) {
        int v1 = lit_val(clauses[i].l1);
        int v2 = lit_val(clauses[i].l2);
        sat_count[i] = v1 + v2;
        if (sat_count[i] > 0) current_sat++;
        else {
            pos_in_unsat[i] = unsat_list.size();
            unsat_list.push_back(i);
        }
    }
    
    for (int v = 0; v < n; ++v) {
        int diff = 0;
        for (int c_idx : adj[v]) {
            diff += calc_gain(c_idx, v);
        }
        score_diff[v] = diff;
    }
}

// Execute a flip of variable v and update data structures incrementally
void flip(int v) {
    // 1. Remove old contributions of affected clauses to score_diff
    for (int c_idx : adj[v]) {
        int v1 = clauses[c_idx].v1;
        int v2 = clauses[c_idx].v2;
        score_diff[v1] -= calc_gain(c_idx, v1);
        if (v1 != v2) score_diff[v2] -= calc_gain(c_idx, v2);
    }
    
    // 2. Flip the variable
    assignment[v] = !assignment[v];
    
    // 3. Update clause states and unsat list
    for (int c_idx : adj[v]) {
        int was_sat = (sat_count[c_idx] > 0);
        int v1_val = lit_val(clauses[c_idx].l1);
        int v2_val = lit_val(clauses[c_idx].l2);
        sat_count[c_idx] = v1_val + v2_val;
        int is_sat = (sat_count[c_idx] > 0);
        
        if (was_sat != is_sat) {
            current_sat += (is_sat ? 1 : -1);
            if (is_sat) { // Unsat -> Sat: Remove from list
                int pos = pos_in_unsat[c_idx];
                int last = unsat_list.back();
                unsat_list[pos] = last;
                pos_in_unsat[last] = pos;
                unsat_list.pop_back();
                pos_in_unsat[c_idx] = -1;
            } else { // Sat -> Unsat: Add to list
                pos_in_unsat[c_idx] = unsat_list.size();
                unsat_list.push_back(c_idx);
            }
        }
    }
    
    // 4. Add new contributions of affected clauses to score_diff
    for (int c_idx : adj[v]) {
        int v1 = clauses[c_idx].v1;
        int v2 = clauses[c_idx].v2;
        score_diff[v1] += calc_gain(c_idx, v1);
        if (v1 != v2) score_diff[v2] += calc_gain(c_idx, v2);
    }
}

int main() {
    fast_io();
    if (!(cin >> n >> m)) return 0;
    
    assignment.resize(n);
    best_assignment.resize(n);
    adj.resize(n);
    sat_count.resize(m);
    score_diff.resize(n);
    pos_in_unsat.resize(m);
    
    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        // Transform 1-based signed input to 0-based literal encoding
        // x -> 2*(x-1), -x -> 2*(x-1)+1
        int l1 = (u > 0) ? 2 * (u - 1) : 2 * (-u - 1) + 1;
        int l2 = (v > 0) ? 2 * (v - 1) : 2 * (-v - 1) + 1;
        clauses.push_back({l1, l2, l1 >> 1, l2 >> 1});
        adj[l1 >> 1].push_back(i);
        if ((l1 >> 1) != (l2 >> 1)) adj[l2 >> 1].push_back(i);
    }
    
    mt19937 rng(1337); 
    
    // Initialize random assignment
    for (int i = 0; i < n; ++i) assignment[i] = rng() % 2;
    build();
    best_sat = current_sat;
    best_assignment = assignment;
    
    double start_time = (double)clock() / CLOCKS_PER_SEC;
    long long iter = 0;
    vector<int> candidates;
    candidates.reserve(n);
    
    // Main Local Search Loop
    while (true) {
        // Time check
        if ((iter & 511) == 0) { 
            double curr_time = (double)clock() / CLOCKS_PER_SEC;
            if (curr_time - start_time > 0.95) break; // Use ~95% of 1s limit
        }
        iter++;
        
        // Strategy: 
        // 1. Identify best possible moves (Greedy)
        // 2. If valid greedy move exists (improves score), take it.
        // 3. Otherwise (Local Optima), perform WalkSAT step (pick unsat clause and flip a var).
        
        int best_d = -1e9;
        candidates.clear();
        
        // Find variable with maximum score improvement
        for (int i = 0; i < n; ++i) {
            if (score_diff[i] > best_d) {
                best_d = score_diff[i];
                candidates.clear();
                candidates.push_back(i);
            } else if (score_diff[i] == best_d) {
                candidates.push_back(i);
            }
        }
        
        bool greedy = false;
        if (best_d > 0) {
            greedy = true;
            flip(candidates[rng() % candidates.size()]);
        } else {
            // Greedy failed to improve, try to fix an unsatisfied clause
            if (unsat_list.empty()) break; // All satisfied
            
            int c_idx = unsat_list[rng() % unsat_list.size()];
            int v1 = clauses[c_idx].v1;
            int v2 = clauses[c_idx].v2;
            
            // Heuristic: flip the variable with better score_diff (less damage)
            if (v1 == v2) flip(v1);
            else {
                if (score_diff[v1] > score_diff[v2]) flip(v1);
                else if (score_diff[v2] > score_diff[v1]) flip(v2);
                else flip((rng() % 2) ? v1 : v2);
            }
        }
        
        // Update best solution found so far
        if (current_sat > best_sat) {
            best_sat = current_sat;
            best_assignment = assignment;
            if (best_sat == m) break; // Perfect
        }
        
        // Periodic perturbation if stuck for too long (Restart-like behavior)
        if (iter % (2000) == 0) { 
            // Random walk steps to escape basin of attraction
            int steps = n / 20; 
            if (steps < 1) steps = 1;
            while(steps--) flip(rng() % n);
        }
    }
    
    // Output
    for (int i = 0; i < n; ++i) {
        cout << best_assignment[i] << (i == n - 1 ? "" : " ");
    }
    cout << "\n";
    
    return 0;
}