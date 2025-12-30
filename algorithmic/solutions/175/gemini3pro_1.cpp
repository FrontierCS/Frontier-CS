#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>

using namespace std;

int main() {
    // Optimize standard I/O for speed as m can be up to 2,000,000
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n, m;
    if (!(cin >> n >> m)) return 0;

    // occ[i] stores packed references to clauses containing variable i
    // Format: (clause_index << 1) | (is_positive ? 1 : 0)
    // Variable indices are 1-based, so size n + 1
    // Using vector of vectors for adjacency list
    vector<vector<int>> occ(n + 1);

    for (int i = 0; i < m; ++i) {
        int u, v, w;
        cin >> u >> v >> w;
        
        // Store occurrence of each variable
        // abs(u) gets variable index 1..n
        // u > 0 indicates positive literal, u < 0 indicates negative literal
        occ[abs(u)].push_back((i << 1) | (u > 0));
        occ[abs(v)].push_back((i << 1) | (v > 0));
        occ[abs(w)].push_back((i << 1) | (w > 0));
    }

    // satisfied[c] is 1 if clause c is currently satisfied, 0 otherwise
    vector<char> satisfied(m, 0);
    
    // k[c] tracks number of unassigned literals in clause c. 
    // Initially each clause has 3 literals.
    vector<int> k(m, 3);

    vector<int> result(n + 1);

    // Weights used for the greedy heuristic (method of conditional expectations).
    // The weight represents the probability mass gained/lost.
    // Specifically, proportional to (0.5)^k.
    // Scaled by 8 to use integers:
    // k=1 -> (0.5)^1 * 8 = 4
    // k=2 -> (0.5)^2 * 8 = 2
    // k=3 -> (0.5)^3 * 8 = 1
    // Index 0 is unused/dummy.
    const int WEIGHTS[4] = {0, 4, 2, 1}; 

    // Iterate through each variable and assign a value greedily
    for (int i = 1; i <= n; ++i) {
        long long score = 0;
        
        // Pass 1: Calculate greedy score for setting x_i = TRUE
        // Score > 0 implies TRUE is better (reduces failure probability more than FALSE)
        for (int packed : occ[i]) {
            int c = packed >> 1;
            if (satisfied[c]) continue;
            
            bool is_positive = packed & 1;
            int current_k = k[c];
            // current_k should be >= 1 here because clause is not satisfied and we are visiting an unset variable in it
            int w = WEIGHTS[current_k];
            
            if (is_positive) {
                // Setting x_i=T satisfies the clause (failure prob drops to 0)
                score += w;
            } else {
                // Setting x_i=T makes literal -x_i False, clause shrinks (failure prob increases)
                score -= w;
            }
        }

        // Decision
        int val = (score >= 0) ? 1 : 0;
        result[i] = val;

        // Pass 2: Update clause statuses based on the decision
        for (int packed : occ[i]) {
            int c = packed >> 1;
            if (satisfied[c]) continue;
            
            bool is_positive = packed & 1;
            // Check if the chosen value satisfies the clause
            // (val=1 and literal is x) OR (val=0 and literal is -x)
            if (val == is_positive) {
                satisfied[c] = 1;
            } else {
                // Literal became false, so one less unset variable remains in the clause
                k[c]--;
            }
        }
    }

    // Output results
    for (int i = 1; i <= n; ++i) {
        cout << result[i] << (i == n ? "" : " ");
    }
    cout << "\n";

    return 0;
}