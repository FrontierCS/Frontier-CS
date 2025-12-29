#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <cmath>
#include <queue>
#include <iomanip>
#include <cstring>
#include <chrono>

using namespace std;

// Constants
const int H = 20;
const int W = 20;
const int MAX_LEN = 200;
int BEAM_WIDTH = 500; 

// Inputs
int Si, Sj, Ti, Tj;
double P;
int h_wall[20][19]; 
int v_wall[19][20]; 

// Precomputed BFS distance
int min_dist[H][W];

struct State {
    string s;
    double prob[H][W];
    double current_score;
    double heuristic;

    State() : current_score(0), heuristic(0) {
        memset(prob, 0, sizeof(prob));
    }
};

bool can_move(int r, int c, int dir) {
    if (dir == 0) { // U
        if (r == 0) return false;
        if (v_wall[r-1][c]) return false;
        return true;
    }
    if (dir == 1) { // D
        if (r == H - 1) return false;
        if (v_wall[r][c]) return false;
        return true;
    }
    if (dir == 2) { // L
        if (c == 0) return false;
        if (h_wall[r][c-1]) return false;
        return true;
    }
    if (dir == 3) { // R
        if (c == W - 1) return false;
        if (h_wall[r][c]) return false;
        return true;
    }
    return false;
}

void bfs_dist() {
    for(int i=0; i<H; ++i) for(int j=0; j<W; ++j) min_dist[i][j] = 1e9;
    queue<pair<int,int>> q;
    min_dist[Ti][Tj] = 0;
    q.push({Ti, Tj});
    
    while(!q.empty()){
        pair<int,int> u = q.front(); q.pop();
        int r = u.first;
        int c = u.second;

        // Up
        if (r > 0 && !v_wall[r-1][c]) {
            if (min_dist[r-1][c] > min_dist[r][c] + 1) {
                min_dist[r-1][c] = min_dist[r][c] + 1;
                q.push({r-1, c});
            }
        }
        // Down
        if (r < H - 1 && !v_wall[r][c]) {
             if (min_dist[r+1][c] > min_dist[r][c] + 1) {
                min_dist[r+1][c] = min_dist[r][c] + 1;
                q.push({r+1, c});
            }
        }
        // Left
        if (c > 0 && !h_wall[r][c-1]) {
             if (min_dist[r][c-1] > min_dist[r][c] + 1) {
                min_dist[r][c-1] = min_dist[r][c] + 1;
                q.push({r, c-1});
            }
        }
        // Right
        if (c < W - 1 && !h_wall[r][c]) {
             if (min_dist[r][c+1] > min_dist[r][c] + 1) {
                min_dist[r][c+1] = min_dist[r][c] + 1;
                q.push({r, c+1});
            }
        }
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    auto start_time = chrono::steady_clock::now();

    cin >> Si >> Sj >> Ti >> Tj >> P;
    for(int i=0; i<H; ++i) {
        string row; cin >> row;
        for(int j=0; j<W-1; ++j) h_wall[i][j] = row[j] - '0';
    }
    for(int i=0; i<H-1; ++i) {
        string row; cin >> row;
        for(int j=0; j<W; ++j) v_wall[i][j] = row[j] - '0';
    }

    bfs_dist();

    vector<State> beam;
    beam.reserve(BEAM_WIDTH * 4);
    
    State initial;
    initial.prob[Si][Sj] = 1.0;
    initial.current_score = 0;
    
    double h_val = 0;
    if (Si != Ti || Sj != Tj) {
        double dist_term = min_dist[Si][Sj] / (1.0 - P);
        if (401.0 - dist_term > 0)
             h_val = 1.0 * (401.0 - dist_term);
    }
    initial.heuristic = h_val;
    beam.push_back(initial);

    int dr[] = {-1, 1, 0, 0};
    int dc[] = {0, 0, -1, 1};
    char dirs[] = "UDLR";

    for (int step = 0; step < MAX_LEN; ++step) {
        auto now = chrono::steady_clock::now();
        double elapsed = chrono::duration_cast<chrono::milliseconds>(now - start_time).count();
        if (elapsed > 1850) {
            BEAM_WIDTH = 1;
        }

        vector<State> next_beam;
        next_beam.reserve(beam.size() * 4);

        for (const auto& st : beam) {
            for (int d = 0; d < 4; ++d) {
                State next_st; 
                next_st.s = st.s + dirs[d];
                next_st.current_score = st.current_score;
                
                double step_gain = 0;
                double move_prob = 1.0 - P;
                
                bool active = false;
                for (int r = 0; r < H; ++r) {
                    for (int c = 0; c < W; ++c) {
                        if (st.prob[r][c] <= 1e-9) continue;
                        active = true;
                        
                        double mass = st.prob[r][c];
                        
                        next_st.prob[r][c] += mass * P;

                        if (can_move(r, c, d)) {
                            int nr = r + dr[d];
                            int nc = c + dc[d];
                            if (nr == Ti && nc == Tj) {
                                step_gain += mass * move_prob * (401 - (step + 1));
                            } else {
                                next_st.prob[nr][nc] += mass * move_prob;
                            }
                        } else {
                            next_st.prob[r][c] += mass * move_prob;
                        }
                    }
                }
                
                next_st.current_score += step_gain;

                if (!active && step_gain == 0) {
                   next_st.heuristic = next_st.current_score;
                   next_beam.push_back(next_st);
                   continue;
                }

                double future = 0;
                for(int r=0; r<H; ++r) {
                    for(int c=0; c<W; ++c) {
                        if (next_st.prob[r][c] > 1e-9) {
                            double expected_rem = min_dist[r][c] / (1.0 - P);
                            double term = 401.0 - ((step + 1) + expected_rem);
                            if (term > 0) future += next_st.prob[r][c] * term;
                        }
                    }
                }
                next_st.heuristic = next_st.current_score + future;
                next_beam.push_back(next_st);
            }
        }

        if (next_beam.empty()) break; 

        if (next_beam.size() > BEAM_WIDTH) {
            nth_element(next_beam.begin(), next_beam.begin() + BEAM_WIDTH, next_beam.end(), 
                [](const State& a, const State& b){
                    return a.heuristic > b.heuristic;
                });
            next_beam.resize(BEAM_WIDTH);
        }
        beam = move(next_beam);
    }

    double best_val = -1;
    string best_s = "";
    for(const auto& st : beam) {
        if (st.current_score > best_val) {
            best_val = st.current_score;
            best_s = st.s;
        }
    }
    cout << best_s << endl;

    return 0;
}