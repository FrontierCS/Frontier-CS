#include <iostream>
#include <vector>
#include <algorithm>

using namespace std;

int main() {
    // Optimize I/O operations for large input
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n, m;
    if (!(cin >> n >> m)) return 0;

    // pos_clauses[i] stores indices of clauses containing x_i
    // neg_clauses[i] stores indices of clauses containing -x_i
    vector<vector<int>> pos_clauses(n + 1);
    vector<vector<int>> neg_clauses(n + 1);
    
    // Track clause status
    vector<bool> is_satisfied(m, false);
    vector<int> k_count(m); // Current number of unassigned literals in clause
    vector<int> ans(n + 1); // Result assignment

    for (int j = 0; j < m; ++j) {
        int l[3];
        cin >> l[0] >> l[1] >> l[2];
        
        // Normalize clause: sort literals
        sort(l, l + 3);
        
        // Remove duplicate literals
        int unique_count = 0;
        for (int k = 0; k < 3; ++k) {
            if (k == 0 || l[k] != l[k-1]) {
                l[unique_count++] = l[k];
            }
        }

        // Check for tautology (contains both x and -x)
        bool tautology = false;
        for (int a = 0; a < unique_count; ++a) {
            for (int b = a + 1; b < unique_count; ++b) {
                if (l[a] == -l[b]) tautology = true;
            }
        }

        if (tautology) {
            is_satisfied[j] = true;
            k_count[j] = 0; 
            continue;
        }

        // Store clause references
        k_count[j] = unique_count;
        for (int a = 0; a < unique_count; ++a) {
            int lit = l[a];
            if (lit > 0) {
                pos_clauses[lit].push_back(j);
            } else {
                neg_clauses[-lit].push_back(j);
            }
        }
    }

    // Method of Conditional Expectations
    // We iterate through variables and greedily pick the assignment that maximizes
    // the expected number of satisfied clauses (weighted by probability mass).
    for (int i = 1; i <= n; ++i) {
        long long w1 = 0;
        long long w0 = 0;

        // Calculate potential gain for setting x_i = 1 (TRUE)
        // We sum 2^(-k) for unsatisfied clauses containing x_i.
        // We scale by multiplying by 8 to use integers:
        // k=1 (prob 0.5->1, diff 0.5) -> weight 4
        // k=2 (prob 0.75->0.875?? No.)
        // Actually, comparing Expected Values.
        // The comparison reduces to comparing sums of 2^(-k) where k is current unassigned count.
        // Scaled weights: k=1 -> 4, k=2 -> 2, k=3 -> 1.
        
        for (int idx : pos_clauses[i]) {
            if (is_satisfied[idx]) continue;
            w1 += (1 << (3 - k_count[idx]));
        }

        // Calculate potential gain for setting x_i = 0 (FALSE)
        for (int idx : neg_clauses[i]) {
            if (is_satisfied[idx]) continue;
            w0 += (1 << (3 - k_count[idx]));
        }

        if (w1 >= w0) {
            ans[i] = 1;
            // Mark satisfied clauses
            for (int idx : pos_clauses[i]) {
                is_satisfied[idx] = true;
            }
            // Decrement literal count for falsified clauses
            for (int idx : neg_clauses[i]) {
                if (!is_satisfied[idx]) {
                    k_count[idx]--;
                }
            }
        } else {
            ans[i] = 0;
            // Mark satisfied clauses
            for (int idx : neg_clauses[i]) {
                is_satisfied[idx] = true;
            }
            // Decrement literal count for falsified clauses
            for (int idx : pos_clauses[i]) {
                if (!is_satisfied[idx]) {
                    k_count[idx]--;
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