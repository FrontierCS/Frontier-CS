#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <random>

using namespace std;

// Grid dimensions
const int N = 20;
const int M = 20;

// Logical dimensions for maze generation (since we use 2x2 blocks implicitly with walls)
const int H = 10;
const int W = 10;

// Global map and visited array
vector<string> grid_map(N, string(M, '0'));
vector<vector<bool>> visited(H, vector<bool>(W, false));

// Random number generator with fixed seed for reproducibility
mt19937 rng(1337);

// Depth-First Search to generate a maze (Spanning Tree)
void dfs(int r, int c) {
    visited[r][c] = true;
    // Mark the logical cell position in the actual grid
    // Logical cell (r, c) corresponds to grid cell (2*r, 2*c)
    grid_map[2 * r][2 * c] = '1';

    // Possible directions: Up, Down, Left, Right
    vector<pair<int, int>> dirs = {{-1, 0}, {1, 0}, {0, -1}, {0, 1}};
    // Shuffle directions to create a random maze
    shuffle(dirs.begin(), dirs.end(), rng);

    for (auto d : dirs) {
        int nr = r + d.first;
        int nc = c + d.second;

        // Check bounds and if visited
        if (nr >= 0 && nr < H && nc >= 0 && nc < W && !visited[nr][nc]) {
            // Remove the wall between the current cell and the neighbor
            // The wall is located at the intermediate coordinate
            grid_map[2 * r + d.first][2 * c + d.second] = '1';
            
            // Recurse
            dfs(nr, nc);
        }
    }
}

int main() {
    // Start DFS from the top-left corner (0, 0) of the logical grid
    dfs(0, 0);

    // Print the dimensions
    cout << N << " " << M << endl;

    // Print the grid
    for (int i = 0; i < N; i++) {
        cout << grid_map[i] << endl;
    }

    return 0;
}