#include <iostream>
#include <vector>
#include <numeric>
#include <set>

using namespace std;

// Function to perform a query and get the result.
int query(int i, int j) {
    cout << "? " << i << " " << j << endl;
    int result;
    cin >> result;
    return result;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    cin >> n;

    vector<int> p(n + 1);

    // This approach works for all n within constraints.
    // For very small n (e.g., n <= 92), an O(n^2) query approach is also possible
    // but this O(n) query solution is more general.

    // Step 1: Find p[1] using n-1 queries
    vector<int> q1(n + 1);
    for (int i = 2; i <= n; ++i) {
        q1[i] = query(1, i);
    }
    
    p[1] = -1; // Represents all bits set to 1
    for (int i = 2; i <= n; ++i) {
        if (p[1] == -1) {
            p[1] = q1[i];
        } else {
            p[1] &= q1[i];
        }
    }

    // Step 2: Find p[2] using n-2 queries
    vector<int> q2(n + 1);
    q2[1] = q1[2]; // Reuse query for (1,2)
    for (int i = 3; i <= n; ++i) {
        q2[i] = query(2, i);
    }
    
    p[2] = q1[2];
    for (int i = 3; i <= n; ++i) {
        p[2] &= q2[i];
    }

    // Step 3: Deduce remaining elements without more queries
    set<int> remaining_values;
    for (int i = 0; i < n; ++i) {
        remaining_values.insert(i);
    }
    remaining_values.erase(p[1]);
    remaining_values.erase(p[2]);

    int A = p[1] & p[2];
    vector<int> v(n + 1);
    vector<int> unsolved_indices;
    
    for (int i = 3; i <= n; ++i) {
        v[i] = q1[i] & q2[i];
        unsolved_indices.push_back(i);
    }
    
    vector<vector<int>> candidates(n + 1);
    for (int i : unsolved_indices) {
        for (int u : remaining_values) {
            if ((A | u) == v[i]) {
                candidates[i].push_back(u);
            }
        }
    }

    while (!unsolved_indices.empty()) {
        int solved_idx = -1;
        int solved_val = -1;

        for (int i : unsolved_indices) {
            if (candidates[i].size() == 1) {
                solved_idx = i;
                solved_val = candidates[i][0];
                p[solved_idx] = solved_val;
                remaining_values.erase(solved_val);
                break;
            }
        }

        vector<int> next_unsolved;
        for (int i : unsolved_indices) {
            if (i != solved_idx) {
                next_unsolved.push_back(i);
                vector<int> next_candidates;
                for(int cand : candidates[i]) {
                    if (cand != solved_val) {
                        next_candidates.push_back(cand);
                    }
                }
                candidates[i] = next_candidates;
            }
        }
        unsolved_indices = next_unsolved;
    }

    // Final Step: Output the permutation
    cout << "! ";
    for (int i = 1; i <= n; ++i) {
        cout << p[i] << (i == n ? "" : " ");
    }
    cout << endl;

    return 0;
}