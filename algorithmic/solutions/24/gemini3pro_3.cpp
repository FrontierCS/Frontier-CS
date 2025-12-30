#include <iostream>
#include <vector>
#include <algorithm>
#include <cctype>

using namespace std;

// Global matrix to store the input
int C[2005][2005];
int n;

// Function to solve a single test case
void solve() {
    // Read input n
    if (!(cin >> n)) return;

    // Read the matrix
    // The input format specifies C_i,j as integers (0 or 1).
    // They might be separated by spaces or not. The problem statement example shows "001", but sample 2 shows "0000".
    // Usually "n integers" implies space-separated, but "001" implies characters.
    // The sample inputs are compact. We should handle both space-separated and dense formats.
    // The safest way is to read non-whitespace characters.
    for (int i = 1; i <= n; ++i) {
        for (int j = 1; j <= n; ++j) {
            char c;
            while (cin.get(c) && !isdigit(c));
            C[i][j] = c - '0';
        }
    }

    // p stores the permutation. Initially just {1}.
    vector<int> p;
    p.reserve(n);
    p.push_back(1);

    // path_changes counts the number of times C[p[i], p[i+1]] != C[p[i+1], p[i+2]]
    // for the linear path.
    int path_changes = 0;

    // Greedily insert 2..n
    for (int k = 2; k <= n; ++k) {
        bool inserted = false;
        int m = p.size(); // Current size before insertion
        
        // Iterate insertion positions from end to start to prefer lexicographically smaller p
        // Inserting closer to the end keeps smaller numbers (already in p) at the beginning.
        for (int j = m; j >= 0; --j) {
            
            // Calculate change in 'path_changes' if we insert k at j
            int changes_removed = 0;
            int changes_added = 0;

            // Define neighbors in the original path p
            int u = (j > 0) ? p[j-1] : -1;
            int v = (j < m) ? p[j] : -1;
            int prev_u = (j > 1) ? p[j-2] : -1;
            int next_v = (j < m-1) ? p[j+1] : -1;

            // Colors of existing edges
            int c_prev = (prev_u != -1 && u != -1) ? C[prev_u][u] : -1;
            int c_curr = (u != -1 && v != -1) ? C[u][v] : -1;
            int c_next = (v != -1 && next_v != -1) ? C[v][next_v] : -1;

            // If an edge (u, v) exists, it might contribute to changes with (prev_u, u) and (v, next_v)
            if (c_curr != -1) {
                if (c_prev != -1 && c_prev != c_curr) changes_removed++;
                if (c_next != -1 && c_curr != c_next) changes_removed++;
            }

            // Colors of new edges: (u, k) and (k, v)
            int c_uk = (u != -1) ? C[u][k] : -1;
            int c_kv = (v != -1) ? C[k][v] : -1;

            // Check changes with new edges
            if (c_prev != -1 && c_uk != -1) {
                if (c_prev != c_uk) changes_added++;
            }
            if (c_uk != -1 && c_kv != -1) {
                if (c_uk != c_kv) changes_added++;
            }
            if (c_kv != -1 && c_next != -1) {
                if (c_kv != c_next) changes_added++;
            }

            int new_path_changes = path_changes - changes_removed + changes_added;

            // Now check the total condition including the wrap-around edge c_n
            // The condition "almost monochromatic" applies to indices 1 <= i < n
            // which covers pairs (c_1, c_2), ..., (c_{n-1}, c_n).
            // c_n is the edge (p_n, p_1).
            // We need to verify if (last_edge != wrap_edge) adds an extra change.
            
            int new_first = (j == 0) ? k : p[0];
            int new_last = (j == m) ? k : p[m-1];
            // Identify the second to last element in the new path
            int new_sec_last;
            if (j == m) new_sec_last = p[m-1];
            else if (j == m-1) new_sec_last = k;
            else new_sec_last = p[m-2]; // Shifted index m-2 becomes m-1

            int total_changes = new_path_changes;
            
            // If new size >= 2 (which is always true for k >= 2), check the boundary
            if (m + 1 >= 2) {
                int c_last_path = C[new_sec_last][new_last];
                int c_wrap = C[new_last][new_first];
                if (c_last_path != c_wrap) total_changes++;
            }

            if (total_changes <= 1) {
                p.insert(p.begin() + j, k);
                path_changes = new_path_changes;
                inserted = true;
                break;
            }
        }

        if (!inserted) {
            // Should not happen based on existence theorems for N >= 3
            cout << -1 << endl;
            return;
        }
    }

    // Output the permutation
    for (int i = 0; i < n; ++i) {
        cout << p[i] << (i == n-1 ? "" : " ");
    }
    cout << endl;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    // Loop to handle multiple test cases
    while (cin.peek() != EOF) {
        solve();
        // Skip any trailing whitespace to correctly detect EOF
        while (isspace(cin.peek())) cin.get();
    }
    return 0;
}