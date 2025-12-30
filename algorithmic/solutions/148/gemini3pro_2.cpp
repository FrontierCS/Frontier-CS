#pragma GCC optimize("O3,unroll-loops")
#pragma GCC target("avx2,bmi,bmi2,lzcnt,popcnt")

#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <bitset>
#include <chrono>
#include <random>

using namespace std;

const int N = 50;
const int MAX_TILES = 2505; 
const int BEAM_WIDTH = 2500; 
const double CONNECTIVITY_BONUS = 12.0;

int SI, SJ;
int T[N][N];
int P[N][N];

struct State {
    int r, c;
    int score;
    int id; 
    bitset<MAX_TILES> visited; 
};

struct History {
    int parent_id;
    char move;
};

// history_layers[i] contains the transitions that produced the states in beam step i+1
vector<vector<History>> history_layers;

int dr[4] = {-1, 1, 0, 0};
int dc[4] = {0, 0, -1, 1};
char dchar[4] = {'U', 'D', 'L', 'R'};

struct Candidate {
    double eval_score;
    int true_score;
    int parent_idx;
    int dir;
    int r, c;
};

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    auto start_time = chrono::steady_clock::now();

    if (!(cin >> SI >> SJ)) return 0;

    int max_t_id = 0;
    for(int i=0; i<N; i++) {
        for(int j=0; j<N; j++) {
            cin >> T[i][j];
            if(T[i][j] > max_t_id) max_t_id = T[i][j];
        }
    }
    for(int i=0; i<N; i++) {
        for(int j=0; j<N; j++) {
            cin >> P[i][j];
        }
    }

    vector<State> beam;
    beam.reserve(BEAM_WIDTH);
    
    bitset<MAX_TILES> initial_visited;
    initial_visited.set(T[SI][SJ]);
    
    // Initial state
    beam.push_back({SI, SJ, P[SI][SJ], 0, initial_visited});
    
    int best_score = P[SI][SJ];
    int best_final_layer_idx = -1; 
    int best_final_node_id = 0;    

    mt19937 rng(12345);
    uniform_real_distribution<double> dist(0.0, 1.0);

    int step = 0;
    
    vector<Candidate> candidates;
    candidates.reserve(BEAM_WIDTH * 4);

    while(!beam.empty()) {
        auto current_time = chrono::steady_clock::now();
        double elapsed = chrono::duration_cast<chrono::milliseconds>(current_time - start_time).count();
        if(elapsed > 1900) break; 

        candidates.clear();

        for(int i=0; i<beam.size(); ++i) {
            State &s = beam[i];
            
            for(int d=0; d<4; ++d) {
                int nr = s.r + dr[d];
                int nc = s.c + dc[d];
                
                if(nr >= 0 && nr < N && nc >= 0 && nc < N) {
                    int t_id = T[nr][nc];
                    if(!s.visited.test(t_id)) {
                        
                        // Calculate connectivity
                        int conn = 0;
                        for(int dd=0; dd<4; ++dd) {
                            int nnr = nr + dr[dd];
                            int nnc = nc + dc[dd];
                            if(nnr >= 0 && nnr < N && nnc >= 0 && nnc < N) {
                                int nt = T[nnr][nnc];
                                if(nt != t_id && !s.visited.test(nt)) {
                                    conn++;
                                }
                            }
                        }
                        
                        double eval = s.score + P[nr][nc] + CONNECTIVITY_BONUS * conn + dist(rng);
                        candidates.push_back({eval, s.score + P[nr][nc], i, d, nr, nc});
                    }
                }
            }
        }
        
        if(candidates.empty()) break;
        
        // Select top BEAM_WIDTH
        if(candidates.size() > BEAM_WIDTH) {
             nth_element(candidates.begin(), candidates.begin() + BEAM_WIDTH, candidates.end(), 
                 [](const Candidate& a, const Candidate& b) {
                     return a.eval_score > b.eval_score;
                 });
             candidates.resize(BEAM_WIDTH);
        }
        
        vector<State> next_beam;
        next_beam.reserve(candidates.size());
        vector<History> current_history;
        current_history.reserve(candidates.size());
        
        for(int i=0; i<candidates.size(); ++i) {
            const auto& cand = candidates[i];
            const State& parent = beam[cand.parent_idx];
            
            State new_state;
            new_state.r = cand.r;
            new_state.c = cand.c;
            new_state.score = cand.true_score;
            new_state.id = i;
            new_state.visited = parent.visited; 
            new_state.visited.set(T[cand.r][cand.c]);
            
            next_beam.push_back(new_state);
            current_history.push_back({cand.parent_idx, dchar[cand.dir]});
            
            if(cand.true_score > best_score) {
                best_score = cand.true_score;
                best_final_layer_idx = step;
                best_final_node_id = i;
            }
        }
        
        history_layers.push_back(move(current_history));
        beam = move(next_beam);
        step++;
    }
    
    string path = "";
    if(best_final_layer_idx != -1) {
        int cur_id = best_final_node_id;
        for(int l = best_final_layer_idx; l >= 0; --l) {
            if(cur_id >= history_layers[l].size()) break; 
            History& h = history_layers[l][cur_id];
            path += h.move;
            cur_id = h.parent_id;
        }
        reverse(path.begin(), path.end());
    }
    
    cout << path << endl;

    return 0;
}