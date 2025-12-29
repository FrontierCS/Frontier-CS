#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <chrono>

using namespace std;

// Global variables for board state
int initial_board[30][30];
int board[30][30];
int rotations[30][30];

// Connectivity table [type][entry_dir] -> exit_dir
// Directions: 0:Left, 1:Up, 2:Right, 3:Down
// -1 means no connection
const int to_connect[8][4] = {
    {1, 0, -1, -1}, // 0: Left-Up
    {3, -1, -1, 0}, // 1: Left-Down
    {-1, -1, 3, 2}, // 2: Right-Down
    {-1, 2, 1, -1}, // 3: Up-Right
    {1, 0, 3, 2},   // 4: Left-Up & Right-Down
    {3, 2, 1, 0},   // 5: Left-Down & Up-Right
    {2, -1, 0, -1}, // 6: Left-Right (Horizontal)
    {-1, 3, -1, 1}  // 7: Up-Down (Vertical)
};

// Movement deltas for directions 0, 1, 2, 3
const int di[] = {0, -1, 0, 1};
const int dj[] = {-1, 0, 1, 0};
// Inverse direction (entering next tile from the output direction of current tile)
// e.g. moving Up (1) enters the next tile from Down (3)
const int inv_d[] = {2, 3, 0, 1};

// Helper to get rotated tile type
// Tiles 0-3 cycle mod 4. Tiles 4-5 cycle mod 2. Tiles 6-7 cycle mod 2.
inline int get_rotated_type(int t, int r) {
    if (t <= 3) return (t + r) % 4;
    if (t <= 5) return 4 + ((t - 4 + r) % 2);
    return 6 + ((t - 6 + r) % 2);
}

// Visited array and marker for evaluation to avoid memset
int visited[30][30][4];
int vis_mark = 0;

// Buffer for loop lengths
int loop_lens[1000];

struct Result {
    int l1, l2;
    double score;
};

// Evaluation function
Result evaluate() {
    vis_mark++;
    int loop_count = 0;
    
    for (int i = 0; i < 30; ++i) {
        for (int j = 0; j < 30; ++j) {
            // Check all 4 ports of the tile
            for (int d = 0; d < 4; ++d) {
                if (visited[i][j][d] == vis_mark) continue;
                
                int t = board[i][j];
                int exit_d = to_connect[t][d];
                if (exit_d == -1) continue; // Port not connected internally

                // Trace path
                int curr_i = i, curr_j = j, curr_d = d;
                int len = 0;
                bool closed = false;
                
                while (true) {
                    // Mark entry port
                    visited[curr_i][curr_j][curr_d] = vis_mark;
                    
                    int out_d = to_connect[board[curr_i][curr_j]][curr_d];
                    // Mark exit port
                    visited[curr_i][curr_j][out_d] = vis_mark;
                    
                    int next_i = curr_i + di[out_d];
                    int next_j = curr_j + dj[out_d];
                    
                    // Boundary check
                    if (next_i < 0 || next_i >= 30 || next_j < 0 || next_j >= 30) {
                        break; // Hit wall
                    }
                    
                    int next_entry = inv_d[out_d];
                    if (to_connect[board[next_i][next_j]][next_entry] == -1) {
                        break; // Dead end (neighbor not connected back)
                    }
                    
                    curr_i = next_i;
                    curr_j = next_j;
                    curr_d = next_entry;
                    len++;
                    
                    // Check if returned to start
                    if (curr_i == i && curr_j == j && curr_d == d) {
                        closed = true;
                        break;
                    }
                }
                
                if (closed) {
                    loop_lens[loop_count++] = len;
                }
            }
        }
    }
    
    int l1 = 0, l2 = 0;
    if (loop_count > 0) {
        // Find top 2 lengths manually
        for(int k = 0; k < loop_count; ++k) {
            if (loop_lens[k] > l1) {
                l2 = l1;
                l1 = loop_lens[k];
            } else if (loop_lens[k] > l2) {
                l2 = loop_lens[k];
            }
        }
    }
    
    // Heuristic score: heavily favor having 2 loops via product, but keep l1 term to guide optimization when l2=0
    double sc = (double)l1 * l2 + 0.1 * l1;
    return {l1, l2, sc};
}

// Xorshift RNG for speed
struct Xorshift {
    unsigned int x = 123456789;
    unsigned int y = 362436069;
    unsigned int z = 521288629;
    unsigned int w = 88675123;
    inline unsigned int next() {
        unsigned int t = x ^ (x << 11);
        x = y; y = z; z = w;
        return w = (w ^ (w >> 19)) ^ (t ^ (t >> 8));
    }
    inline int next_int(int n) {
        return next() % n;
    }
} rng;

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    // Read input
    for (int i = 0; i < 30; ++i) {
        string row;
        cin >> row;
        for (int j = 0; j < 30; ++j) {
            initial_board[i][j] = row[j] - '0';
        }
    }
    
    // Initial random state
    for(int i = 0; i < 30; ++i) {
        for(int j = 0; j < 30; ++j) {
            rotations[i][j] = rng.next_int(4);
            board[i][j] = get_rotated_type(initial_board[i][j], rotations[i][j]);
        }
    }

    Result current_res = evaluate();
    Result best_res = current_res;
    int best_rotations[30][30];
    // Copy initial best
    for(int i = 0; i < 30; ++i) 
        for(int j = 0; j < 30; ++j) 
            best_rotations[i][j] = rotations[i][j];

    auto start_time = chrono::steady_clock::now();
    double time_limit = 1.95; // Time limit
    long long iter = 0;
    
    // Hill Climbing with plateau traversal
    while (true) {
        iter++;
        if ((iter & 1023) == 0) {
            auto curr_time = chrono::steady_clock::now();
            double elapsed = chrono::duration<double>(curr_time - start_time).count();
            if (elapsed > time_limit) break;
        }
        
        // Pick random tile
        int r = rng.next_int(30);
        int c = rng.next_int(30);
        int old_rot = rotations[r][c];
        int old_type = board[r][c];
        
        // Pick new rotation (guaranteed to be different)
        int d_rot = rng.next_int(3) + 1; 
        int new_rot = (old_rot + d_rot) % 4;
        
        rotations[r][c] = new_rot;
        board[r][c] = get_rotated_type(initial_board[r][c], new_rot);
        
        Result new_res = evaluate();
        
        // Accept if score improves or stays same (to move on plateaus)
        if (new_res.score >= current_res.score) {
            current_res = new_res;
            
            // Update best solution found so far based on strict problem criteria
            long long current_prod = (long long)current_res.l1 * current_res.l2;
            long long best_prod = (long long)best_res.l1 * best_res.l2;
            
            if (current_prod > best_prod) {
                best_res = current_res;
                for(int ii = 0; ii < 30; ++ii) 
                    for(int jj = 0; jj < 30; ++jj) 
                        best_rotations[ii][jj] = rotations[ii][jj];
            } 
            // Tie-breaking with L1 length can be beneficial
            else if (current_prod == best_prod && current_res.l1 > best_res.l1) {
                best_res = current_res;
                for(int ii = 0; ii < 30; ++ii) 
                    for(int jj = 0; jj < 30; ++jj) 
                        best_rotations[ii][jj] = rotations[ii][jj];
            }
        } else {
            // Revert change
            rotations[r][c] = old_rot;
            board[r][c] = old_type;
        }
    }
    
    // Output result
    for (int i = 0; i < 30; ++i) {
        for (int j = 0; j < 30; ++j) {
            cout << best_rotations[i][j];
        }
    }
    cout << endl;

    return 0;
}