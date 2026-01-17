#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>

using namespace std;

struct Clause {
    int l[3];
};

int n, m;
vector<Clause> clauses;
vector<int> assignment; // Stores current assignment: -1 (unknown), 0 (false), 1 (true)
vector<vector<int>> var_in_clauses; // Mapping from variable to list of clause indices it appears in

// Function to calculate the probability that a clause is satisfied
// given the current partial assignment.
// Unassigned variables are treated as random with P(True)=0.5
double get_clause_prob(int c_idx) {
    const Clause& c = clauses[c_idx];
    
    // Check if clause is already satisfied by a determined variable
    // Also collect literals that are not False
    vector<int> active_lits;
    for (int j = 0; j < 3; ++j) {
        int lit = c.l[j];
        int var = abs(lit);
        bool is_pos = (lit > 0);
        
        if (assignment[var] != -1) {
            // Variable is fixed
            bool val = (assignment[var] == 1);
            if (val == is_pos) {
                // Literal is True -> Clause is satisfied
                return 1.0;
            }
            // If Literal is False, it effectively disappears from the clause
        } else {
            // Variable is unknown, keep the literal
            active_lits.push_back(lit);
        }
    }
    
    // If no literals left and not satisfied, probability is 0
    if (active_lits.empty()) return 0.0;
    
    // Check for tautologies in undetermined part (e.g. L and -L in same clause)
    // Tautology means it will certainly be satisfied regardless of assignment
    for (size_t i = 0; i < active_lits.size(); ++i) {
        for (size_t k = i + 1; k < active_lits.size(); ++k) {
            if (active_lits[i] == -active_lits[k]) return 1.0; 
        }
    }
    
    // Sort and remove duplicates (e.g. x v x -> x)
    sort(active_lits.begin(), active_lits.end());
    active_lits.erase(unique(active_lits.begin(), active_lits.end()), active_lits.end());
    
    // The probability is 1 - (1/2)^k, where k is number of unique undetermined variables
    return 1.0 - pow(0.5, (double)active_lits.size());
}

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> n >> m)) return 0;
    
    clauses.resize(m);
    var_in_clauses.resize(n + 1);
    assignment.assign(n + 1, -1); // Initialize all variables as unknown

    for (int i = 0; i < m; ++i) {
        cin >> clauses[i].l[0] >> clauses[i].l[1] >> clauses[i].l[2];
        // Record which clauses contain which variables for optimization
        for (int j = 0; j < 3; ++j) {
            var_in_clauses[abs(clauses[i].l[j])].push_back(i);
        }
    }

    // Deduplicate clause indices in adjacency list
    for (int i = 1; i <= n; ++i) {
        sort(var_in_clauses[i].begin(), var_in_clauses[i].end());
        var_in_clauses[i].erase(unique(var_in_clauses[i].begin(), var_in_clauses[i].end()), var_in_clauses[i].end());
    }

    // Iterate through each variable and determine its value greedily based on expected number of satisfied clauses
    // This is the method of conditional expectations which guarantees at least 7/8 of clauses are satisfied.
    for (int i = 1; i <= n; ++i) {
        double prob0 = 0;
        double prob1 = 0;
        
        // Calculate expected contribution of relevant clauses if x_i = 0
        assignment[i] = 0;
        for (int c_idx : var_in_clauses[i]) {
            prob0 += get_clause_prob(c_idx);
        }
        
        // Calculate expected contribution of relevant clauses if x_i = 1
        assignment[i] = 1;
        for (int c_idx : var_in_clauses[i]) {
            prob1 += get_clause_prob(c_idx);
        }
        
        // Greedily choose the assignment that gives higher probability sum
        if (prob1 >= prob0) {
            assignment[i] = 1;
        } else {
            assignment[i] = 0;
        }
    }

    // Output the result
    for (int i = 1; i <= n; ++i) {
        cout << assignment[i] << (i == n ? "" : " ");
    }
    cout << "\n";

    return 0;
}