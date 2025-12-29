/*
    AtCoder Heuristic Contest 015
    Problem: Candy Box
    Solution: Monte Carlo Tree Search with Greedy Rollout
*/

#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <random>
#include <chrono>
#include <cstring>

using namespace std;

const int N = 10;
const int T_MAX = 100;
const char DIR_CHARS[] = {'F', 'B', 'L', 'R'};
const int DR[] = {-1, 1, 0, 0};
const int DC[] = {0, 0, -1, 1};

int flavors[T_MAX];

struct Board {
    int8_t grid[N][N];

    Board() {
        memset(grid, 0, sizeof(grid));
    }

    void place(int p, int f) {
        int count = 0;
        for (int i = 0; i < N; ++i) {
            for (int j = 0; j < N; ++j) {
                if (grid[i][j] == 0) {
                    count++;
                    if (count == p) {
                        grid[i][j] = f;
                        return;
                    }
                }
            }
        }
    }

    bool tilt(int d) {
        bool changed = false;
        if (d == 0) { // F (Up)
            for (int j = 0; j < N; ++j) {
                int pos = 0;
                for (int i = 0; i < N; ++i) {
                    if (grid[i][j] != 0) {
                        if (i != pos) {
                            grid[pos][j] = grid[i][j];
                            grid[i][j] = 0;
                            changed = true;
                        }
                        pos++;
                    }
                }
            }
        } else if (d == 1) { // B (Down)
            for (int j = 0; j < N; ++j) {
                int pos = N - 1;
                for (int i = N - 1; i >= 0; --i) {
                    if (grid[i][j] != 0) {
                        if (i != pos) {
                            grid[pos][j] = grid[i][j];
                            grid[i][j] = 0;
                            changed = true;
                        }
                        pos--;
                    }
                }
            }
        } else if (d == 2) { // L
            for (int i = 0; i < N; ++i) {
                int pos = 0;
                for (int j = 0; j < N; ++j) {
                    if (grid[i][j] != 0) {
                        if (j != pos) {
                            grid[i][pos] = grid[i][j];
                            grid[i][j] = 0;
                            changed = true;
                        }
                        pos++;
                    }
                }
            }
        } else if (d == 3) { // R
            for (int i = 0; i < N; ++i) {
                int pos = N - 1;
                for (int j = N - 1; j >= 0; --j) {
                    if (grid[i][j] != 0) {
                        if (j != pos) {
                            grid[i][pos] = grid[i][j];
                            grid[i][j] = 0;
                            changed = true;
                        }
                        pos--;
                    }
                }
            }
        }
        return changed;
    }

    // Full score evaluation
    long long evaluate_full() const {
        bool visited[N][N];
        memset(visited, 0, sizeof(visited));
        long long score = 0;
        
        // BFS queue
        pair<int, int> q[N*N]; 

        for (int i = 0; i < N; ++i) {
            for (int j = 0; j < N; ++j) {
                if (grid[i][j] != 0 && !visited[i][j]) {
                    int f = grid[i][j];
                    int size = 0;
                    int head = 0, tail = 0;
                    
                    visited[i][j] = true;
                    q[tail++] = {i, j};
                    size++;
                    
                    while(head < tail){
                        pair<int,int> curr = q[head++];
                        int r = curr.first;
                        int c = curr.second;
                        
                        for(int k=0; k<4; ++k){
                            int nr = r + DR[k];
                            int nc = c + DC[k];
                            if(nr >= 0 && nr < N && nc >= 0 && nc < N && !visited[nr][nc] && grid[nr][nc] == f){
                                visited[nr][nc] = true;
                                q[tail++] = {nr, nc};
                                size++;
                            }
                        }
                    }
                    score += (long long)size * size;
                }
            }
        }
        return score;
    }
    
    // Fast adjacency evaluation
    int evaluate_adj() const {
        int adj = 0;
        for (int i = 0; i < N; ++i) {
            for (int j = 0; j < N - 1; ++j) {
                if (grid[i][j] != 0 && grid[i][j] == grid[i][j+1]) adj++;
            }
        }
        for (int j = 0; j < N; ++j) {
            for (int i = 0; i < N - 1; ++i) {
                if (grid[i][j] != 0 && grid[i][j] == grid[i+1][j]) adj++;
            }
        }
        return adj;
    }
};

mt19937 rng(12345);

double get_time() {
    using namespace std::chrono;
    return duration_cast<duration<double>>(high_resolution_clock::now().time_since_epoch()).count();
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    for (int i = 0; i < T_MAX; ++i) {
        cin >> flavors[i];
    }

    Board current_board;
    
    // Total time allowance: 1.9s (leave 100ms for safety)
    double start_time_global = get_time();
    double time_budget = 1.90; 

    for (int t = 0; t < T_MAX; ++t) {
        int p;
        cin >> p;
        current_board.place(p, flavors[t]);
        
        if (t == T_MAX - 1) {
            cout << "F" << endl;
            continue;
        }

        // Determine time for this turn
        double elapsed = get_time() - start_time_global;
        double remaining_time = time_budget - elapsed;
        double time_limit = remaining_time / (T_MAX - t);
        
        double turn_start = get_time();
        
        long long sum_scores[4] = {0};
        int counts[4] = {0};
        
        // MCTS Loop
        int sims = 0;
        while (true) {
            if ((sims & 31) == 0) { // check time every 32 sims
                if (get_time() - turn_start > time_limit) break;
            }
            
            int first_move = sims % 4;
            sims++;
            
            Board sim_board = current_board;
            sim_board.tilt(first_move);
            
            // Rollout
            for (int k = t + 1; k < T_MAX; ++k) {
                int current_empty = 100 - k;
                if (current_empty == 0) break;
                
                // Random place
                int rnd_p = std::uniform_int_distribution<int>(1, current_empty)(rng);
                sim_board.place(rnd_p, flavors[k]);
                
                // Select move greedy
                int best_m = -1;
                int best_adj = -1;
                bool best_ch = false;
                
                // Random offset for move order
                int offset = rng() & 3; 
                
                for (int i = 0; i < 4; ++i) {
                    int m = (i + offset) & 3;
                    Board temp = sim_board;
                    bool ch = temp.tilt(m);
                    
                    int adj = temp.evaluate_adj();
                    
                    if (best_m == -1) {
                        best_m = m;
                        best_adj = adj;
                        best_ch = ch;
                    } else {
                        // Priority: Changed > Not Changed
                        if (ch && !best_ch) {
                            best_m = m;
                            best_adj = adj;
                            best_ch = true;
                        } else if (ch == best_ch) {
                            if (adj > best_adj) {
                                best_m = m;
                                best_adj = adj;
                            }
                        }
                    }
                }
                sim_board.tilt(best_m);
            }
            
            long long final_score = sim_board.evaluate_full();
            sum_scores[first_move] += final_score;
            counts[first_move]++;
        }
        
        int best_move = 0;
        double max_avg = -1e18;
        
        for(int m=0; m<4; ++m){
            double avg = 0;
            if(counts[m] > 0) avg = (double)sum_scores[m] / counts[m];
            
            // Penalize no-op for the immediate move
            Board tmp = current_board;
            bool changed = tmp.tilt(m);
            if (!changed) avg -= 1e12; // massive penalty
            
            if(avg > max_avg){
                max_avg = avg;
                best_move = m;
            }
        }
        
        cout << DIR_CHARS[best_move] << endl;
        current_board.tilt(best_move);
    }

    return 0;
}