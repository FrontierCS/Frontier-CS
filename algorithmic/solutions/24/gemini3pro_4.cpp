#include <iostream>
#include <vector>
#include <string>
#include <algorithm>

using namespace std;

const int MAXN = 2005;
int C[MAXN][MAXN];
int p[MAXN];
bool visited[MAXN];
int n;
bool found_sol;

// dfs to construct the permutation
// u: current vertex
// count: number of vertices in path so far
// phase: 0 (start), 1 (first color block), 2 (second color block)
// current_color: color of the current block
void dfs(int u, int count, int phase, int current_color) {
    if (found_sol) return;

    if (count == n) {
        // Check closing edge (u, p[1])
        int last_edge_color = C[u][p[1]];
        bool ok = false;
        if (phase == 1) {
            // If we are still in phase 1 (only one color seen so far),
            // the closing edge can be either color.
            // If it's same as current_color, we have 0 changes.
            // If it's different, we have 1 change in the linear sequence c_1...c_n
            // (specifically at c_{n-1} vs c_n, or just c_n being diff).
            // Wait, definition is changes in c_i vs c_{i+1} for 1 <= i < n.
            // If phase 1, all c_1...c_{n-1} are same. 0 changes.
            // c_n can be anything.
            ok = true;
        } else if (phase == 2) {
            // If we switched to phase 2, we must stick with that color.
            // The closing edge corresponds to c_n.
            // The sequence is A...AB...B.
            // Changes happen at the switch A->B.
            // We must ensure no change at the end if we want linear property?
            // Actually, if we are in phase 2 (color B), the sequence of edges so far is A...A B...B.
            // c_{n-1} is B.
            // We need c_n (edge u->p[1]) to be B to avoid a change at index n-1?
            // No, the condition is number of indices i < n where c_i != c_{i+1}.
            // So we check c_{n-1} vs c_n.
            // c_{n-1} is current_color (B).
            // If c_n is A, then we have a change at n-1.
            // We already had a change when switching from A to B.
            // So that would be 2 changes. Invalid.
            // Thus c_n must be B.
            if (last_edge_color == current_color) ok = true;
        }

        if (ok) {
            found_sol = true;
            for (int i = 1; i <= n; ++i) {
                cout << p[i] << (i == n ? "" : " ");
            }
            cout << "\n";
        }
        return;
    }

    // Iterate through candidates in increasing order for lexicographical minimality
    for (int v = 1; v <= n; ++v) {
        if (found_sol) return;
        if (!visited[v]) {
            int color = C[u][v];
            int next_phase = phase;
            int next_color = current_color;
            bool possible = false;

            if (phase == 0) {
                // First edge determines the first phase
                next_phase = 1;
                next_color = color;
                possible = true;
            } else if (phase == 1) {
                if (color == current_color) {
                    possible = true; // Continue with same color
                } else {
                    next_phase = 2; // Switch color
                    next_color = color;
                    possible = true;
                }
            } else { // phase == 2
                if (color == current_color) {
                    possible = true; // Must continue with same color
                }
                // Cannot switch again
            }

            if (possible) {
                visited[v] = true;
                p[count + 1] = v;
                dfs(v, count + 1, next_phase, next_color);
                visited[v] = false;
            }
        }
    }
}

void solve() {
    for (int i = 1; i <= n; ++i) {
        string row;
        cin >> row;
        for (int j = 1; j <= n; ++j) {
            C[i][j] = row[j - 1] - '0';
        }
    }

    for (int i = 1; i <= n; ++i) visited[i] = false;
    found_sol = false;

    // We want the lexicographically smallest permutation.
    // Since we are looking for a cycle, we can always rotate it to start with 1.
    // Thus p[1] = 1 is fixed.
    p[1] = 1;
    visited[1] = true;

    // Start DFS
    dfs(1, 1, 0, -1);

    if (!found_sol) {
        cout << -1 << "\n";
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    while (cin >> n) {
        solve();
    }
    return 0;
}