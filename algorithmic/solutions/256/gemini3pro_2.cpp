#include <iostream>
#include <vector>
#include <cstdlib>

using namespace std;

// Global grid to store determined values. -1 means undetermined.
int grid[55][55];
int n;

// Function to perform a query
int query(int r1, int c1, int r2, int c2) {
    cout << "? " << r1 << " " << c1 << " " << r2 << " " << c2 << endl;
    int res;
    cin >> res;
    if (res == -1) exit(0);
    return res;
}

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> n)) return 0;

    // Initialize grid with -1
    for (int i = 1; i <= n; ++i) {
        for (int j = 1; j <= n; ++j) {
            grid[i][j] = -1;
        }
    }

    // Base knowledge
    grid[1][1] = 1;
    grid[n][n] = 0;

    // 1. Fill Even cells (r+c is even)
    // We can fill them in topological order from (1, 1).
    // For any cell (i, j) with i+j > 2 and even sum, there exists an ancestor at distance 2.
    for (int i = 1; i <= n; ++i) {
        for (int j = 1; j <= n; ++j) {
            if (grid[i][j] != -1) continue;
            if ((i + j) % 2 == 0) {
                // Find a known parent at distance 2
                int pi = -1, pj = -1;
                // Candidates: (i-2, j), (i-1, j-1), (i, j-2)
                // Prefer ones that are within bounds and determined
                if (i > 2 && grid[i - 2][j] != -1) { pi = i - 2; pj = j; }
                else if (i > 1 && j > 1 && grid[i - 1][j - 1] != -1) { pi = i - 1; pj = j - 1; }
                else if (j > 2 && grid[i][j - 2] != -1) { pi = i; pj = j - 2; }
                
                if (pi != -1) {
                    int res = query(pi, pj, i, j);
                    if (res == 1) grid[i][j] = grid[pi][pj];
                    else grid[i][j] = 1 - grid[pi][pj];
                }
            }
        }
    }

    // 2. Fill Odd cells (r+c is odd)
    // Set a tentative value for (1, 2) and fill relative to it.
    grid[1][2] = 0; // Tentative

    // We need to handle (2, 1) specially because it doesn't have parents at dist 2 from (1, 2).
    // However, both (1, 2) and (2, 1) can reach (2, 3) at distance 2.
    // Determine (2, 3) from (1, 2)
    {
        int r_target = 2, c_target = 3;
        // Since n >= 3, (2, 3) is always valid.
        int res1 = query(1, 2, r_target, c_target);
        if (res1 == 1) grid[r_target][c_target] = grid[1][2];
        else grid[r_target][c_target] = 1 - grid[1][2];
        
        // Now determine (2, 1) using (2, 3). Path (2, 1) -> (2, 3)
        int res2 = query(2, 1, r_target, c_target);
        if (res2 == 1) grid[2][1] = grid[r_target][c_target];
        else grid[2][1] = 1 - grid[r_target][c_target];
    }

    // Fill remaining Odd cells
    for (int i = 1; i <= n; ++i) {
        for (int j = 1; j <= n; ++j) {
            if (grid[i][j] != -1) continue;
            if ((i + j) % 2 != 0) {
                int pi = -1, pj = -1;
                if (i > 2 && grid[i - 2][j] != -1) { pi = i - 2; pj = j; }
                else if (i > 1 && j > 1 && grid[i - 1][j - 1] != -1) { pi = i - 1; pj = j - 1; }
                else if (j > 2 && grid[i][j - 2] != -1) { pi = i; pj = j - 2; }
                
                if (pi != -1) {
                    int res = query(pi, pj, i, j);
                    if (res == 1) grid[i][j] = grid[pi][pj];
                    else grid[i][j] = 1 - grid[pi][pj];
                }
            }
        }
    }

    // 3. Determine if Odd cells need to be flipped
    // Find a pair (u, v) with distance 3 where u is Even (fixed) and v is Odd (tentative)
    // such that we can distinguish the correct parity F.
    bool determined = false;
    int F = 0; // F=1 means flip all odd cells

    for (int r1 = 1; r1 <= n && !determined; ++r1) {
        for (int c1 = 1; c1 <= n && !determined; ++c1) {
            if ((r1 + c1) % 2 != 0) continue; // u must be Even

            // Possible v at distance 3
            int dr[] = {0, 1, 2, 3};
            int dc[] = {3, 2, 1, 0};

            for (int k = 0; k < 4; ++k) {
                int r2 = r1 + dr[k];
                int c2 = c1 + dc[k];
                if (r2 > n || c2 > n) continue;

                // Analyze possible paths u -> a -> b -> v
                // Check consistency for F=0 and F=1
                bool possible0 = false;
                bool possible1 = false;

                // Iterate possible 'a' (neighbors of u)
                if (r1 + 1 <= n) { // a = (r1+1, c1)
                    int ra = r1 + 1, ca = c1;
                    // Neighbors of a leading to v
                    if (ra + 1 <= n) { // b = (ra+1, ca)
                        int rb = ra + 1, cb = ca;
                        // Check if b -> v is valid (dist 1)
                        if ((rb == r2 - 1 && cb == c2) || (rb == r2 && cb == c2 - 1)) {
                            // Path found
                            int val_u = grid[r1][c1];
                            int val_a = grid[ra][ca];
                            int val_b = grid[rb][cb];
                            int val_v = grid[r2][c2];
                            
                            // Check F=0: u==v AND a==b
                            if (val_u == val_v && val_a == val_b) possible0 = true;
                            // Check F=1: u==(v^1) AND (a^1)==b
                            if (val_u == (val_v ^ 1) && (val_a ^ 1) == val_b) possible1 = true;
                        }
                    }
                    if (ca + 1 <= n) { // b = (ra, ca+1)
                        int rb = ra, cb = ca + 1;
                        if ((rb == r2 - 1 && cb == c2) || (rb == r2 && cb == c2 - 1)) {
                            int val_u = grid[r1][c1];
                            int val_a = grid[ra][ca];
                            int val_b = grid[rb][cb];
                            int val_v = grid[r2][c2];
                            if (val_u == val_v && val_a == val_b) possible0 = true;
                            if (val_u == (val_v ^ 1) && (val_a ^ 1) == val_b) possible1 = true;
                        }
                    }
                }
                if (c1 + 1 <= n) { // a = (r1, c1+1)
                    int ra = r1, ca = c1 + 1;
                    if (ra + 1 <= n) {
                        int rb = ra + 1, cb = ca;
                        if ((rb == r2 - 1 && cb == c2) || (rb == r2 && cb == c2 - 1)) {
                            int val_u = grid[r1][c1];
                            int val_a = grid[ra][ca];
                            int val_b = grid[rb][cb];
                            int val_v = grid[r2][c2];
                            if (val_u == val_v && val_a == val_b) possible0 = true;
                            if (val_u == (val_v ^ 1) && (val_a ^ 1) == val_b) possible1 = true;
                        }
                    }
                    if (ca + 1 <= n) {
                        int rb = ra, cb = ca + 1;
                        if ((rb == r2 - 1 && cb == c2) || (rb == r2 && cb == c2 - 1)) {
                            int val_u = grid[r1][c1];
                            int val_a = grid[ra][ca];
                            int val_b = grid[rb][cb];
                            int val_v = grid[r2][c2];
                            if (val_u == val_v && val_a == val_b) possible0 = true;
                            if (val_u == (val_v ^ 1) && (val_a ^ 1) == val_b) possible1 = true;
                        }
                    }
                }

                if (possible0 != possible1) {
                    int res = query(r1, c1, r2, c2);
                    if (res == 1) {
                        F = possible0 ? 0 : 1;
                    } else {
                        F = possible0 ? 1 : 0;
                    }
                    determined = true;
                    break;
                }
            }
        }
    }

    if (F == 1) {
        for (int i = 1; i <= n; ++i) {
            for (int j = 1; j <= n; ++j) {
                if ((i + j) % 2 != 0) {
                    grid[i][j] = 1 - grid[i][j];
                }
            }
        }
    }

    cout << "!" << endl;
    for (int i = 1; i <= n; ++i) {
        for (int j = 1; j <= n; ++j) {
            cout << grid[i][j];
        }
        cout << endl;
    }

    return 0;
}