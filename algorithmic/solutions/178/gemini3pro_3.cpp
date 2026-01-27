#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>

using namespace std;

// Structure to represent a clause
struct Clause {
    int l[3];
};

int main() {
    // Optimize standard I/O operations for speed
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n, m;
    if (!(cin >> n >> m)) return 0;

    vector<Clause> clauses(m);
    for (int i = 0; i < m; ++i) {
        cin >> clauses[i].l[0] >> clauses[i].l[1] >> clauses[i].l[2];
    }

    // Vector to store the assignment of variables (1-based index)
    // -1: unassigned (though we fill sequentially so we don't strictly need -1)
    // 0: FALSE, 1: TRUE
    vector<int> assignment(n + 1, 0);

    // Method of Conditional Expectations
    // Iterate through each variable and choose the value (0 or 1) 
    // that maximizes the expected number of satisfied clauses.
    for (int i = 1; i <= n; ++i) {
        double w0 = 0.0; // Expected score if x[i] = 0
        double w1 = 0.0; // Expected score if x[i] = 1

        // Test both possibilities for the current variable x[i]
        for (int val = 0; val <= 1; ++val) {
            double current_w = 0.0;
            
            for (const auto& c : clauses) {
                bool satisfied = false;
                vector<int> future_lits;
                future_lits.reserve(3);
                
                for (int j = 0; j < 3; ++j) {
                    int lit = c.l[j];
                    int var = abs(lit);
                    bool is_pos = (lit > 0);
                    
                    if (var < i) {
                        // This variable has already been fixed in a previous step
                        int fixed_val = assignment[var];
                        // Check if this literal evaluates to TRUE
                        if ((is_pos && fixed_val == 1) || (!is_pos && fixed_val == 0)) {
                            satisfied = true;
                            break; 
                        }
                    } else if (var == i) {
                        // This is the variable we are currently deciding
                        if ((is_pos && val == 1) || (!is_pos && val == 0)) {
                            satisfied = true;
                            break;
                        }
                    } else {
                        // This variable is yet to be decided (future)
                        future_lits.push_back(lit);
                    }
                }

                if (satisfied) {
                    // Clause is already satisfied by fixed variables
                    current_w += 1.0;
                } else {
                    // Not satisfied by fixed variables
                    // Determine probability of satisfying it with future random assignments
                    if (future_lits.empty()) {
                        // No future variables left to satisfy this clause -> Prob = 0
                        current_w += 0.0;
                    } else {
                        // Check for tautology in future literals (e.g., A or not A)
                        bool tautology = false;
                        for (size_t a = 0; a < future_lits.size(); ++a) {
                            for (size_t b = a + 1; b < future_lits.size(); ++b) {
                                if (future_lits[a] == -future_lits[b]) {
                                    tautology = true;
                                    break;
                                }
                            }
                            if (tautology) break;
                        }

                        if (tautology) {
                            // Always satisfied regardless of assignment
                            current_w += 1.0;
                        } else {
                            // Count distinct variables in future literals
                            // Probability that a clause with k distinct random variables is satisfied is 1 - (1/2)^k
                            int distinct_vars = 0;
                            for (size_t a = 0; a < future_lits.size(); ++a) {
                                bool duplicate = false;
                                for (size_t b = 0; b < a; ++b) {
                                    if (abs(future_lits[a]) == abs(future_lits[b])) {
                                        duplicate = true;
                                        break;
                                    }
                                }
                                if (!duplicate) distinct_vars++;
                            }
                            current_w += (1.0 - pow(0.5, distinct_vars));
                        }
                    }
                }
            }
            
            if (val == 0) w0 = current_w;
            else w1 = current_w;
        }

        // Greedy choice: pick the value that yields higher expectation
        if (w1 >= w0) {
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