#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <random>
#include <chrono>
#include <cstring>

using namespace std;

// Constants
const int N = 30;
// TO[tile_type][entry_side] = exit_direction (movement direction)
// Sides/Directions: 0:Left, 1:Up, 2:Right, 3:Down
int TO[8][4] = {
    {1, 0, -1, -1}, // 0: L-U
    {3, -1, -1, 0}, // 1: L-D
    {-1, -1, 3, 2}, // 2: R-D
    {-1, 2, 1, -1}, // 3: R-U
    {1, 0, 3, 2},   // 4: L-U & R-D
    {3, 2, 1, 0},   // 5: L-D & R-U
    {2, -1, 0, -1}, // 6: L-R
    {-1, 3, -1, 1}  // 7: U-D
};

int DI[4] = {0, -1, 0, 1}; // L, U, R, D
int DJ[4] = {-1, 0, 1, 0};

int base_grid[N][N];
int rot_grid[N][N];     // Our decision variables (0-3)
int current_grid[N][N]; // Computed tile types

int best_rot[N][N];
double best_score = -1.0;

// Visited array
int vis[N][N][4];
int vis_token = 0;

void update_cell(int r, int c) {
    int t = base_grid[r][c];
    int k = rot_grid[r][c];
    if (t < 4) {
        current_grid[r][c] = (t + k) % 4;
    } else if (t < 6) {
        current_grid[r][c] = 4 + (t - 4 + k) % 2;
    } else {
        current_grid[r][c] = 6 + (t - 6 + k) % 2;
    }
}

double evaluate() {
    vis_token++;
    // Using a static vector to avoid reallocation overhead might be slightly faster,
    // but vector allocation is usually fine for these constraints.
    // Given the stack limit, local vector is safer.
    static vector<int> loops;
    loops.clear();
    int fragments = 0;

    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            int t = current_grid[i][j];
            for (int d = 0; d < 4; ++d) {
                // Check if this port is used in the tile and not visited
                if (TO[t][d] == -1) continue;
                if (vis[i][j][d] == vis_token) continue;

                // Start tracing a new component (loop or path segment)
                int r = i;
                int c = j;
                int in_d = d; // Entering (r,c) from side `in_d` of the tile
                
                int len = 0;
                bool is_loop = false;
                
                int start_r = r;
                int start_c = c;
                int start_in_d = in_d;

                while (true) {
                    // Check bounds
                    if (r < 0 || r >= N || c < 0 || c >= N) {
                        break;
                    }
                    
                    int type = current_grid[r][c];
                    // If no connection from input side, path ends (shouldn't happen if logic correct for internal trace)
                    // But effectively handled by TO check
                    if (TO[type][in_d] == -1) break;

                    int out_d = TO[type][in_d]; // Direction to move to next tile

                    // Check visited
                    if (vis[r][c][in_d] == vis_token) {
                        // We hit a visited port.
                        // If it is the start, it's a loop.
                        if (r == start_r && c == start_c && in_d == start_in_d) {
                            is_loop = true;
                        }
                        break;
                    }

                    // Mark internal connection used
                    vis[r][c][in_d] = vis_token;
                    // The other side of the internal track is implicit by type, but we enter from in_d and leave to out_d.
                    // The port on the 'out' side is out_d. We should mark it too to prevent re-entry from that side?
                    // Actually, TO[type][in_d] gives the movement direction.
                    // The port index corresponding to that side is `out_d`.
                    // And TO[type][out_d] would be `in_d`? Not necessarily for Type 0-3?
                    // Let's check: Type 0 (L-U). in L(0) -> out U(1).
                    // TO[0][0] = 1. TO[0][1] = 0. Yes.
                    // So we can mark out_d as well.
                    vis[r][c][out_d] = vis_token;

                    // Move to next tile
                    r += DI[out_d];
                    c += DJ[out_d];
                    // The entry side for the next tile is opposite of movement direction
                    in_d = (out_d + 2) % 4;
                    
                    len++;
                }

                if (is_loop) {
                    loops.push_back(len);
                } else {
                    fragments++;
                }
            }
        }
    }

    sort(loops.rbegin(), loops.rend());
    
    double real_score = 0;
    if (loops.size() >= 2) {
        real_score = (double)loops[0] * loops[1];
    } 
    
    // Heuristic:
    // If real_score > 0, we maximize it. Add small term to break ties (minimize fragments).
    // If real_score == 0, we prioritize L1 (if exists) and minimizing fragments.
    
    double heuristic = real_score;
    if (real_score == 0) {
        if (!loops.empty()) heuristic = loops[0];
    }
    
    // Add bonus for connectivity (fewer fragments means longer paths/loops)
    // Multiplier must be small enough not to override primary score.
    // 0.1 is safe since integer scores are discrete.
    return heuristic + 0.1 / (1.0 + fragments);
}

int main() {
    // Fast I/O
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    // Input
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            cin >> base_grid[i][j];
            rot_grid[i][j] = 0; // Start with 0 rotation
            update_cell(i, j);
        }
    }

    // Time management
    auto start_time = chrono::high_resolution_clock::now();
    double time_limit = 1.95; // seconds

    // Initial Eval
    best_score = evaluate();
    memcpy(best_rot, rot_grid, sizeof(rot_grid));

    // Simulated Annealing
    // State is simple, so we can run many iterations.
    
    mt19937 rng(1337);
    uniform_int_distribution<int> dist_coord(0, N - 1);
    uniform_int_distribution<int> dist_rot(1, 3);
    uniform_real_distribution<double> dist_prob(0.0, 1.0);

    // Initial randomization to escape local optima of input
    // Actually, input is random, so maybe not needed.
    // But SA works better with some heat.
    
    double T0 = 100.0;
    double T1 = 0.0;
    
    int iter = 0;
    while (true) {
        iter++;
        if ((iter & 255) == 0) {
            auto curr_time = chrono::high_resolution_clock::now();
            chrono::duration<double> elapsed = curr_time - start_time;
            if (elapsed.count() > time_limit) break;
        }

        double progress = 0; // Not used for linear check, but can be computed
        // Estimate progress? 
        // Just use time check.
        // For T calculation:
        auto curr_time = chrono::high_resolution_clock::now();
        chrono::duration<double> elapsed = curr_time - start_time;
        double t_ratio = elapsed.count() / time_limit;
        double T = T0 + (T1 - T0) * t_ratio;

        int r = dist_coord(rng);
        int c = dist_coord(rng);
        int drot = dist_rot(rng);
        
        int old_rot = rot_grid[r][c];
        int new_rot = (old_rot + drot) % 4;
        
        rot_grid[r][c] = new_rot;
        update_cell(r, c);
        
        double new_score = evaluate();
        
        double delta = new_score - best_score;
        
        bool accept = false;
        if (delta >= 0) {
            accept = true;
        } else {
            double prob = exp(delta / T);
            if (dist_prob(rng) < prob) {
                accept = true;
            }
        }
        
        if (accept) {
            best_score = new_score;
            // Keep best solution found
            // Since we update best_score even for worse accepted moves in SA logic, 
            // we should track global best separately?
            // "best_score" here tracks CURRENT state score.
            // We need global_best.
        } else {
            // Revert
            rot_grid[r][c] = old_rot;
            update_cell(r, c);
        }
        
        // Track global max
        // To save time, we can assume final state is good, but tracking is safer.
        // Actually, let's add `global_best` logic.
    }
    
    // Since I didn't implement separate global_best tracking inside the loop 
    // (to keep it fast and clean), 
    // and SA converges, the final state should be good.
    // However, SA explores bad states. We must store the absolute best.
    // Let's rewrite the loop slightly to track `global_best`.

    // Reset for restart with proper tracking
    memcpy(rot_grid, best_rot, sizeof(rot_grid));
    for(int i=0; i<N; ++i) for(int j=0; j<N; ++j) update_cell(i,j);
    double current_val = evaluate();
    double global_max = current_val;
    memcpy(best_rot, rot_grid, sizeof(rot_grid));
    
    iter = 0;
    while (true) {
        iter++;
        if ((iter & 1023) == 0) {
            auto curr_time = chrono::high_resolution_clock::now();
            chrono::duration<double> elapsed = curr_time - start_time;
            if (elapsed.count() > time_limit) break;
            
            // Temperature update
            double t_ratio = elapsed.count() / time_limit;
            T0 = 10.0 * (1.0 - t_ratio); // Decay temperature
        }
        
        int r = dist_coord(rng);
        int c = dist_coord(rng);
        int drot = dist_rot(rng); // 1, 2, or 3
        
        int old_rot = rot_grid[r][c];
        int new_rot = (old_rot + drot) % 4;
        
        rot_grid[r][c] = new_rot;
        update_cell(r, c);
        
        double new_val = evaluate();
        
        if (new_val > global_max) {
            global_max = new_val;
            memcpy(best_rot, rot_grid, sizeof(rot_grid));
        }
        
        double delta = new_val - current_val;
        if (delta >= 0 || dist_prob(rng) < exp(delta / (T0 + 1e-9))) {
            current_val = new_val;
        } else {
            rot_grid[r][c] = old_rot;
            update_cell(r, c);
        }
    }

    // Output
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            cout << best_rot[i][j];
        }
    }
    cout << endl;

    return 0;
}