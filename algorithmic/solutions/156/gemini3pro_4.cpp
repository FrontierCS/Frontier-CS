#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstring>
#include <tuple>

using namespace std;

// RNG
struct XorShift {
    unsigned int x = 123456789;
    unsigned int y = 362436069;
    unsigned int z = 521288629;
    unsigned int w = 88675123;
    unsigned int next() {
        unsigned int t = x ^ (x << 11);
        x = y; y = z; z = w;
        return w = (w ^ (w >> 19)) ^ (t ^ (t >> 8));
    }
    int next_int(int n) {
        return next() % n;
    }
    double next_double() {
        return next() / 4294967296.0;
    }
} rng;

int T[30][30];
int R[30][30];
int best_R[30][30];

// to[tile_type][entry_dir] -> exit_dir (relative)
// Directions: 0:Left, 1:Up, 2:Right, 3:Down
// entry_dir is the side of the tile we enter from.
// exit_dir is the side we exit to.
const int base_to[8][4] = {
    {1, 0, -1, -1},
    {3, -1, -1, 0},
    {-1, -1, 3, 2},
    {-1, 2, 1, -1},
    {1, 0, 3, 2},
    {3, 2, 1, 0},
    {2, -1, 0, -1},
    {-1, 3, -1, 1},
};

const int di[4] = {0, -1, 0, 1};
const int dj[4] = {-1, 0, 1, 0};

bool visited_port[30][30][4];

long long get_score(bool final_eval) {
    memset(visited_port, 0, sizeof(visited_port));
    
    vector<int> loops;
    loops.reserve(100);
    
    for(int i=0; i<30; ++i) {
        for(int j=0; j<30; ++j) {
            for(int k=0; k<4; ++k) {
                if(visited_port[i][j][k]) continue;
                
                int type = T[i][j];
                int rot = R[i][j];
                // Connection check
                int rel_in = (k + rot) % 4;
                int rel_out = base_to[type][rel_in];
                
                if(rel_out == -1) continue; 
                
                // Trace
                int curr_i = i, curr_j = j, curr_in = k;
                int len = 0;
                bool is_loop = false;
                
                while(true) {
                    visited_port[curr_i][curr_j][curr_in] = true;
                    
                    int t = T[curr_i][curr_j];
                    int r = R[curr_i][curr_j];
                    int r_in = (curr_in + r) % 4;
                    int r_out = base_to[t][r_in];
                    
                    if(r_out == -1) break; // Should not happen given start check
                    
                    int abs_out = (r_out - r + 4) % 4;
                    visited_port[curr_i][curr_j][abs_out] = true;
                    
                    int next_i = curr_i + di[abs_out];
                    int next_j = curr_j + dj[abs_out];
                    
                    if(next_i < 0 || next_i >= 30 || next_j < 0 || next_j >= 30) {
                        break;
                    }
                    
                    int next_in = (abs_out + 2) % 4;
                    
                    // Check next tile connectivity
                    int nt = T[next_i][next_j];
                    int nr = R[next_i][next_j];
                    int n_rin = (next_in + nr) % 4;
                    if(base_to[nt][n_rin] == -1) {
                        break;
                    }
                    
                    if(next_i == i && next_j == j && next_in == k) {
                        is_loop = true;
                        len++;
                        break;
                    }
                    
                    if(visited_port[next_i][next_j][next_in]) {
                         // Merged into a previously visited path/loop
                         break;
                    }
                    
                    curr_i = next_i;
                    curr_j = next_j;
                    curr_in = next_in;
                    len++;
                }
                
                if(is_loop) {
                    loops.push_back(len);
                }
            }
        }
    }
    
    if(loops.empty()) return 0;
    
    // Sort descending
    sort(loops.rbegin(), loops.rend());
    
    if (final_eval) {
        if(loops.size() < 2) return 0;
        return (long long)loops[0] * loops[1];
    } else {
        if(loops.size() == 1) return loops[0];
        // Heuristic: L1*L2 + bonus to separate from 1-loop case
        return (long long)loops[0] * loops[1] + 100000;
    }
}

int main() {
    auto start_time = chrono::high_resolution_clock::now();
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    for(int i=0; i<30; ++i) {
        string row;
        cin >> row;
        for(int j=0; j<30; ++j) {
            T[i][j] = row[j] - '0';
            R[i][j] = rng.next_int(4);
        }
    }
    
    for(int i=0; i<30; ++i) for(int j=0; j<30; ++j) best_R[i][j] = R[i][j];
    
    long long current_score = get_score(false);
    long long best_real_score = get_score(true);
    
    double T_start = 100.0;
    double T_end = 0.0;
    double time_limit = 1.95;
    
    int iters = 0;
    while(true) {
        iters++;
        if((iters & 255) == 0) {
            auto now = chrono::high_resolution_clock::now();
            double elapsed = chrono::duration<double>(now - start_time).count();
            if(elapsed > time_limit) break;
        }
        
        int r = rng.next_int(30);
        int c = rng.next_int(30);
        int old_rot = R[r][c];
        int new_rot = (old_rot + 1 + rng.next_int(3)) % 4;
        
        R[r][c] = new_rot;
        long long new_score = get_score(false);
        
        bool accept = false;
        if(new_score > current_score) {
            accept = true;
        } else {
            auto now = chrono::high_resolution_clock::now();
            double elapsed = chrono::duration<double>(now - start_time).count();
            double temp = T_start + (T_end - T_start) * (elapsed / time_limit);
            if(temp > 0.0001) {
                double prob = exp((double)(new_score - current_score) / temp);
                if(rng.next_double() < prob) accept = true;
            }
        }
        
        if(accept) {
            current_score = new_score;
            if(new_score > 100000) {
                // Potential improvement in real score
                long long real_s = get_score(true);
                if(real_s > best_real_score) {
                    best_real_score = real_s;
                    for(int i=0; i<30; ++i) for(int j=0; j<30; ++j) best_R[i][j] = R[i][j];
                }
            }
        } else {
            R[r][c] = old_rot;
        }
    }
    
    for(int i=0; i<30; ++i) {
        for(int j=0; j<30; ++j) {
            cout << best_R[i][j];
        }
    }
    cout << endl;
    
    return 0;
}