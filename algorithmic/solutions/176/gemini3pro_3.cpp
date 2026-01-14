#include <iostream>
#include <vector>
#include <algorithm>

using namespace std;

// Structure to keep track of clause status
struct Clause {
    bool satisfied;
    int k; // Number of currently unset literals in the clause
};

int main() {
    // Fast I/O
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n, m;
    if (!(cin >> n >> m)) return 0;

    vector<Clause> clauses(m);
    // occ[v][0] stores indices of clauses containing literal -v
    // occ[v][1] stores indices of clauses containing literal v
    vector<vector<vector<int>>> occ(n + 1, vector<vector<int>>(2));
    
    // Weights based on the method of conditional expectations.
    // The contribution of a clause to the expected number of satisfied clauses
    // is (1 - 0.5^k). The change in expectation when fixing a variable
    // effectively uses weights proportional to 2^(1-k).
    // We scale by 4 to keep integers:
    // k=1 -> weight 4
    // k=2 -> weight 2
    // k=3 -> weight 1
    int weights[] = {0, 4, 2, 1}; 

    for (int i = 0; i < m; ++i) {
        int input_lits[3];
        cin >> input_lits[0] >> input_lits[1] >> input_lits[2];
        
        // Normalize clause: remove duplicates
        vector<int> lits;
        lits.reserve(3);
        for (int x : input_lits) lits.push_back(x);
        
        sort(lits.begin(), lits.end());
        lits.erase(unique(lits.begin(), lits.end()), lits.end());
        
        bool is_tautology = false;
        // Check if clause contains both v and -v
        for (size_t j = 0; j < lits.size(); ++j) {
            for (size_t k_idx = j + 1; k_idx < lits.size(); ++k_idx) {
                if (lits[j] == -lits[k_idx]) {
                    is_tautology = true;
                    break;
                }
            }
            if (is_tautology) break;
        }

        if (is_tautology) {
            clauses[i].satisfied = true;
            clauses[i].k = 0; 
        } else {
            clauses[i].satisfied = false;
            clauses[i].k = lits.size();
            for (int lit : lits) {
                if (lit > 0) {
                    occ[lit][1].push_back(i);
                } else {
                    occ[-lit][0].push_back(i);
                }
            }
        }
    }

    vector<int> ans(n + 1);

    // Greedy assignment variable by variable
    for (int i = 1; i <= n; ++i) {
        long long balance = 0;
        
        // Calculate impact of setting x_i = 1
        // Gain from satisfying clauses with positive literal x_i
        for (int c_idx : occ[i][1]) {
            if (!clauses[c_idx].satisfied) {
                int k = clauses[c_idx].k;
                if (k >= 1 && k <= 3) balance += weights[k];
            }
        }

        // Calculate impact of setting x_i = 0 (loss for setting 1)
        // Gain from satisfying clauses with negative literal -x_i
        for (int c_idx : occ[i][0]) {
            if (!clauses[c_idx].satisfied) {
                int k = clauses[c_idx].k;
                if (k >= 1 && k <= 3) balance -= weights[k];
            }
        }

        if (balance >= 0) {
            ans[i] = 1;
            // x_i is TRUE
            // Mark clauses with x_i as satisfied
            for (int c_idx : occ[i][1]) {
                clauses[c_idx].satisfied = true;
            }
            // Decrement unset count for clauses with -x_i
            for (int c_idx : occ[i][0]) {
                if (!clauses[c_idx].satisfied) {
                    clauses[c_idx].k--;
                }
            }
        } else {
            ans[i] = 0;
            // x_i is FALSE
            // Mark clauses with -x_i as satisfied
            for (int c_idx : occ[i][0]) {
                clauses[c_idx].satisfied = true;
            }
            // Decrement unset count for clauses with x_i
            for (int c_idx : occ[i][1]) {
                if (!clauses[c_idx].satisfied) {
                    clauses[c_idx].k--;
                }
            }
        }
    }

    // Output results
    for (int i = 1; i <= n; ++i) {
        cout << ans[i] << (i == n ? "" : " ");
    }
    cout << "\n";

    return 0;
}