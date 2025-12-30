#include <iostream>
#include <vector>

using namespace std;

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    long long x;
    if (!(cin >> x)) return 0;

    // Find the highest set bit H
    int H = 0;
    for (int i = 62; i >= 0; --i) {
        if ((x >> i) & 1) {
            H = i;
            break;
        }
    }

    // Determine grid size
    // We need indices up to 2*H+2.
    // Bit k uses row 2k+1.
    // The generator for step k->k+1 goes up to 2k+3.
    // The highest needed node is (2H+2, 2H+2) to collect the flow from the highest bit H.
    int n = 2 * H + 2;
    
    // Grid 1-based indexing, size (n+1)x(n+1)
    vector<vector<int>> grid(n + 1, vector<int>(n + 1, 0));

    // Start point
    grid[1][1] = 1;

    // Build the generator along the main diagonal
    // Step i generates 2^{i+1} paths at (2i+3, 2i+3) from 2^i paths at (2i+1, 2i+1)
    for (int i = 0; i < H; ++i) {
        int r = 2 * i + 1;
        // The structure creates 2 paths from (r, r) to (r+1, r+1)
        // And then shifts to (r+2, r+2)
        grid[r][r+1] = 1;
        grid[r+1][r] = 1;
        grid[r+1][r+1] = 1;
        grid[r+2][r+1] = 1;
        grid[r+2][r+2] = 1;
    }

    // Construct paths to transport the counts to (n, n) based on binary representation of x
    for (int k = 0; k <= H; ++k) {
        if ((x >> k) & 1) {
            int r = 2 * k + 1;
            // Create a horizontal path from the node with 2^k paths to column n
            // The node with 2^k paths is effectively tapped at (r, r+1) or just branched from (r,r)
            // We fill row r from r+1 to n
            for (int j = r + 1; j <= n; ++j) {
                grid[r][j] = 1;
            }
            // Create a vertical path down column n to (n, n)
            for (int i = r; i <= n; ++i) {
                grid[i][n] = 1;
            }
        }
    }

    // Output the result
    cout << n << "\n";
    for (int i = 1; i <= n; ++i) {
        for (int j = 1; j <= n; ++j) {
            cout << grid[i][j] << (j == n ? "" : " ");
        }
        cout << "\n";
    }

    return 0;
}