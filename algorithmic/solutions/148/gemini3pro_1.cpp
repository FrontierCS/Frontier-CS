#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <ctime>
#include <cstdlib>

using namespace std;

// Constants
const int N = 50;
const int DR[] = {-1, 1, 0, 0};
const int DC[] = {0, 0, -1, 1};
const char DCHAR[] = {'U', 'D', 'L', 'R'};

// Input Data
int SI, SJ;
int T[N][N];
int P[N][N];
pair<int, int> Partners[N][N]; 
int NumTiles = 0;

// RNG
struct Xorshift {
    unsigned int x = 123456789;
    unsigned int y = 362436069;
    unsigned int z = 521288629;
    unsigned int w = 88675123;
    unsigned int next() {
        unsigned int t = x ^ (x << 11);
        x = y; y = z; z = w;
        return w = (w ^ (w >> 19)) ^ (t ^ (t >> 8));
    }
    int nextInt(int n) {
        return next() % n;
    }
    double nextDouble() {
        return (double)next() / 0xFFFFFFFF;
    }
} rng;

// Global State Management
int visited_token[2505];
int current_token = 0;

struct Step {
    int r, c;
    int tile_id;
    char dir;
    int points_gained;
};

vector<Step> current_path_stack;
vector<Step> best_path_stack;
int current_r, current_c;
int current_score;
int max_score = -1;

void reset_visited() {
    current_token++;
}

bool is_visited(int tile_id) {
    return visited_token[tile_id] == current_token;
}

void mark_visited(int tile_id) {
    visited_token[tile_id] = current_token;
}

void unmark_visited(int tile_id) {
    visited_token[tile_id] = current_token - 1; 
}

void read_input() {
    if (!(cin >> SI >> SJ)) return;
    int max_t = 0;
    for (int i = 0; i < N; i++) {
        for (int j = 0; j < N; j++) {
            cin >> T[i][j];
            max_t = max(max_t, T[i][j]);
            Partners[i][j] = {-1, -1};
        }
    }
    NumTiles = max_t + 1;
    for (int i = 0; i < N; i++) {
        for (int j = 0; j < N; j++) {
            cin >> P[i][j];
        }
    }
    
    // Identify partners for size-2 tiles
    vector<pair<int, int>> tile_cells[2505];
    for (int i = 0; i < N; i++) {
        for (int j = 0; j < N; j++) {
            tile_cells[T[i][j]].push_back({i, j});
        }
    }
    for (int t = 0; t < NumTiles; t++) {
        if (tile_cells[t].size() == 2) {
            pair<int, int> u = tile_cells[t][0];
            pair<int, int> v = tile_cells[t][1];
            Partners[u.first][u.second] = v;
            Partners[v.first][v.second] = u;
        }
    }
}

double get_time() {
    return (double)clock() / CLOCKS_PER_SEC;
}

void solve() {
    max_score = 0;
    best_path_stack.clear();
    
    // Time limit: 1.95s to be safe
    double TL = 1.95;
    current_path_stack.reserve(3000);
    best_path_stack.reserve(3000);

    while (get_time() < TL) {
        // Start a new run
        reset_visited();
        current_path_stack.clear();
        current_r = SI;
        current_c = SJ;
        mark_visited(T[SI][SJ]);
        current_score = P[SI][SJ];
        
        // Check initial score (rare case where we can't move at all)
        if (current_score > max_score) {
            max_score = current_score;
            best_path_stack = current_path_stack;
        }

        // Randomize heuristics for this run
        double partner_penalty = 0.5 + rng.nextDouble(); // Range [0.5, 1.5]
        double open_space_bonus = 5.0 + rng.nextDouble() * 15.0; // Range [5.0, 20.0]
        
        int steps_without_improvement = 0;
        
        while (true) {
            // Check time periodically
            if ((current_path_stack.size() & 63) == 0) {
                 if (get_time() > TL) break;
            }

            struct Candidate {
                int r, c, dir_idx;
                double weight;
            };
            vector<Candidate> moves; 
            moves.reserve(4);
            
            // Find valid moves
            for (int k = 0; k < 4; k++) {
                int nr = current_r + DR[k];
                int nc = current_c + DC[k];
                
                if (nr >= 0 && nr < N && nc >= 0 && nc < N) {
                    int tid = T[nr][nc];
                    // Can only step on a tile if it hasn't been used yet
                    if (!is_visited(tid)) {
                        int p_curr = P[nr][nc];
                        int p_partner = 0;
                        pair<int, int> prt = Partners[nr][nc];
                        if (prt.first != -1) {
                            p_partner = P[prt.first][prt.second];
                        }
                        
                        // Heuristic calculation
                        double val = (double)p_curr - partner_penalty * p_partner;
                        // Add base offset to keep positive and random noise
                        double w = val + 150.0 + rng.nextDouble() * 20.0; 
                        
                        // Lookahead: Prefer moves that have more valid neighbors (open space)
                        int free_deg = 0;
                        for(int d2=0; d2<4; ++d2) {
                            int nnr = nr + DR[d2];
                            int nnc = nc + DC[d2];
                            if(nnr>=0 && nnr<N && nnc>=0 && nnc<N) {
                                if (!is_visited(T[nnr][nnc])) {
                                    free_deg++;
                                }
                            }
                        }
                        w += free_deg * open_space_bonus;

                        if (w < 1.0) w = 1.0;
                        moves.push_back({nr, nc, k, w});
                    }
                }
            }
            
            if (moves.empty()) {
                // No valid moves -> Stuck
                
                // Backtracking logic to escape dead end
                if (current_path_stack.empty()) break; // Run completely finished
                
                // Restart run if we haven't improved for too long
                if (steps_without_improvement > 1500) break;
                steps_without_improvement++;
                
                // Determine how many steps to backtrack
                // Usually a small amount, occasionally a large amount
                int back_steps = 1 + rng.nextInt(min((int)current_path_stack.size(), 15));
                if (rng.nextInt(20) == 0) {
                     back_steps = 1 + rng.nextInt(current_path_stack.size());
                }

                for (int b = 0; b < back_steps; b++) {
                    if (current_path_stack.empty()) break;
                    Step last = current_path_stack.back();
                    current_path_stack.pop_back();
                    unmark_visited(last.tile_id);
                    current_score -= last.points_gained;
                }
                
                // Update current position
                if (current_path_stack.empty()) {
                    current_r = SI;
                    current_c = SJ;
                } else {
                    current_r = current_path_stack.back().r;
                    current_c = current_path_stack.back().c;
                }
                
                continue;
            }
            
            // Weighted Random Selection
            double total_w = 0;
            for (auto& m : moves) total_w += m.weight;
            
            double rval = rng.nextDouble() * total_w;
            int selected_idx = -1;
            double cur_sum = 0;
            for (int i = 0; i < moves.size(); i++) {
                cur_sum += moves[i].weight;
                if (cur_sum >= rval) {
                    selected_idx = i;
                    break;
                }
            }
            if (selected_idx == -1) selected_idx = moves.size() - 1;
            
            Candidate choice = moves[selected_idx];
            
            // Execute Move
            mark_visited(T[choice.r][choice.c]);
            int gain = P[choice.r][choice.c];
            current_score += gain;
            current_r = choice.r;
            current_c = choice.c;
            
            current_path_stack.push_back({current_r, current_c, T[choice.r][choice.c], DCHAR[choice.dir_idx], gain});
            
            // Update Best Solution
            if (current_score > max_score) {
                max_score = current_score;
                best_path_stack = current_path_stack;
                steps_without_improvement = 0;
            }
        }
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    read_input();
    solve();
    
    // Construct output string from best path
    string ans = "";
    ans.reserve(best_path_stack.size());
    for (const auto& step : best_path_stack) {
        ans += step.dir;
    }
    cout << ans << endl;
    
    return 0;
}