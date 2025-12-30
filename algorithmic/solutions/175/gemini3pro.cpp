#include <iostream>
#include <vector>
#include <algorithm>

using namespace std;

// Maximum number of variables and clauses as per constraints
const int MAXN = 3005;
const int MAXM = 2000005;

// Adjacency lists for literals to clauses
// pos[i] stores indices of clauses containing literal x_i
// neg[i] stores indices of clauses containing literal -x_i
vector<int> pos[MAXN];
vector<int> neg[MAXN];

// State arrays
// is_satisfied[j] is true if clause j is already satisfied by a previous assignment
// k[j] stores the number of currently unassigned literals in clause j
bool is_satisfied[MAXM];
int k[MAXM];

// Array to store the final truth assignment (1 for True, 0 for False)
int assignment[MAXN];

int main() {
    // Optimize standard I/O operations for speed
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n, m;
    if (!(cin >> n >> m)) return 0;

    for (int i = 0; i < m; ++i) {
        int l[3];
        cin >> l[0] >> l[1] >> l[2];

        // Sort the literals to handle duplicates easily
        sort(l, l + 3);
        // Remove duplicate literals in the same clause
        int distinct_count = unique(l, l + 3) - l;

        // Check for tautology (clause containing both x and -x)
        bool tautology = false;
        for (int x = 0; x < distinct_count; ++x) {
            for (int y = x + 1; y < distinct_count; ++y) {
                if (l[x] == -l[y]) {
                    tautology = true;
                    break;
                }
            }
            if (tautology) break;
        }

        if (tautology) {
            // Tautologies are always satisfied
            is_satisfied[i] = true;
            k[i] = 0; 
        } else {
            is_satisfied[i] = false;
            k[i] = distinct_count;
            // Build adjacency lists
            for (int j = 0; j < distinct_count; ++j) {
                int val = l[j];
                if (val > 0) {
                    pos[val].push_back(i);
                } else {
                    neg[-val].push_back(i);
                }
            }
        }
    }

    // Determine assignment using the Method of Conditional Expectations
    // This greedy approach guarantees satisfying at least 7/8 of clauses (weighted)
    for (int i = 1; i <= n; ++i) {
        long long score = 0;
        
        // Calculate the impact of setting x_i = TRUE
        // If x_i is TRUE:
        //  - Clauses in pos[i] become satisfied. Gain is related to probability 2^(-k).
        //  - Clauses in neg[i] lose a literal. Loss is related to probability drop.
        // The comparison reduces to weighted sums where weight(k) = 2^(-k).
        // We multiply weights by 8 to use integers: k=1 -> 4, k=2 -> 2, k=3 -> 1.
        
        for (int c_idx : pos[i]) {
            if (!is_satisfied[c_idx]) {
                score += (1 << (3 - k[c_idx]));
            }
        }
        for (int c_idx : neg[i]) {
            if (!is_satisfied[c_idx]) {
                score -= (1 << (3 - k[c_idx]));
            }
        }

        if (score >= 0) {
            // Set x_i = TRUE
            assignment[i] = 1;
            for (int c_idx : pos[i]) {
                is_satisfied[c_idx] = true;
            }
            for (int c_idx : neg[i]) {
                if (!is_satisfied[c_idx]) {
                    k[c_idx]--;
                }
            }
        } else {
            // Set x_i = FALSE
            assignment[i] = 0;
            for (int c_idx : neg[i]) {
                is_satisfied[c_idx] = true;
            }
            for (int c_idx : pos[i]) {
                if (!is_satisfied[c_idx]) {
                    k[c_idx]--;
                }
            }
        }
    }

    // Output the resulting assignment
    for (int i = 1; i <= n; ++i) {
        cout << assignment[i] << (i == n ? "" : " ");
    }
    cout << "\n";

    return 0;
}