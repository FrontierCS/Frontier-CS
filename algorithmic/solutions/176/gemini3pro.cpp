#include <iostream>
#include <vector>
#include <cmath>
#include <cstdlib>
#include <ctime>
#include <algorithm>

using namespace std;

// ----------------------
// Global Data Structures
// ----------------------

int n, m;

struct Clause {
    int l[3]; // literals: >0 for x, <0 for -x
};
vector<Clause> clauses;

// Adjacency lists: variable -> list of clause indices
vector<vector<int>> occ_pos; // clauses containing variable v as positive literal
vector<vector<int>> occ_neg; // clauses containing variable v as negative literal

// Assignment state
vector<int> assignment;      // assignment[v] \in {0, 1}
vector<int> sat_count;       // number of satisfied literals in clause c
vector<int> unsat_clauses;   // list of currently unsatisfied clause indices
vector<int> pos_in_unsat;    // maps clause index to position in unsat_clauses (-1 if satisfied)

// Best solution tracking
vector<int> best_assignment;
int best_unsat_cnt;

// ----------------------
// Helper Functions
// ----------------------

// Add clause c to unsatisfied list
void add_unsat(int c) {
    if (pos_in_unsat[c] != -1) return;
    pos_in_unsat[c] = unsat_clauses.size();
    unsat_clauses.push_back(c);
}

// Remove clause c from unsatisfied list
void remove_unsat(int c) {
    int idx = pos_in_unsat[c];
    if (idx == -1) return;
    int last_c = unsat_clauses.back();
    unsat_clauses[idx] = last_c;
    pos_in_unsat[last_c] = idx;
    unsat_clauses.pop_back();
    pos_in_unsat[c] = -1;
}

// Initialize assignment state based on current `assignment` vector
void init_state() {
    fill(sat_count.begin(), sat_count.end(), 0);
    unsat_clauses.clear();
    fill(pos_in_unsat.begin(), pos_in_unsat.end(), -1);

    for (int i = 0; i < m; ++i) {
        int cnt = 0;
        for (int k = 0; k < 3; ++k) {
            int lit = clauses[i].l[k];
            int var = abs(lit);
            if (lit > 0) {
                if (assignment[var] == 1) cnt++;
            } else {
                if (assignment[var] == 0) cnt++;
            }
        }
        sat_count[i] = cnt;
        if (cnt == 0) add_unsat(i);
    }
}

// Flip variable v and update state
void flip(int v) {
    int old_val = assignment[v];
    int new_val = 1 - old_val;
    assignment[v] = new_val;

    // Update clauses where v appears positively
    for (int c : occ_pos[v]) {
        if (new_val == 1) { 
            // 0 -> 1: literal becomes true
            if (sat_count[c] == 0) remove_unsat(c);
            sat_count[c]++;
        } else {
            // 1 -> 0: literal becomes false
            sat_count[c]--;
            if (sat_count[c] == 0) add_unsat(c);
        }
    }

    // Update clauses where v appears negatively
    for (int c : occ_neg[v]) {
        if (new_val == 0) {
            // 1 -> 0: -v becomes true
            if (sat_count[c] == 0) remove_unsat(c);
            sat_count[c]++;
        } else {
            // 0 -> 1: -v becomes false
            sat_count[c]--;
            if (sat_count[c] == 0) add_unsat(c);
        }
    }
}

// Calculate number of clauses that would become unsatisfied if v is flipped
int get_break_count(int v) {
    int cnt = 0;
    int val = assignment[v];
    
    // If val is 1, flipping to 0 breaks clauses where v is the ONLY true literal.
    // These must be in occ_pos.
    if (val == 1) {
        for (int c : occ_pos[v]) {
            if (sat_count[c] == 1) cnt++;
        }
    } 
    // If val is 0, flipping to 1 breaks clauses where -v is the ONLY true literal.
    // These must be in occ_neg.
    else {
        for (int c : occ_neg[v]) {
            if (sat_count[c] == 1) cnt++;
        }
    }
    return cnt;
}

int main() {
    // Optimization for faster I/O
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    srand(time(NULL));

    if (!(cin >> n >> m)) return 0;

    clauses.resize(m);
    occ_pos.resize(n + 1);
    occ_neg.resize(n + 1);
    assignment.resize(n + 1);
    sat_count.resize(m);
    pos_in_unsat.resize(m, -1);

    for (int i = 0; i < m; ++i) {
        for (int k = 0; k < 3; ++k) {
            int lit;
            cin >> lit;
            clauses[i].l[k] = lit;
            if (lit > 0) occ_pos[lit].push_back(i);
            else occ_neg[-lit].push_back(i);
        }
    }

    // Initial random assignment
    for (int i = 1; i <= n; ++i) {
        assignment[i] = rand() % 2;
    }
    init_state();

    best_assignment = assignment;
    best_unsat_cnt = unsat_clauses.size();

    // WalkSAT parameters
    int max_flips = 500000; 
    int max_tries = (m == 0) ? 0 : 10;
    int flips_per_try = (max_tries > 0) ? (max_flips / max_tries) : 0;
    
    // Probability (in percent) to make a random move
    int noise_prob = 50; 

    for (int t = 0; t < max_tries; ++t) {
        if (t > 0) {
            // Restart with random assignment
            for (int i = 1; i <= n; ++i) assignment[i] = rand() % 2;
            init_state();
        }

        for (int f = 0; f < flips_per_try; ++f) {
            if (unsat_clauses.empty()) {
                best_assignment = assignment;
                goto end_search;
            }

            // Update best
            if ((int)unsat_clauses.size() < best_unsat_cnt) {
                best_unsat_cnt = unsat_clauses.size();
                best_assignment = assignment;
            }

            // 1. Pick a random unsatisfied clause
            int rand_idx = rand() % unsat_clauses.size();
            int c_idx = unsat_clauses[rand_idx];

            // 2. Identify variables in this clause
            int vars[3];
            for(int k=0; k<3; ++k) vars[k] = abs(clauses[c_idx].l[k]);

            // 3. Select variable to flip using WalkSAT heuristic
            int best_var = -1;
            int min_break = 1e9;
            vector<int> zero_break;
            
            for (int k = 0; k < 3; ++k) {
                int v = vars[k];
                int b = get_break_count(v);
                if (b == 0) zero_break.push_back(v);
                if (b < min_break) {
                    min_break = b;
                    best_var = v;
                }
            }

            if (!zero_break.empty()) {
                // Free move exists
                best_var = zero_break[rand() % zero_break.size()];
            } else {
                // No free move
                if ((rand() % 100) < noise_prob) {
                    // Random walk
                    best_var = vars[rand() % 3];
                } else {
                    // Greedy: pick var with min break
                }
            }

            flip(best_var);
        }
    }

end_search:
    // Output result
    for (int i = 1; i <= n; ++i) {
        cout << best_assignment[i] << (i == n ? "" : " ");
    }
    cout << "\n";

    return 0;
}