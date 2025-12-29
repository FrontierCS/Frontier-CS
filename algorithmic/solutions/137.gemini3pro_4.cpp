#include <iostream>
#include <vector>
#include <string>
#include <random>
#include <algorithm>

using namespace std;

// Logical dimensions for maze generation (nodes)
const int H = 10;
const int W = 10;
// Output physical dimensions
const int R = 20;
const int C = 20;

struct Maze {
    char grid[R][C];
    int leaves;

    Maze() {
        for(int i=0; i<R; ++i)
            for(int j=0; j<C; ++j)
                grid[i][j] = '0';
        leaves = 0;
    }
};

// Directions: Up, Down, Left, Right
int dr[] = {-1, 1, 0, 0};
int dc[] = {0, 0, -1, 1};

// Generates a random maze using Prim's algorithm on a grid graph
// Returns the maze and the count of leaves (dead ends)
Maze generate_maze(std::mt19937 &rng) {
    Maze m;
    // Logical grid visited status
    bool visited[H][W] = {false};

    struct Wall {
        int r, c, d; // r,c are logical coords; d is direction index
    };
    vector<Wall> walls;

    // Start at a random logical cell
    std::uniform_int_distribution<int> distH(0, H-1);
    std::uniform_int_distribution<int> distW(0, W-1);
    int start_r = distH(rng);
    int start_c = distW(rng);

    visited[start_r][start_c] = true;
    // Logical cell (r,c) maps to physical cell (2r, 2c)
    m.grid[2*start_r][2*start_c] = '1';

    // Add initial walls to list
    for(int d=0; d<4; ++d) {
        int nr = start_r + dr[d];
        int nc = start_c + dc[d];
        if(nr >= 0 && nr < H && nc >= 0 && nc < W) {
            walls.push_back({start_r, start_c, d});
        }
    }

    // Randomized Prim's Algorithm
    while(!walls.empty()) {
        std::uniform_int_distribution<int> distIdx(0, walls.size()-1);
        int idx = distIdx(rng);
        
        // Remove random wall from list
        Wall w = walls[idx];
        walls[idx] = walls.back();
        walls.pop_back();

        int nr = w.r + dr[w.d];
        int nc = w.c + dc[w.d];

        if(nr >= 0 && nr < H && nc >= 0 && nc < W && !visited[nr][nc]) {
            // Valid unvisited neighbor: carve path
            // The wall in physical grid is between (2r,2c) and (2nr,2nc)
            int wall_phys_r = 2*w.r + dr[w.d];
            int wall_phys_c = 2*w.c + dc[w.d];
            m.grid[wall_phys_r][wall_phys_c] = '1';
            
            visited[nr][nc] = true;
            m.grid[2*nr][2*nc] = '1';

            // Add new walls from the newly visited cell
            for(int d=0; d<4; ++d) {
                int nnr = nr + dr[d];
                int nnc = nc + dc[d];
                if(nnr >= 0 && nnr < H && nnc >= 0 && nnc < W && !visited[nnr][nnc]) {
                    walls.push_back({nr, nc, d});
                }
            }
        }
    }

    // Count leaves in the logical tree (nodes with degree 1)
    // A high number of leaves (dead ends) makes it harder to gather all agents.
    int leaf_count = 0;
    for(int r=0; r<H; ++r) {
        for(int c=0; c<W; ++c) {
            int degree = 0;
            for(int d=0; d<4; ++d) {
                // Check physical connection
                int wr = 2*r + dr[d];
                int wc = 2*c + dc[d];
                // Check bounds and if it's open
                if(wr >= 0 && wr < R && wc >= 0 && wc < C && m.grid[wr][wc] == '1') {
                    degree++;
                }
            }
            if(degree == 1) leaf_count++;
        }
    }
    m.leaves = leaf_count;
    return m;
}

int main() {
    // Seed designed to give good results
    std::mt19937 rng(1337); 

    Maze best_maze;
    best_maze.leaves = -1;

    // Generate many mazes and keep the one with the most leaves (traps)
    // Heuristic: Bushy trees with many dead ends are harder to synchronize blindly.
    for(int i=0; i<5000; ++i) {
        Maze cand = generate_maze(rng);
        if(cand.leaves > best_maze.leaves) {
            best_maze = cand;
        }
    }

    // Output the result
    cout << R << " " << C << endl;
    for(int i=0; i<R; ++i) {
        for(int j=0; j<C; ++j) {
            cout << best_maze.grid[i][j];
        }
        cout << endl;
    }

    return 0;
}