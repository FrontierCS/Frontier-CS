#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

using namespace std;

int main() {
    // Optimize I/O operations for performance
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n, m;
    if (!(cin >> n >> m)) return 0;

    // Adjacency lists: pos[i] stores clause indices where variable i is positive
    // neg[i] stores clause indices where variable i is negative
    vector<vector<int>> pos(n + 1), neg(n + 1);
    vector<int> degree(n + 1, 0);

    for (int i = 0; i < m; ++i) {
        int l1, l2, l3;
        cin >> l1 >> l2 >> l3;
        
        auto add_lit = [&](int lit, int c_idx) {
            if (lit > 0) {
                pos[lit].push_back(c_idx);
                degree[lit]++;
            } else {
                neg[-lit].push_back(c_idx);
                degree[-lit]++;
            }
        };
        add_lit(l1, i);
        add_lit(l2, i);
        add_lit(l3, i);
    }

    // Processing order: variables with higher frequency first
    // This is a heuristic that generally improves the result of the greedy strategy
    vector<int> p(n);
    iota(p.begin(), p.end(), 1);
    sort(p.begin(), p.end(), [&](int a, int b) {
        return degree[a] > degree[b];
    });

    vector<bool> sat(m, false); // Tracks if clause i is satisfied
    vector<int> k(m, 3);        // Tracks number of unassigned literals in clause i
    vector<int> ans(n + 1, 0);  // Stores the result assignment

    // Weights corresponding to (1/2)^k scaled by 8
    // k=1 => 4, k=2 => 2, k=3 => 1
    auto get_weight = [&](int unassigned_count) -> int {
        if (unassigned_count == 1) return 4;
        if (unassigned_count == 2) return 2;
        if (unassigned_count == 3) return 1;
        return 0; 
    };

    // Greedy strategy using Method of Conditional Expectations
    for (int i : p) {
        long long w_pos = 0;
        long long w_neg = 0;

        // Calculate score for setting x_i = 1 (TRUE)
        // Benefit: clauses in pos[i] become satisfied (remove risk of unsat)
        for (int c_idx : pos[i]) {
            if (!sat[c_idx]) {
                w_pos += get_weight(k[c_idx]);
            }
        }
        
        // Calculate score for setting x_i = 0 (FALSE)
        // Benefit: clauses in neg[i] become satisfied
        for (int c_idx : neg[i]) {
            if (!sat[c_idx]) {
                w_neg += get_weight(k[c_idx]);
            }
        }

        if (w_pos >= w_neg) {
            ans[i] = 1;
            // Clauses with x_i become satisfied
            for (int c_idx : pos[i]) {
                sat[c_idx] = true;
            }
            // Clauses with -x_i lose a literal
            for (int c_idx : neg[i]) {
                if (!sat[c_idx]) {
                    k[c_idx]--;
                }
            }
        } else {
            ans[i] = 0;
            // Clauses with -x_i become satisfied
            for (int c_idx : neg[i]) {
                sat[c_idx] = true;
            }
            // Clauses with x_i lose a literal
            for (int c_idx : pos[i]) {
                if (!sat[c_idx]) {
                    k[c_idx]--;
                }
            }
        }
    }

    // Output the assignment
    for (int i = 1; i <= n; ++i) {
        cout << ans[i] << (i == n ? "" : " ");
    }
    cout << "\n";

    return 0;
}