#include <iostream>
#include <vector>
#include <string>

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int N = 49, M = 50;

    std::cout << N << " " << M << std::endl;
    std::vector<std::string> grid(N, std::string(M, '#'));

    // Create horizontal corridors for box and player, separated by walls
    for (int k = 0; k < 12; ++k) {
        int r_box_1 = 4 * k;
        int r_box_2 = 4 * k + 1;
        int r_wall = 4 * k + 2;
        int r_player = 4 * k + 3;

        // Carve out the corridors
        for (int j = 2; j < M - 2; ++j) {
            grid[r_box_1][j] = '.';
            grid[r_box_2][j] = '.';
            grid[r_player][j] = '.';
        }

        // Create a single opening in the wall for each lane
        if (k % 2 == 0) { // Even lane (L->R), opening on the right
            grid[r_wall][M - 3] = '.';
        } else { // Odd lane (R->L), opening on the left
            grid[r_wall][2] = '.';
        }
    }

    // Create wide vertical corridors for turns
    for (int i = 0; i < N; ++i) {
        grid[i][0] = '.'; grid[i][1] = '.';
        grid[i][M - 2] = '.'; grid[i][M - 1] = '.';
    }

    // Add walls to block the ends of box corridors, forcing turns
    for (int k = 0; k < 12; ++k) {
        int r_box_1 = 4 * k;
        int r_box_2 = 4 * k + 1;
        if (k % 2 == 0) { // L->R lane ends on the right, so block the left
            grid[r_box_1][1] = '#'; grid[r_box_2][1] = '#';
        } else { // R->L lane ends on the left, so block the right
            grid[r_box_1][M - 2] = '#'; grid[r_box_2][M - 2] = '#';
        }
    }
    
    // Block ends of player corridors to guide them into vertical passages
    for (int r_player = 3; r_player < N; r_player += 4) {
        grid[r_player][1] = '#';
        grid[r_player][M - 2] = '#';
    }

    // Place Storage, Box, and Player
    // Storage 'S' at the end of the first lane (L->R)
    grid[0][M - 4] = 'S'; grid[0][M - 3] = 'S';
    grid[1][M - 4] = 'S'; grid[1][M - 3] = 'S';

    // Box 'B' at the start of the last lane (R->L)
    grid[44][M - 4] = 'B'; grid[44][M - 3] = 'B';
    grid[45][M - 4] = 'B'; grid[45][M - 3] = 'B';
    
    // Player 'P' in the last player corridor, near the box
    grid[47][M - 3] = 'P';

    for (int i = 0; i < N; ++i) {
        std::cout << grid[i] << std::endl;
    }

    return 0;
}