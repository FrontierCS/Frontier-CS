#include <iostream>
#include <vector>
#include <chrono>
#include <algorithm>
#include <cstring>

using namespace std;

// Global variables for board and inputs
int flavors[100];
int board[100]; // 0: empty, 1-3: flavor. Index: row*10 + col

// Directions: F(Up), B(Down), L(Left), R(Right)
const char DIR_CHARS[] = "FBLR";

// Fast RNG (Xorshift)
struct Xorshift {
    uint64_t state;
    Xorshift(uint64_t seed = 88172645463325252ull) : state(seed) {}
    uint64_t next() {
        uint64_t x = state;
        x ^= x << 13;
        x ^= x >> 7;
        x ^= x << 17;
        return state = x;
    }
} rng;

// Function to tilt the board
// d: 0=F, 1=B, 2=L, 3=R
void tilt(int* b, int d) {
    if (d == 0) { // F: Up
        for (int c = 0; c < 10; ++c) {
            int p = 0;
            for (int r = 0; r < 10; ++r) {
                int idx = r * 10 + c;
                if (b[idx] != 0) {
                    if (r != p) {
                        b[p * 10 + c] = b[idx];
                        b[idx] = 0;
                    }
                    p++;
                }
            }
        }
    } else if (d == 1) { // B: Down
        for (int c = 0; c < 10; ++c) {
            int p = 9;
            for (int r = 9; r >= 0; --r) {
                int idx = r * 10 + c;
                if (b[idx] != 0) {
                    if (r != p) {
                        b[p * 10 + c] = b[idx];
                        b[idx] = 0;
                    }
                    p--;
                }
            }
        }
    } else if (d == 2) { // L: Left
        for (int r = 0; r < 10; ++r) {
            int p = 0;
            for (int c = 0; c < 10; ++c) {
                int idx = r * 10 + c;
                if (b[idx] != 0) {
                    if (c != p) {
                        b[r * 10 + p] = b[idx];
                        b[idx] = 0;
                    }
                    p++;
                }
            }
        }
    } else if (d == 3) { // R: Right
        for (int r = 0; r < 10; ++r) {
            int p = 9;
            for (int c = 9; c >= 0; --c) {
                int idx = r * 10 + c;
                if (b[idx] != 0) {
                    if (c != p) {
                        b[r * 10 + p] = b[idx];
                        b[idx] = 0;
                    }
                    p--;
                }
            }
        }
    }
}

// Calculate adjacency score: count pairs of adjacent same-flavor candies
int calc_adjacency(const int* b) {
    int score = 0;
    // Horizontal
    for (int r = 0; r < 10; ++r) {
        for (int c = 0; c < 9; ++c) {
            int u = b[r*10+c];
            int v = b[r*10+c+1];
            if (u != 0 && u == v) score++;
        }
    }
    // Vertical
    for (int c = 0; c < 10; ++c) {
        for (int r = 0; r < 9; ++r) {
            int u = b[r*10+c];
            int v = b[(r+1)*10+c];
            if (u != 0 && u == v) score++;
        }
    }
    return score;
}

// Calculate final score: sum of squared sizes of connected components
bool visited[100];
int q[100];
int calc_score(const int* b) {
    memset(visited, 0, sizeof(visited));
    int total_sq = 0;
    for (int i = 0; i < 100; ++i) {
        if (b[i] != 0 && !visited[i]) {
            int color = b[i];
            int head = 0, tail = 0;
            q[tail++] = i;
            visited[i] = true;
            int count = 0;
            while(head < tail) {
                int u = q[head++];
                count++;
                int r = u / 10;
                int c = u % 10;
                // Neighbors: Up, Down, Left, Right
                int nbrs[4];
                int k=0;
                if(r > 0) nbrs[k++] = u - 10;
                if(r < 9) nbrs[k++] = u + 10;
                if(c > 0) nbrs[k++] = u - 1;
                if(c < 9) nbrs[k++] = u + 1;
                
                for(int j=0; j<k; ++j) {
                    int v = nbrs[j];
                    if(b[v] == color && !visited[v]) {
                        visited[v] = true;
                        q[tail++] = v;
                    }
                }
            }
            total_sq += count * count;
        }
    }
    return total_sq;
}

int main() {
    // Optimize I/O
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    // Read flavors
    for(int i=0; i<100; ++i) cin >> flavors[i];
    
    auto start_time = chrono::steady_clock::now();
    
    // Main loop
    for(int t=1; t<=100; ++t) {
        int p; 
        if(!(cin >> p)) break;
        
        // Find p-th empty cell and place candy
        int empty_cnt = 0;
        int placement_idx = -1;
        for(int i=0; i<100; ++i) {
            if(board[i] == 0) {
                empty_cnt++;
                if(empty_cnt == p) {
                    placement_idx = i;
                    break;
                }
            }
        }
        board[placement_idx] = flavors[t-1];
        
        // If last turn, just output F (or any valid) and exit loop/finish
        if (t == 100) {
            cout << "F" << endl;
            continue;
        }

        // Time Management
        auto curr_time = chrono::steady_clock::now();
        auto elapsed_ms = chrono::duration_cast<chrono::milliseconds>(curr_time - start_time).count();
        double remaining_ms = 1950.0 - elapsed_ms; // 2000ms limit, buffer 50ms
        double time_limit = remaining_ms / (100 - t + 1);
        if (time_limit < 3.0) time_limit = 3.0; // Ensure at least minimal processing
        
        // Monte Carlo Simulation
        double sum_scores[4] = {0};
        int counts[4] = {0};
        
        static int sim_board[100];
        static int temp_board[100];
        
        int iter = 0;
        while(true) {
            iter++;
            // Check time every 32 iterations to minimize overhead
            if ((iter & 31) == 0) {
                auto now = chrono::steady_clock::now();
                if (chrono::duration_cast<chrono::milliseconds>(now - curr_time).count() > time_limit) {
                    break;
                }
            }
            
            int first_move = (iter - 1) % 4;
            
            // Initial state for simulation
            memcpy(sim_board, board, sizeof(board));
            tilt(sim_board, first_move);
            
            int current_sim_t = t; 
            // current_sim_t represents number of candies on board after placement and tilt
            // We simulate from t+1 to 100
            
            while (current_sim_t < 100) {
                int f = flavors[current_sim_t]; // Flavor for next candy
                
                // Pick random empty spot
                int e = 100 - current_sim_t;
                if (e <= 0) break;
                
                int r = rng.next() % e;
                int pos = -1;
                int cnt = 0;
                // Linear scan to find empty spot
                for(int k=0; k<100; ++k) {
                    if(sim_board[k] == 0) {
                        if(cnt == r) {
                            pos = k;
                            break;
                        }
                        cnt++;
                    }
                }
                sim_board[pos] = f;
                
                // Greedy move selection
                int best_m = 0;
                int max_adj = -1;
                
                // Random start direction for tie-breaking
                int start_d = rng.next() & 3;
                
                for(int dd=0; dd<4; ++dd) {
                    int d = (start_d + dd) & 3;
                    memcpy(temp_board, sim_board, sizeof(sim_board));
                    tilt(temp_board, d);
                    int adj = calc_adjacency(temp_board);
                    if (adj > max_adj) {
                        max_adj = adj;
                        best_m = d;
                    }
                }
                
                tilt(sim_board, best_m);
                current_sim_t++;
            }
            
            sum_scores[first_move] += calc_score(sim_board);
            counts[first_move]++;
        }
        
        int best_move = 0;
        double best_avg = -1.0;
        for(int i=0; i<4; ++i) {
            if (counts[i] > 0) {
                double avg = sum_scores[i] / counts[i];
                if (avg > best_avg) {
                    best_avg = avg;
                    best_move = i;
                }
            }
        }
        
        cout << DIR_CHARS[best_move] << endl;
        tilt(board, best_move);
    }
    
    return 0;
}