#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <chrono>

using namespace std;

const int N = 30;
const int LIMIT_TIME_MS = 1950;
const int di[] = {0, -1, 0, 1}; // 0:L, 1:U, 2:R, 3:D
const int dj[] = {-1, 0, 1, 0};

// Base connectivity: to[type][in_dir] = out_dir
// in_dir is the direction of the neighbor relative to current cell
// -1 means no connection
int base_to[8][4] = {
    {1, 0, -1, -1}, // 0: L-U
    {3, -1, -1, 0}, // 1: L-D
    {-1, -1, 3, 2}, // 2: R-D
    {-1, 2, 1, -1}, // 3: U-R
    {1, 0, 3, 2},   // 4: L-U, R-D
    {3, 2, 1, 0},   // 5: L-D, U-R
    {2, -1, 0, -1}, // 6: L-R
    {-1, 3, -1, 1}  // 7: U-D
};

// Precomputed rotated connectivity
// trans_to[type][rot][in_dir]
int trans_to[8][4][4];

void precompute() {
    for (int t = 0; t < 8; ++t) {
        for (int r = 0; r < 4; ++r) {
            for (int d = 0; d < 4; ++d) {
                // d is direction of neighbor relative to current cell.
                // d_local is the direction on the un-rotated tile.
                // Rotating a tile CCW means indices shift: new = (old - 1) % 4.
                // So old = (new + 1) % 4. Since r is number of 90 deg CCW rotations:
                int d_local = (d + r) % 4;
                int out_local = base_to[t][d_local];
                if (out_local == -1) {
                    trans_to[t][r][d] = -1;
                } else {
                    // out_local is direction on un-rotated tile.
                    // We need to map it back to rotated frame.
                    // new = (old - r + 4) % 4
                    trans_to[t][r][d] = (out_local - r + 4) % 4;
                }
            }
        }
    }
}

struct State {
    int rot[N][N];
};

int board_types[N][N];
State current_sol;
State best_sol;
long long best_score_val = -1;

int vis[N][N][4];
int vis_token = 0;

// Evaluation function
long long evaluate(const State& state, long long& l1_out, long long& l2_out) {
    vis_token++;
    if (vis_token > 1000000) {
        for(int i=0; i<N; ++i)
            for(int j=0; j<N; ++j)
                for(int k=0; k<4; ++k) vis[i][j][k] = 0;
        vis_token = 1;
    }

    vector<int> loops;
    int total_connected_len = 0;

    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            for (int d = 0; d < 4; ++d) {
                if (vis[i][j][d] == vis_token) continue;
                
                int t = board_types[i][j];
                int r = state.rot[i][j];
                if (trans_to[t][r][d] == -1) continue;

                int curr_i = i, curr_j = j, curr_d = d;
                int len = 0;
                bool is_cycle = false;
                
                int si = curr_i, sj = curr_j, sd = curr_d;
                
                // Trace path/cycle
                while (true) {
                    vis[curr_i][curr_j][curr_d] = vis_token;
                    
                    int t_curr = board_types[curr_i][curr_j];
                    int r_curr = state.rot[curr_i][curr_j];
                    int out_d = trans_to[t_curr][r_curr][curr_d];
                    
                    if (out_d == -1) break; 
                    
                    int next_i = curr_i + di[out_d];
                    int next_j = curr_j + dj[out_d];
                    
                    if (next_i < 0 || next_i >= N || next_j < 0 || next_j >= N) break;
                    
                    int next_in_d = (out_d + 2) % 4; // Enter direction for next tile
                    
                    int t_next = board_types[next_i][next_j];
                    int r_next = state.rot[next_i][next_j];
                    if (trans_to[t_next][r_next][next_in_d] == -1) break; // Not connected
                    
                    len++;
                    curr_i = next_i;
                    curr_j = next_j;
                    curr_d = next_in_d;
                    
                    if (curr_i == si && curr_j == sj && curr_d == sd) {
                        is_cycle = true;
                        break;
                    }
                    
                    if (vis[curr_i][curr_j][curr_d] == vis_token) break; // Merged into visited
                }

                if (is_cycle) {
                    loops.push_back(len);
                } else {
                    total_connected_len += len;
                }
            }
        }
    }
    
    sort(loops.rbegin(), loops.rend());
    long long l1 = (loops.size() > 0) ? loops[0] : 0;
    long long l2 = (loops.size() > 1) ? loops[1] : 0;
    
    l1_out = l1;
    l2_out = l2;
    
    // Heuristic Score Calculation
    long long score = 0;
    if (l2 > 0) {
        score += l1 * l2 * 10000;
        score += (l1 + l2) * 100;
    } else if (l1 > 0) {
        score += l1 * 100;
    }
    score += total_connected_len;
    return score;
}

unsigned long long rng_state = 123456789;
unsigned long long xorshift() {
    rng_state ^= rng_state << 13;
    rng_state ^= rng_state >> 7;
    rng_state ^= rng_state << 17;
    return rng_state;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    precompute();
    
    for (int i = 0; i < N; ++i) {
        string s;
        cin >> s;
        for (int j = 0; j < N; ++j) {
            board_types[i][j] = s[j] - '0';
        }
    }
    
    // Initialization
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            current_sol.rot[i][j] = xorshift() % 4;
        }
    }
    
    long long l1, l2;
    long long current_score = evaluate(current_sol, l1, l2);
    best_sol = current_sol;
    best_score_val = l1 * l2;
    long long internal_best = current_score;

    auto start_time = chrono::high_resolution_clock::now();
    int iter = 0;
    
    while (true) {
        iter++;
        if ((iter & 511) == 0) {
            auto curr_time = chrono::high_resolution_clock::now();
            double elapsed = chrono::duration<double, milli>(curr_time - start_time).count();
            if (elapsed > LIMIT_TIME_MS) break;
        }
        
        int r = xorshift() % N;
        int c = xorshift() % N;
        int old_rot = current_sol.rot[r][c];
        int type = board_types[r][c];
        int new_rot;
        
        // Optimize neighborhood based on tile symmetry
        // Types 4-5 and 6-7 have 180 degree symmetry
        if (type >= 4) {
            new_rot = (old_rot + 1) % 4; 
        } else {
            new_rot = (old_rot + (xorshift() % 3) + 1) % 4;
        }
        
        current_sol.rot[r][c] = new_rot;
        
        long long next_l1, next_l2;
        long long next_score = evaluate(current_sol, next_l1, next_l2);
        
        if (next_score >= internal_best) {
            internal_best = next_score;
            if (next_l1 * next_l2 > best_score_val) {
                best_score_val = next_l1 * next_l2;
                best_sol = current_sol;
            }
        } else {
            // Revert (Hill Climbing)
            current_sol.rot[r][c] = old_rot;
        }
    }
    
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            cout << best_sol.rot[i][j];
        }
    }
    cout << endl;
    
    return 0;
}