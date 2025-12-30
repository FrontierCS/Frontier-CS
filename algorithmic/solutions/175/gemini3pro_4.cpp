#include <iostream>
#include <vector>
#include <algorithm>

using namespace std;

int main() {
    // Optimization for faster I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n, m;
    if (!(cin >> n >> m)) return 0;

    // Adjacency lists mapping variables to the clauses they appear in.
    // pos[i] stores indices of clauses where variable i appears as a positive literal.
    // neg[i] stores indices of clauses where variable i appears as a negative literal.
    // Static allocation to avoid stack overflow and handle limits efficiently.
    static vector<int> pos[3001];
    static vector<int> neg[3001];
    
    // Arrays to store the state of each clause.
    // satisfied[i]: true if clause i is already satisfied by a variable assignment.
    // k[i]: number of currently active (unassigned) literals in clause i.
    static bool satisfied[2000005];
    static int k[2000005];

    for (int i = 0; i < m; ++i) {
        int l[3];
        cin >> l[0] >> l[1] >> l[2];
        
        // Sort and unique to handle duplicate literals within a single clause (e.g., x v x v y)
        sort(l, l + 3);
        int distinct_count = unique(l, l + 3) - l;
        
        k[i] = distinct_count;
        satisfied[i] = false;
        
        for (int j = 0; j < distinct_count; ++j) {
            int val = l[j];
            if (val > 0) {
                pos[val].push_back(i);
            } else {
                neg[-val].push_back(i);
            }
        }
    }

    vector<int> result(n + 1);

    // Weights used to estimate the "gain" of satisfying a clause.
    // This implements the method of conditional expectations / Johnson's algorithm.
    // The probability of a clause with k unassigned literals failing (if remaining are random) is (1/2)^k.
    // We want to minimize failure probability, or maximize success probability.
    // Satisfying a clause increases probability from 1-(1/2)^k to 1. Gain is (1/2)^k.
    // Falsifying a literal decreases probability from 1-(1/2)^k to 1-(1/2)^(k-1). Loss is (1/2)^k.
    // We compare sum of gains for setting x_i=TRUE vs x_i=FALSE.
    // Scaled by 8 for integer arithmetic: (1/2)^1 -> 4, (1/2)^2 -> 2, (1/2)^3 -> 1.
    int weights[4] = {0, 4, 2, 1}; 

    for (int i = 1; i <= n; ++i) {
        long long score_true = 0;
        long long score_false = 0;

        // Calculate score for setting x_i = TRUE
        // If x_i = TRUE, clauses in pos[i] become satisfied.
        for (int c_idx : pos[i]) {
            if (!satisfied[c_idx]) {
                if (k[c_idx] >= 1 && k[c_idx] <= 3) 
                    score_true += weights[k[c_idx]];
            }
        }
        
        // Calculate score for setting x_i = FALSE
        // If x_i = FALSE, clauses in neg[i] become satisfied.
        for (int c_idx : neg[i]) {
            if (!satisfied[c_idx]) {
                if (k[c_idx] >= 1 && k[c_idx] <= 3) 
                    score_false += weights[k[c_idx]];
            }
        }

        // Greedy choice: pick the assignment with the higher score
        bool assign_true = (score_true >= score_false);
        result[i] = assign_true ? 1 : 0;

        // Lists of clauses affected by the choice
        const vector<int> &satisfy_list = assign_true ? pos[i] : neg[i];
        const vector<int> &falsify_list = assign_true ? neg[i] : pos[i];

        // Mark clauses that become satisfied
        for (int c_idx : satisfy_list) {
            satisfied[c_idx] = true;
        }

        // For clauses where a literal became false, decrement the count of available literals k
        // This makes them more "critical" (higher weight) for subsequent variables
        for (int c_idx : falsify_list) {
            if (!satisfied[c_idx]) {
                k[c_idx]--;
            }
        }
    }

    // Output the assignment
    for (int i = 1; i <= n; ++i) {
        cout << result[i] << (i == n ? "" : " ");
    }
    cout << "\n";

    return 0;
}