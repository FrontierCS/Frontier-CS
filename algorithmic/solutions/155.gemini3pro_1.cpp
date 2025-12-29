#include <iostream>
#include <vector>
#include <string>
#include <queue>
#include <algorithm>
#include <iomanip>
#include <cmath>
#include <array>

using namespace std;

// Constants
const int N = 20;
const double EPS = 1e-12;

// Inputs
int Si, Sj, Ti, Tj;
double P_forget;
int H[N][N-1]; // H[i][j] wall between (i,j) and (i,j+1)
int V[N-1][N]; // V[i][j] wall between (i,j) and (i+1,j)

// Precomputed and auxiliary
int Dist[N][N];
bool CanMove[N][N][4];

// Directions: U, D, L, R
const int DR[] = {-1, 1, 0, 0};
const int DC[] = {0, 0, -1, 1};
const char DCHAR[] = {'U', 'D', 'L', 'R'};

struct State {
    array<double, N*N> prob;
    double expected_score;
    string path;
    double heuristic_val;
};

// Check if blocked based on raw input
bool is_blocked_raw(int r, int c, int d) {
    if (d == 0) return (r == 0) || V[r-1][c];       // Up
    if (d == 1) return (r == N-1) || V[r][c];       // Down
    if (d == 2) return (c == 0) || H[r][c-1];       // Left
    if (d == 3) return (c == N-1) || H[r][c];       // Right
    return false;
}

void precompute_can_move() {
    for(int r=0; r<N; ++r) {
        for(int c=0; c<N; ++c) {
            for(int d=0; d<4; ++d) {
                CanMove[r][c][d] = !is_blocked_raw(r, c, d);
            }
        }
    }
}

void compute_distances() {
    for(int i=0; i<N; ++i) 
        for(int j=0; j<N; ++j) 
            Dist[i][j] = 10000;
    
    Dist[Ti][Tj] = 0;
    queue<pair<int,int>> q;
    q.push({Ti, Tj});
    
    while(!q.empty()){
        auto [r, c] = q.front();
        q.pop();
        
        for(int d=0; d<4; ++d) {
            // Check reverse moves: could we have come from neighbor to (r,c) via move d?
            // Neighbor pos:
            int nr = r - DR[d];
            int nc = c - DC[d];
            
            if(nr >= 0 && nr < N && nc >= 0 && nc < N) {
                // If we can move from (nr, nc) in direction d to (r, c)
                if(CanMove[nr][nc][d]) {
                     if(Dist[nr][nc] > Dist[r][c] + 1) {
                        Dist[nr][nc] = Dist[r][c] + 1;
                        q.push({nr, nc});
                     }
                }
            }
        }
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if(!(cin >> Si >> Sj >> Ti >> Tj >> P_forget)) return 0;
    
    for(int i=0; i<N; ++i) {
        string row; cin >> row;
        for(int j=0; j<N-1; ++j) H[i][j] = row[j] - '0';
    }
    for(int i=0; i<N-1; ++i) {
        string row; cin >> row;
        for(int j=0; j<N; ++j) V[i][j] = row[j] - '0';
    }

    precompute_can_move();
    compute_distances();

    int BEAM_WIDTH = 1500;
    
    vector<State> beams;
    beams.reserve(BEAM_WIDTH * 4);
    
    State initial;
    initial.prob.fill(0.0);
    initial.prob[Si*N + Sj] = 1.0;
    initial.expected_score = 0.0;
    initial.path = "";
    
    double move_prob = 1.0 - P_forget;
    double stay_prob = P_forget;

    // Initial heuristic
    double term = 0;
    if(Si != Ti || Sj != Tj) {
        term = 401.0 - (double)Dist[Si][Sj] / move_prob;
    } else {
        term = 401.0; 
    }
    initial.heuristic_val = term;
    
    beams.push_back(initial);

    for (int t = 1; t <= 200; ++t) {
        vector<State> next_beams;
        // Reserve memory approx
        next_beams.reserve(min((int)beams.size() * 4, BEAM_WIDTH * 4));
        
        for (const auto& s : beams) {
            for (int d = 0; d < 4; ++d) {
                State ns;
                ns.prob.fill(0.0);
                ns.path = s.path + DCHAR[d];
                ns.expected_score = s.expected_score;
                double current_potential = 0;

                for (int i = 0; i < N*N; ++i) {
                    double p = s.prob[i];
                    if (p < EPS) continue;

                    int r = i / N;
                    int c = i % N;

                    // 1. Stay (Forget)
                    // Staying at (r, c) means we are still at (r, c)
                    int idx_stay = i;
                    double added_stay = p * stay_prob;
                    ns.prob[idx_stay] += added_stay;
                    
                    // Add to potential
                    // Est score = 401 - (t + expected_future_turns)
                    current_potential += added_stay * (401.0 - t - (double)Dist[r][c] / move_prob);

                    // 2. Move (Success)
                    int nr = r, nc = c;
                    if (CanMove[r][c][d]) {
                        nr = r + DR[d];
                        nc = c + DC[d];
                    }
                    
                    if (nr == Ti && nc == Tj) {
                        // Reached target
                        ns.expected_score += p * move_prob * (401.0 - t);
                    } else {
                        int idx_move = nr*N + nc;
                        double added_move = p * move_prob;
                        ns.prob[idx_move] += added_move;
                        current_potential += added_move * (401.0 - t - (double)Dist[nr][nc] / move_prob);
                    }
                }
                
                ns.heuristic_val = ns.expected_score + current_potential;
                next_beams.push_back(ns);
            }
        }

        if (next_beams.empty()) break; 

        // Keep top K
        if (next_beams.size() > BEAM_WIDTH) {
            nth_element(next_beams.begin(), next_beams.begin() + BEAM_WIDTH, next_beams.end(), 
                [](const State& a, const State& b){
                    return a.heuristic_val > b.heuristic_val;
                });
            next_beams.resize(BEAM_WIDTH);
        }
        
        beams = move(next_beams);
    }

    // Find best in final beams
    auto it = max_element(beams.begin(), beams.end(), 
        [](const State& a, const State& b){
            return a.heuristic_val < b.heuristic_val;
        });
    cout << it->path << endl;

    return 0;
}