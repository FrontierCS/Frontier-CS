#include <iostream>
#include <vector>
#include <string>

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int N = 49, M = 49;

    std::vector<std::string> grid(N, std::string(M, '.'));

    // Create outer walls.
    for (int i = 0; i < N; ++i) {
        grid[i][0] = '#';
        grid[i][M - 1] = '#';
    }
    for (int j = 0; j < M; ++j) {
        grid[0][j] = '#';
        grid[N - 1][j] = '#';
    }

    // Create horizontal walls to separate box and player corridors.
    // A module consists of a 2-row box corridor, a 1-row wall, and a 1-row player corridor.
    for (int i = 3; i < N - 1; i += 4) {
        for (int j = 1; j < M - 1; ++j) {
            grid[i][j] = '#';
        }
    }

    // Create the snake-like path with vertical walls and openings for turns.
    // The structure repeats every 8 rows (two modules).
    for (int k = 0; k < 6; ++k) {
        int i_base = 8 * k;
        
        // Rightward corridor segment (e.g., rows 1-2, 9-10, etc.)
        // Block the left entrance to force movement from a turn.
        if (i_base + 1 < N - 1) grid[i_base + 1][1] = '#';
        if (i_base + 2 < N - 1) grid[i_base + 2][1] = '#';

        // Leftward corridor segment (e.g., rows 5-6, 13-14, etc.)
        // Block the right entrance.
        if (i_base + 5 < N - 1) grid[i_base + 5][M - 2] = '#';
        if (i_base + 6 < N - 1) grid[i_base + 6][M - 2] = '#';

        // Create openings for turns. A turn needs a 2-wide vertical space.
        
        // Right turn area: connects a rightward corridor to the next leftward one.
        // It pierces the wall between them.
        if (i_base + 3 < N - 1) {
            grid[i_base + 3][M - 3] = '.';
            grid[i_base + 3][M - 2] = '.';
        }

        // Left turn area: connects a leftward corridor to the next rightward one.
        // It pierces the wall between them.
        if (i_base + 7 < N - 1) {
            grid[i_base + 7][1] = '.';
            grid[i_base + 7][2] = '.';
        }
    }

    // Place the Box ('B'), Storage ('S'), and Player ('P').
    
    // Box at the beginning of the first corridor.
    grid[1][2] = grid[1][3] = 'B';
    grid[2][2] = grid[2][3] = 'B';
    
    // Storage at the end of the last corridor.
    // The last segment is k=5 (i_base=40), which has a leftward corridor at rows 45-46.
    // The end of this corridor is at the left side.
    grid[45][2] = grid[45][3] = 'S';
    grid[46][2] = grid[46][3] = 'S';
    
    // Player in the first player corridor, positioned to start the puzzle.
    grid[4][1] = 'P';

    // Output the generated grid.
    std::cout << N << " " << M << std::endl;
    for (int i = 0; i < N; ++i) {
        std::cout << grid[i] << std::endl;
    }

    return 0;
}