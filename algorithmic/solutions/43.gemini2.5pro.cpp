#include <iostream>
#include <vector>
#include <string>

void generate_grid() {
    int N = 49, M = 49;
    std::cout << N << " " << M << std::endl;
    std::vector<std::string> grid(N, std::string(M, '#'));

    // Carve a 1-tile wide perimeter path for the player.
    for (int i = 1; i < N - 1; ++i) {
        grid[i][1] = '.';
        grid[i][M - 2] = '.';
    }
    for (int j = 1; j < M - 1; ++j) {
        grid[1][j] = '.';
        grid[N - 2][j] = '.';
    }

    int num_segments = 15;

    // Carve out the snake's horizontal corridors.
    for (int i = 0; i < num_segments; ++i) {
        int r1 = 2 + 3 * i;
        int r2 = 3 + 3 * i;

        if (i % 2 == 0) { // Rightward corridor
            for (int c = 2; c < M - 3; ++c) {
                grid[r1][c] = '.';
                grid[r2][c] = '.';
            }
        } else { // Leftward corridor
            for (int c = 3; c < M - 2; ++c) {
                grid[r1][c] = '.';
                grid[r2][c] = '.';
            }
        }
    }

    // Carve vertical shafts to connect the horizontal corridors.
    for (int i = 0; i < num_segments - 1; ++i) {
        int r_conn_base = 2 + 3 * i;
        if (i % 2 == 0) { // Right turn (connects right end of even segment to right end of odd segment)
            for (int r_offset = 0; r_offset < 5; ++r_offset) {
                grid[r_conn_base + r_offset][M - 3] = '.';
                grid[r_conn_base + r_offset][M - 4] = '.';
            }
        } else { // Left turn (connects left end of odd segment to left end of even segment)
            for (int r_offset = 0; r_offset < 5; ++r_offset) {
                grid[r_conn_base + r_offset][2] = '.';
                grid[r_conn_base + r_offset][3] = '.';
            }
        }
    }
    
    // Place the Player, Box, and Storage.
    grid[2][2] = 'P';

    grid[2][3] = 'B';
    grid[2][4] = 'B';
    grid[3][3] = 'B';
    grid[3][4] = 'B';
    
    int last_seg_idx = num_segments - 1;
    int sr = 2 + 3 * last_seg_idx;
    // The last segment is rightward. Place storage at its end.
    int sc = M - 3 - 2;
    grid[sr][sc] = 'S';
    grid[sr][sc + 1] = 'S';
    grid[sr + 1][sc] = 'S';
    grid[sr + 1][sc + 1] = 'S';

    // Print the generated grid.
    for (int i = 0; i < N; ++i) {
        std::cout << grid[i] << std::endl;
    }
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    generate_grid();
    return 0;
}