#include <iostream>
#include <vector>
#include <string>

using namespace std;

int main() {
    // We construct a "Snake" pattern on the 20x20 grid.
    // This creates a long induced path (Hamiltonian-like path on the tree of empty cells).
    // The length of this path is approximately 210 cells.
    // The random moves (U, D, L, R) will cause the set of kangaroos to behave like a 1D random walk
    // along this path. Moves perpendicular to the current corridor (e.g., U/D in horizontal rows) 
    // are blocked by walls, effectively reducing the number of "active" steps by half.
    // With 50,000 total steps, we have ~25,000 effective steps.
    // The expected range of a random walk with 25,000 steps is around 250.
    // Since our path length (210) is somewhat less than the expected range (250), there is a significant
    // probability (based on the distribution of the range) that the random walk will fail to cover
    // the entire path (and thus fail to synchronize all agents to a single cell) in many test cases.
    // This maximizes the number of failed synchronizations.

    int n = 20;
    int m = 20;
    
    // Output dimensions
    cout << n << " " << m << endl;

    // Initialize grid with walls ('0')
    vector<string> grid(n, string(m, '0'));

    // Construct the snake pattern
    for (int r = 0; r < n; ++r) {
        if (r % 2 == 0) {
            // Even rows (0, 2, ..., 18) are full horizontal corridors
            for (int c = 0; c < m; ++c) {
                grid[r][c] = '1';
            }
        } else {
            // Odd rows (1, 3, ..., 19) contain a single empty cell to connect the even rows.
            // We alternate the position of this connector to create a winding path.
            // Row 1 connects Row 0 and Row 2 at the Right end.
            // Row 3 connects Row 2 and Row 4 at the Left end.
            // Pattern repeats.
            if (r % 4 == 1) {
                // Connect at the right end (column 19)
                grid[r][m - 1] = '1';
            } else {
                // Connect at the left end (column 0)
                grid[r][0] = '1';
            }
        }
    }

    // Print the map
    for (int i = 0; i < n; ++i) {
        cout << grid[i] << endl;
    }

    return 0;
}