#include <iostream>

using namespace std;

// Using a global array to ensure zero-initialization and sufficient stack space
int grid[305][305];

int main() {
    // Optimize standard I/O operations for speed
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    long long x;
    if (!(cin >> x)) return 0;

    // Base case: if x is 1, a single cell grid is sufficient
    if (x == 1) {
        cout << 1 << "\n";
        cout << 1 << "\n";
        return 0;
    }

    // Determine the position of the most significant bit of x
    int L = 0;
    for (int i = 62; i >= 0; --i) {
        if ((x >> i) & 1) {
            L = i;
            break;
        }
    }

    // Initial configuration for the most significant bit (which is 1)
    // We start with a 2x2 area that provides exactly 1 path to (2,2)
    grid[1][1] = 1;
    grid[1][2] = 1;
    grid[2][2] = 1;

    int n = 2; // Current size of the grid being used (tip is at n,n)

    // Iterate through the bits of x from MSB-1 down to 0
    // At each step, we double the number of paths and optionally add 1
    for (int i = L - 1; i >= 0; --i) {
        int r = n;
        int c = n;
        
        // Construct a gadget to double the number of paths
        // Moving from (r, c) to (r+1, c+1) via two routes:
        // (r, c) -> (r, c+1) -> (r+1, c+1)
        // (r, c) -> (r+1, c) -> (r+1, c+1)
        grid[r][c + 1] = 1;
        grid[r + 1][c] = 1;
        grid[r + 1][c + 1] = 1;
        
        // If the current bit is 1, we need to add exactly 1 extra path.
        // We use row 1 as a "supply line" carrying 1 path from (1,1).
        // We drop a vertical line from the supply line to the merge point (r, c+1).
        if ((x >> i) & 1) {
            // Extend the supply line on row 1 to column c+1
            for (int k = 1; k <= c + 1; ++k) {
                grid[1][k] = 1;
            }
            // Create a vertical path in column c+1 down to row r
            // This merges into (r, c+1), adding 1 to the path count there
            for (int k = 1; k <= r; ++k) {
                grid[k][c + 1] = 1;
            }
        }
        
        // Increase grid size for the next iteration
        n++;
    }

    // Output the calculated grid size and content
    cout << n << "\n";
    for (int i = 1; i <= n; ++i) {
        for (int j = 1; j <= n; ++j) {
            cout << grid[i][j] << (j == n ? "" : " ");
        }
        cout << "\n";
    }

    return 0;
}