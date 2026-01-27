#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <ctime>
#include <random>

using namespace std;

// Structure to store clause literals
struct Clause {
    int l1, l2;
};

int n, m;
vector<Clause> clauses;
vector<vector<int>> lit_in_clauses; // Mapping from literal to list of clause indices
vector<int> assignment; // Current assignment (0 or 1)
vector<int> clause_sat_count; // Number of satisfied literals in each clause
int current_sat; // Current number of satisfied clauses

vector<int> best_assignment;
int best_sat = -1;

// Rebuilds the satisfaction counts based on current 'assignment'
void build_state() {
    current_sat = 0;
    fill(clause_sat_count.begin(), clause_sat_count.end(), 0);
    for (int i = 0; i < m; ++i) {
        // Evaluate literal 1
        // Literal l is true if (assignment[var] != type)
        // l1%2 == 0 means positive (needs 1), l1%2 == 1 means negative (needs 0)
        int val1 = (assignment[clauses[i].l1 / 2] != (clauses[i].l1 % 2));
        int val2 = (assignment[clauses[i].l2 / 2] != (clauses[i].l2 % 2));
        clause_sat_count[i] = val1 + val2;
        if (clause_sat_count[i] > 0) current_sat++;
    }
}

// Attempts to flip the variable 'var'. 
// Returns true if the flip improves the score and is kept.
// Returns false if the flip does not improve the score and is reverted.
bool try_flip(int var) {
    int old_val = assignment[var];
    // Determine which literals change state
    // If old_val = 0 (var is false):
    //   Flip makes var true.
    //   Pos literal (2*var) becomes true.
    //   Neg literal (2*var+1) becomes false.
    // If old_val = 1 (var is true):
    //   Flip makes var false.
    //   Pos literal (2*var) becomes false.
    //   Neg literal (2*var+1) becomes true.
    
    // Literal becoming true corresponds to the NEW value.
    // if new value is 1, pos lit is true. if new value is 0, neg lit is true.
    // Formula: 2*var + old_val
    // (If old=0, new=1 -> 2*var. If old=1, new=0 -> 2*var+1)
    int lit_becoming_true = 2 * var + old_val;
    int lit_becoming_false = 2 * var + (1 - old_val);
    
    int score_diff = 0;
    
    // Process clauses where a literal becomes true (gain potential)
    // We increment sat_count. If count goes 0 -> 1, score increases.
    for (int c : lit_in_clauses[lit_becoming_true]) {
        if (clause_sat_count[c] == 0) score_diff++;
        clause_sat_count[c]++;
    }
    
    // Process clauses where a literal becomes false (loss potential)
    // We decrement sat_count. If count goes 1 -> 0, score decreases.
    for (int c : lit_in_clauses[lit_becoming_false]) {
        clause_sat_count[c]--;
        if (clause_sat_count[c] == 0) score_diff--;
    }
    
    // Greedy decision: if strictly improving, keep it.
    if (score_diff > 0) {
        assignment[var] = 1 - old_val;
        current_sat += score_diff;
        return true;
    } else {
        // Revert changes to counts
        for (int c : lit_in_clauses[lit_becoming_false]) {
            clause_sat_count[c]++;
        }
        for (int c : lit_in_clauses[lit_becoming_true]) {
            clause_sat_count[c]--;
        }
        return false;
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> n >> m)) return 0;

    clauses.resize(m);
    lit_in_clauses.resize(2 * n);

    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        // Map input to internal literal representation
        // Variable k (1-based) -> k-1 (0-based)
        // +k -> 2*(k-1)
        // -k -> 2*(k-1) + 1
        int l1 = (u > 0) ? 2 * (u - 1) : 2 * (-u - 1) + 1;
        int l2 = (v > 0) ? 2 * (v - 1) : 2 * (-v - 1) + 1;
        clauses[i] = {l1, l2};
        lit_in_clauses[l1].push_back(i);
        lit_in_clauses[l2].push_back(i);
    }
    
    clause_sat_count.resize(m);
    assignment.resize(n);
    vector<int> vars(n);
    iota(vars.begin(), vars.end(), 0);
    
    // Random number generator
    mt19937 rng(static_cast<unsigned>(time(NULL)));
    
    clock_t start = clock();
    double time_limit = 0.95 * CLOCKS_PER_SEC; // Limit execution time (adjust if needed)
    
    best_sat = -1;
    
    // Random Restart Hill Climbing
    while (double(clock() - start) < time_limit) {
        // Generate random assignment
        for (int i = 0; i < n; ++i) assignment[i] = rng() % 2;
        build_state();
        
        // Update best
        if (current_sat > best_sat) {
            best_sat = current_sat;
            best_assignment = assignment;
            if (best_sat == m) break; // Optimal found
        }
        
        bool improved = true;
        while (improved) {
            if (double(clock() - start) > time_limit) break;
            improved = false;
            shuffle(vars.begin(), vars.end(), rng);
            
            for (int v : vars) {
                if (try_flip(v)) {
                    improved = true;
                    if (current_sat > best_sat) {
                        best_sat = current_sat;
                        best_assignment = assignment;
                        if (best_sat == m) goto finish;
                    }
                }
            }
        }
    }

finish:
    if (best_assignment.empty()) best_assignment.resize(n, 0); // Safety for m=0 or no time

    for (int i = 0; i < n; ++i) {
        cout << best_assignment[i] << (i == n - 1 ? "" : " ");
    }
    cout << "\n";

    return 0;
}