#include <iostream>
#include <vector>
#include <algorithm>

using namespace std;

int main() {
    long long x;
    if (!(cin >> x)) return 0;

    if (x == 1) {
        cout << "2\n1 1\n0 1\n";
        return 0;
    }

    // Determine the highest bit set
    int L = 0;
    for (int i = 62; i >= 0; --i) {
        if ((x >> i) & 1) {
            L = i;
            break;
        }
    }

    // Grid size N = 3*L + 2 is sufficient
    // Nodes are at (3*i + 1, 3*i + 1) for i = 0 to L
    // i=0 -> (1,1), i=L -> (3L+1, 3L+1)
    int n = 3 * L + 2;
    vector<vector<int>> grid(n + 1, vector<int>(n + 1, 0));

    // Fill collector column
    for (int r = 1; r <= n; ++r) {
        grid[r][n] = 1;
    }

    for (int i = 0; i <= L; ++i) {
        // Current node (r, c)
        int r = 3 * i + 1;
        int c = 3 * i + 1;
        
        // Node itself
        grid[r][c] = 1;

        // If bit i is set, connect to collector
        if ((x >> i) & 1) {
            for (int k = c + 1; k <= n; ++k) {
                grid[r][k] = 1;
            }
        }

        // Build path to next level i+1
        if (i < L) {
            // Doubling block: generates 2 paths from (r,c) to (r+1, c+1)
            // (r,c) -> (r, c+1) -> (r+1, c+1)
            // (r,c) -> (r+1, c) -> (r+1, c+1)
            grid[r][c + 1] = 1;
            grid[r + 1][c] = 1;
            grid[r + 1][c + 1] = 1;

            // Transport block: move from (r+1, c+1) to next node (r+3, c+3)
            // Path: (r+1, c+1) -> (r+2, c+1) -> (r+3, c+1) -> (r+3, c+2) -> (r+3, c+3)
            // (Using Down, Down, Right, Right)
            // Indices: r+1 is 3i+2. Next node is 3(i+1)+1 = 3i+4. Diff is 2.
            // Wait, my formula was 3i+1 -> 3(i+1)+1 = 3i+4.
            // Node i: 3i+1. Node i+1: 3i+4.
            // Doubling puts us at (3i+2, 3i+2).
            // We need to reach (3i+4, 3i+4).
            // Path:
            // (3i+2, 3i+2) -> (3i+3, 3i+2) (Down)
            // (3i+3, 3i+2) -> (3i+4, 3i+2) (Down)
            // (3i+4, 3i+2) -> (3i+4, 3i+3) (Right)
            // (3i+4, 3i+3) -> (3i+4, 3i+4) (Right)
            
            grid[r + 2][c + 1] = 1; // (3i+3, 3i+2)
            grid[r + 3][c + 1] = 1; // (3i+4, 3i+2)
            grid[r + 3][c + 2] = 1; // (3i+4, 3i+3)
            grid[r + 3][c + 3] = 1; // (3i+4, 3i+4)
        }
    }

    cout << n << "\n";
    for (int i = 1; i <= n; ++i) {
        for (int j = 1; j <= n; ++j) {
            cout << grid[i][j] << (j == n ? "" : " ");
        }
        cout << "\n";
    }

    return 0;
}