#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <ctime>
#include <cstdlib>

using namespace std;

// Structure to represent a clause
struct Clause {
    int l1, l2; // Literals
    int v1, v2; // Variable indices (1-based)
};

int n, m;
vector<Clause> clauses;
vector<vector<int>> var_clauses; // Mapping from variable to list of clause indices it appears in
vector<int> assignment; // Current assignment: 1-based, 0 or 1
vector<int> gain; // Gain in score if variable is flipped
vector<int> best_assignment; // Stores the best assignment found so far
int current_score = 0;
int max_score = -1;

// Helper to check if a literal is true under the current assignment
inline bool is_true(int literal, const vector<int>& assign) {
    int v = abs(literal);
    // if literal > 0, it is true if assign[v] == 1
    // if literal < 0, it is true if assign[v] == 0
    return (literal > 0) == (bool)assign[v];
}

// Function to update gains of variables involved in a specific clause
// sign = 1 adds contribution, sign = -1 removes contribution
void add_clause_gain(int c_idx, int sign) {
    const auto& c = clauses[c_idx];
    bool val1 = is_true(c.l1, assignment);
    bool val2 = is_true(c.l2, assignment);
    int current_sat = (val1 || val2); // 1 if satisfied, 0 otherwise

    // Calculate effect of flipping v1 on this clause
    {
        // If we flip v1, does l1 change? Yes.
        bool n_val1 = !val1; 
        // If we flip v1, does l2 change? Only if v2 is the same variable as v1.
        bool n_val2 = (c.v2 == c.v1) ? !val2 : val2;
        int new_sat = (n_val1 || n_val2);
        int diff = new_sat - current_sat;
        if (diff != 0) gain[c.v1] += sign * diff;
    }

    // Calculate effect of flipping v2 on this clause (if v2 is distinct from v1)
    if (c.v1 != c.v2) {
        bool n_val1 = val1; // l1 doesn't change when v2 flipped
        bool n_val2 = !val2; // l2 changes
        int new_sat = (n_val1 || n_val2);
        int diff = new_sat - current_sat;
        if (diff != 0) gain[c.v2] += sign * diff;
    }
}

// Initialize scores and gains based on the current assignment
void build() {
    fill(gain.begin(), gain.end(), 0);
    current_score = 0;
    for (int i = 0; i < m; ++i) {
        if (is_true(clauses[i].l1, assignment) || is_true(clauses[i].l2, assignment)) {
            current_score++;
        }
        add_clause_gain(i, 1);
    }
}

// Flip the value of variable u and update system state
void flip(int u) {
    // 1. Remove contribution of affected clauses from gains
    for (int c_idx : var_clauses[u]) {
        add_clause_gain(c_idx, -1);
    }
    
    // 2. Update assignment and current score
    current_score += gain[u];
    assignment[u] = 1 - assignment[u];
    
    // 3. Add contribution of affected clauses to gains based on new state
    for (int c_idx : var_clauses[u]) {
        add_clause_gain(c_idx, 1);
    }
}

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    srand(time(NULL));

    if (!(cin >> n >> m)) return 0;

    clauses.resize(m);
    var_clauses.resize(n + 1);
    for (int i = 0; i < m; ++i) {
        cin >> clauses[i].l1 >> clauses[i].l2;
        clauses[i].v1 = abs(clauses[i].l1);
        clauses[i].v2 = abs(clauses[i].l2);
        
        var_clauses[clauses[i].v1].push_back(i);
        // Avoid adding the same clause index twice if the clause is like (x v x)
        if (clauses[i].v1 != clauses[i].v2) {
            var_clauses[clauses[i].v2].push_back(i);
        }
    }

    assignment.resize(n + 1);
    best_assignment.resize(n + 1);
    gain.resize(n + 1);

    // Initial random assignment
    for (int i = 1; i <= n; ++i) assignment[i] = rand() % 2;
    best_assignment = assignment;

    clock_t start_time = clock();
    double time_limit = 0.95; // seconds

    build();
    max_score = current_score;

    vector<int> candidates;
    candidates.reserve(n);

    // Main loop: Hill Climbing with Random Restarts
    while ((double)(clock() - start_time) / CLOCKS_PER_SEC < time_limit) {
        int max_g = -1e9;
        candidates.clear();
        
        // Find variable(s) with the best gain
        for (int i = 1; i <= n; ++i) {
            if (gain[i] > max_g) {
                max_g = gain[i];
                candidates.clear();
                candidates.push_back(i);
            } else if (gain[i] == max_g) {
                candidates.push_back(i);
            }
        }

        // If we can improve the score, do it
        if (max_g > 0) {
            int pick = candidates[rand() % candidates.size()];
            flip(pick);
            if (current_score > max_score) {
                max_score = current_score;
                best_assignment = assignment;
                if (max_score == m) break; // All satisfied
            }
        } else {
            // Local optimum reached: Restart with a new random assignment
            for (int i = 1; i <= n; ++i) assignment[i] = rand() % 2;
            build();
            if (current_score > max_score) {
                max_score = current_score;
                best_assignment = assignment;
            }
        }
        
        // Edge case for m=0
        if (m == 0) break;
    }

    // Output result
    for (int i = 1; i <= n; ++i) {
        cout << best_assignment[i] << (i == n ? "" : " ");
    }
    cout << "\n";

    return 0;
}