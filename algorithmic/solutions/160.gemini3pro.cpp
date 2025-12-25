/*
    AtCoder Heuristic Contest 015 - Halloween Candy
    Solution using Monte Carlo Simulation with Greedy Rollout
*/
#include <iostream>
#include <vector>
#include <algorithm>
#include <chrono>
#include <random>
#include <cstring>

using namespace std;

// Problem Constants
const int N = 10;
const int NUM_CANDIES = 100;
const double TIME_LIMIT_PER_TURN = 0.018; // Seconds per turn to fit within 2s total

// Global data
int future_flavors[NUM_CANDIES + 1];
char DIR_CHARS[] = {'F', 'B', 'L', 'R'};

// Random Number Generator
mt19937 rng(1337);

// Grid Structure
struct Grid {
    int cells[N][N];
    
    Grid() {
        memset(cells, 0, sizeof(cells));
    }
    
    // Find p-th empty cell and place flavor f
    // p is 1-based index among empty cells, according to row-major order
    void place(int p, int f) {
        int count = 0;
        for (int r = 0; r < N; ++r) {
            for (int c = 0; c < N; ++c) {
                if (cells[r][c] == 0) {
                    count++;
                    if (count == p) {
                        cells[r][c] = f;
                        return;
                    }
                }
            }
        }
    }
    
    // Tilt the box in direction dir
    // 0:F (Up), 1:B (Down), 2:L (Left), 3:R (Right)
    void tilt(int dir) {
        if (dir == 0) { // F
            for (int c = 0; c < N; ++c) {
                int pos = 0;
                for (int r = 0; r < N; ++r) {
                    if (cells[r][c] != 0) {
                        if (r != pos) {
                            cells[pos][c] = cells[r][c];
                            cells[r][c] = 0;
                        }
                        pos++;
                    }
                }
            }
        } else if (dir == 1) { // B
            for (int c = 0; c < N; ++c) {
                int pos = N - 1;
                for (int r = N - 1; r >= 0; --r) {
                    if (cells[r][c] != 0) {
                        if (r != pos) {
                            cells[pos][c] = cells[r][c];
                            cells[r][c] = 0;
                        }
                        pos--;
                    }
                }
            }
        } else if (dir == 2) { // L
            for (int r = 0; r < N; ++r) {
                int pos = 0;
                for (int c = 0; c < N; ++c) {
                    if (cells[r][c] != 0) {
                        if (c != pos) {
                            cells[r][pos] = cells[r][c];
                            cells[r][c] = 0;
                        }
                        pos++;
                    }
                }
            }
        } else if (dir == 3) { // R
            for (int r = 0; r < N; ++r) {
                int pos = N - 1;
                for (int c = N - 1; c >= 0; --c) {
                    if (cells[r][c] != 0) {
                        if (c != pos) {
                            cells[r][pos] = cells[r][c];
                            cells[r][c] = 0;
                        }
                        pos--;
                    }
                }
            }
        }
    }

    // Heuristic score: Number of adjacent pairs of same flavor
    int count_adjacent_pairs() const {
        int score = 0;
        // Horizontal
        for (int r = 0; r < N; ++r) {
            for (int c = 0; c < N - 1; ++c) {
                if (cells[r][c] != 0 && cells[r][c] == cells[r][c+1]) {
                    score++;
                }
            }
        }
        // Vertical
        for (int c = 0; c < N; ++c) {
            for (int r = 0; r < N - 1; ++r) {
                if (cells[r][c] != 0 && cells[r][c] == cells[r+1][c]) {
                    score++;
                }
            }
        }
        return score;
    }

    // True score: Sum of squares of connected component sizes
    int calculate_true_score() const {
        bool visited[N][N];
        memset(visited, 0, sizeof(visited));
        int total_sq_score = 0;
        
        // Directions for BFS
        int dr[] = {1, -1, 0, 0};
        int dc[] = {0, 0, 1, -1};
        
        // Queue for BFS
        pair<int, int> q[105];

        for (int r = 0; r < N; ++r) {
            for (int c = 0; c < N; ++c) {
                if (cells[r][c] != 0 && !visited[r][c]) {
                    int flavor = cells[r][c];
                    int size = 0;
                    
                    int head = 0;
                    int tail = 0;
                    
                    visited[r][c] = true;
                    q[tail++] = {r, c};
                    size++;
                    
                    while(head < tail){
                        pair<int,int> curr = q[head++];
                        for(int k=0; k<4; ++k){
                            int nr = curr.first + dr[k];
                            int nc = curr.second + dc[k];
                            if(nr >= 0 && nr < N && nc >= 0 && nc < N && 
                               !visited[nr][nc] && cells[nr][nc] == flavor) {
                                visited[nr][nc] = true;
                                q[tail++] = {nr, nc};
                                size++;
                            }
                        }
                    }
                    total_sq_score += size * size;
                }
            }
        }
        return total_sq_score;
    }
};

double get_time_sec() {
    using namespace std::chrono;
    return duration_cast<duration<double>>(high_resolution_clock::now().time_since_epoch()).count();
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    // Read flavors
    for (int i = 1; i <= NUM_CANDIES; ++i) {
        cin >> future_flavors[i];
    }

    Grid current_grid;
    
    for (int t = 1; t <= NUM_CANDIES; ++t) {
        int p_t;
        cin >> p_t;
        
        current_grid.place(p_t, future_flavors[t]);
        
        // At t=100, the box is full. Tilting does nothing meaningful for positioning,
        // but we must output a valid move. Any move results in same state.
        if (t == NUM_CANDIES) {
            cout << "F" << endl;
            continue;
        }

        // Start Monte Carlo
        double start_time = get_time_sec();
        
        vector<long long> total_score(4, 0);
        vector<int> counts(4, 0);
        
        int sim_count = 0;
        
        // Run simulations until time limit
        while (true) {
            sim_count++;
            // Check time every 64 iterations to reduce overhead
            if ((sim_count & 63) == 0) {
                if (get_time_sec() - start_time > TIME_LIMIT_PER_TURN) break;
            }

            int first_move = sim_count % 4; // Round robin start to ensure coverage
            
            Grid sim_grid = current_grid;
            sim_grid.tilt(first_move);
            
            // Rollout simulation
            for (int k = t + 1; k <= NUM_CANDIES; ++k) {
                int empty_cnt = 101 - k;
                if (empty_cnt <= 0) break;

                // Random placement of opponent candy
                int p = (int)(rng() % empty_cnt) + 1;
                sim_grid.place(p, future_flavors[k]);
                
                if (k == NUM_CANDIES) break;

                // Greedy step for player: choose move that maximizes adjacent pairs
                int best_m = -1;
                int best_val = -1;
                
                // Shuffle move check order to handle ties randomly
                int moves[4] = {0, 1, 2, 3};
                for(int i=0; i<4; ++i) {
                    int j = i + (rng() % (4 - i));
                    swap(moves[i], moves[j]);
                }

                for (int i = 0; i < 4; ++i) {
                    int m = moves[i];
                    Grid temp = sim_grid;
                    temp.tilt(m);
                    int val = temp.count_adjacent_pairs();
                    if (val > best_val) {
                        best_val = val;
                        best_m = m;
                    }
                }
                sim_grid.tilt(best_m);
            }
            
            // Evaluate final state with actual scoring function
            total_score[first_move] += sim_grid.calculate_true_score();
            counts[first_move]++;
        }
        
        // Pick best move based on average score
        int best_move = 0;
        double best_avg = -1.0;
        
        for (int m = 0; m < 4; ++m) {
            if (counts[m] > 0) {
                double avg = (double)total_score[m] / counts[m];
                if (avg > best_avg) {
                    best_avg = avg;
                    best_move = m;
                }
            }
        }
        
        cout << DIR_CHARS[best_move] << endl;
        current_grid.tilt(best_move);
    }
    
    return 0;
}