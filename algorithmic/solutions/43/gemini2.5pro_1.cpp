#include <iostream>
#include <vector>
#include <string>

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int N = 50, M = 50;
    std::cout << N << " " << M << std::endl;
    std::vector<std::string> grid(N, std::string(M, '#'));

    // Carve horizontal corridors for the box path
    for (int i = 0; i < 12; ++i) {
        int r = 2 + i * 4;
        for (int c = 2; c < M - 2; ++c) {
            grid[r][c] = '.';
            grid[r+1][c] = '.';
        }
    }

    // Carve vertical turns connecting the corridors
    for (int i = 0; i < 11; ++i) {
        int r1 = 2 + i * 4;
        int r2 = r1 + 4;
        int c = (i % 2 == 0) ? M - 3 : 2;
        for (int r = r1 + 1; r < r2; ++r) {
            grid[r][c] = '.';
            grid[r][c+1] = '.';
        }
    }

    // Carve a long snake-like maze for the player in the center
    // Area for maze: rows [2, 47], columns [6, 43]
    for (int i = 0; i < 23; ++i) { // 23 segments, each 2 rows high
        int r = 2 + i * 2;
        if (i % 2 == 0) { // Rightward segment
            for (int c = 6; c <= 43; ++c) {
                grid[r][c] = '.';
                grid[r+1][c] = '.';
            }
        } else { // Leftward segment
            for (int c = 43; c >= 6; --c) {
                grid[r][c] = '.';
                grid[r+1][c] = '.';
            }
        }
    }
    // Add connections between maze segments
    for (int i = 0; i < 22; ++i) {
        int r = 3 + i * 2;
        if (i % 2 == 0) { // End of a rightward segment, connect downwards at column 43
            grid[r][43] = '.';
            grid[r+1][43] = '.';
        } else { // End of a leftward segment, connect downwards at column 6
            grid[r][6] = '.';
            grid[r+1][6] = '.';
        }
    }

    // Connect the box path to the player maze at turning points
    for (int i = 0; i < 11; ++i) {
        int r_mid = 4 + i * 4;
        if (i % 2 == 0) { // Right side turn
            for(int r_off = -1; r_off <= 1; ++r_off) {
                grid[r_mid + r_off][M - 4] = '.';
            }
        } else { // Left side turn
            for(int r_off = -1; r_off <= 1; ++r_off) {
                grid[r_mid + r_off][5] = '.';
            }
        }
    }

    // Place the Player, Box, and Storage locations
    grid[2][2] = 'B'; grid[2][3] = 'B';
    grid[3][2] = 'B'; grid[3][3] = 'B';

    int last_corridor_r = 2 + 11 * 4;
    grid[last_corridor_r][2] = 'S'; grid[last_corridor_r+1][2] = 'S';
    grid[last_corridor_r][3] = 'S'; grid[last_corridor_r+1][3] = 'S';

    grid[2][1] = 'P';

    // Print the generated grid
    for (int i = 0; i < N; ++i) {
        std::cout << grid[i] << std::endl;
    }

    return 0;
}