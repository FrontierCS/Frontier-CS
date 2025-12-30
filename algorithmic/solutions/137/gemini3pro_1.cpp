#include <iostream>
#include <vector>
#include <string>

using namespace std;

int main() {
    // Parameters for the map
    int n = 20;
    int m = 20;
    
    // Output dimensions
    cout << n << " " << m << endl;

    // Initialize grid with '0' (walls)
    vector<string> grid(n, string(m, '0'));

    // Construct a "snake" pattern to maximize the path diameter.
    // Corridors are placed on even rows (0, 2, ..., 18).
    // They are connected by single cells in odd rows (1, 3, ..., 17).
    
    // Fill corridors
    for (int r = 0; r <= 18; r += 2) {
        for (int c = 0; c < m; ++c) {
            grid[r][c] = '1';
        }
    }

    // Add connectors
    // Pattern: Right-end connection, then Left-end connection, repeating.
    for (int r = 0; r < 18; r += 2) {
        if ((r / 2) % 2 == 0) {
            // Row r goes Left->Right, connect at column 19 (Right)
            grid[r + 1][19] = '1';
        } else {
            // Row r goes Right->Left, connect at column 0 (Left)
            grid[r + 1][0] = '1';
        }
    }

    // To utilize the remaining space in row 19 and increase the number of states,
    // we add "teeth" (dead ends) attached to row 18.
    // Row 18 is a full corridor. We attach cells at (19, c).
    // To maintain the tree property (no cycles), we cannot place horizontally adjacent cells in row 19.
    // We place them at even indices: 0, 2, ..., 18.
    for (int c = 0; c < m; c += 2) {
        grid[19][c] = '1';
    }

    // Print the grid
    for (int i = 0; i < n; ++i) {
        cout << grid[i] << endl;
    }

    return 0;
}