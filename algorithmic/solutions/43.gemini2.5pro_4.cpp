#include <iostream>
#include <vector>
#include <string>

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    int N = 49, M = 49;

    std::vector<std::string> grid(N, std::string(M, '#'));

    // Carve out concentric 3-cell-wide paths
    for (int k = 0; ; ++k) {
        int r1 = 4 * k + 1, c1 = 4 * k + 1;
        int r2 = N - 2 - 4 * k, c2 = M - 2 - 4 * k;
        if (r1 > r2 || c1 > c2) break;
        for (int i = r1; i <= r2; ++i) {
            for (int j = c1; j <= c2; ++j) {
                grid[i][j] = '.';
            }
        }
    }

    // Create breaches in the walls to form a single spiral path
    // The pattern of breaches forces the box to traverse each layer of the spiral.
    // Breach between path 1 and 2 (wall at row 44)
    grid[44][5] = '.'; grid[44][6] = '.';
    // Breach between path 2 and 3 (wall at row 8)
    grid[8][5] = '.'; grid[8][6] = '.';
    // Breach between path 3 and 4 (wall at row 36)
    grid[36][9] = '.'; grid[36][10] = '.';
    // Breach between path 4 and 5 (wall at row 16)
    grid[16][9] = '.'; grid[16][10] = '.';
    // Breach between path 5 and 6 (central room) (wall at row 28)
    grid[28][13] = '.'; grid[28][14] = '.';

    // Place the 2x2 box at the start of the spiral
    grid[1][1] = 'B'; grid[1][2] = 'B';
    grid[2][1] = 'B'; grid[2][2] = 'B';

    // Place the player next to the box
    grid[1][3] = 'P';

    // Place the 2x2 storage at the end of the spiral, in the central room
    int center_r = N / 2;
    int center_c = M / 2;
    grid[center_r - 2][center_c - 1] = 'S'; grid[center_r - 2][center_c] = 'S';
    grid[center_r - 1][center_c - 1] = 'S'; grid[center_r - 1][center_c] = 'S';
    
    // Output the grid
    std::cout << N << " " << M << std::endl;
    for (int i = 0; i < N; ++i) {
        std::cout << grid[i] << std::endl;
    }

    return 0;
}