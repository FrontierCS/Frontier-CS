#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
using namespace std;

int main() {
    const int N = 50, M = 50;
    vector<string> grid(N, string(M, '#'));

    // Carve a spiral corridor that is 3 cells wide
    int top = 1, bottom = N-2, left = 1, right = M-2;
    while (top <= bottom && left <= right) {
        // Top horizontal segment: rows top..top+2, columns left..right
        if (top + 2 <= bottom) {
            for (int i = top; i <= min(top+2, bottom); ++i)
                for (int j = left; j <= right; ++j)
                    grid[i][j] = '.';
        }
        // Right vertical segment: columns right-2..right, rows top+2..bottom-2
        if (right - 2 >= left && top + 2 <= bottom - 2) {
            for (int j = max(left, right-2); j <= right; ++j)
                for (int i = top+2; i <= bottom-2; ++i)
                    grid[i][j] = '.';
        }
        // Bottom horizontal segment: rows bottom-2..bottom, columns left..right
        if (bottom - 2 >= top) {
            for (int i = max(top, bottom-2); i <= bottom; ++i)
                for (int j = left; j <= right; ++j)
                    grid[i][j] = '.';
        }
        // Left vertical segment: columns left..left+2, rows top+2..bottom-2
        if (left + 2 <= right && top + 2 <= bottom - 2) {
            for (int j = left; j <= min(left+2, right); ++j)
                for (int i = top+2; i <= bottom-2; ++i)
                    grid[i][j] = '.';
        }
        // Move inward
        top += 3;
        bottom -= 3;
        left += 3;
        right -= 3;
    }

    // Place the 2x2 box at the start of the spiral (top-left corner)
    int box_r = 1, box_c = 1;
    grid[box_r][box_c] = 'B';
    grid[box_r][box_c+1] = 'B';
    grid[box_r+1][box_c] = 'B';
    grid[box_r+1][box_c+1] = 'B';

    // Find a suitable 2x2 storage location far from the box
    int storage_r = -1, storage_c = -1;
    int max_dist = -1;
    for (int i = 1; i+1 < N; ++i) {
        for (int j = 1; j+1 < M; ++j) {
            if (grid[i][j] == '.' && grid[i][j+1] == '.' &&
                grid[i+1][j] == '.' && grid[i+1][j+1] == '.') {
                // Not overlapping with box
                if (i >= box_r-1 && i <= box_r+1 && j >= box_c-1 && j <= box_c+1)
                    continue;
                int dist = abs(i - box_r) + abs(j - box_c);
                if (dist > max_dist) {
                    max_dist = dist;
                    storage_r = i;
                    storage_c = j;
                }
            }
        }
    }
    // Place storage
    if (storage_r == -1) {
        // Fallback: near center
        storage_r = N/2 - 1;
        storage_c = M/2 - 1;
    }
    grid[storage_r][storage_c] = 'S';
    grid[storage_r][storage_c+1] = 'S';
    grid[storage_r+1][storage_c] = 'S';
    grid[storage_r+1][storage_c+1] = 'S';

    // Place the player adjacent to the box (not on box or storage)
    int player_r = -1, player_c = -1;
    int dr[] = {0, 1, 0, -1};
    int dc[] = {1, 0, -1, 0};
    for (int d = 0; d < 4; ++d) {
        int r = box_r + dr[d];
        int c = box_c + dc[d];
        if (r >= 0 && r < N && c >= 0 && c < M && grid[r][c] == '.') {
            player_r = r;
            player_c = c;
            break;
        }
    }
    // If no adjacent empty cell, search for any empty cell
    if (player_r == -1) {
        for (int i = 0; i < N; ++i)
            for (int j = 0; j < M; ++j)
                if (grid[i][j] == '.') {
                    player_r = i;
                    player_c = j;
                    goto found;
                }
    }
found:
    grid[player_r][player_c] = 'P';

    // Output
    cout << N << " " << M << endl;
    for (int i = 0; i < N; ++i)
        cout << grid[i] << endl;

    return 0;
}