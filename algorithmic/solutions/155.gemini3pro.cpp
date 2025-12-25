#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <queue>
#include <tuple>

using namespace std;

// Global variables for problem data
int Si, Sj, Ti, Tj;
double P_forget;
int H[20][19];
int V[19][20];
int dist_map[20][20]; 

// Directions: U, D, L, R
int di[] = {-1, 1, 0, 0};
int dj[] = {0, 0, -1, 1};
char dc[] = {'U', 'D', 'L', 'R'};

struct State {
    // Flattened 20x20 grid probabilities
    double probs[400];
    double expected_score;
    string s;
    
    State() {
        for(int i=0; i<400; ++i) probs[i] = 0.0;
        expected_score = 0.0;
        s.reserve(200);
    }
};

// Check if move is valid (no wall blocking)
bool can_move(int i, int j, int dir) {
    int ni = i + di[dir];
    int nj = j + dj[dir];
    if (ni < 0 || ni >= 20 || nj < 0 || nj >= 20) return false;
    
    if (dir == 0) { // U
        if (V[ni][nj] == 1) return false;
    } else if (dir == 1) { // D
        if (V[i][j] == 1) return false;
    } else if (dir == 2) { // L
        if (H[ni][nj] == 1) return false;
    } else if (dir == 3) { // R
        if (H[i][j] == 1) return false;
    }
    return true;
}

// BFS to compute shortest path distance from all cells to target
void bfs_dist() {
    for(int i=0; i<20; ++i)
        for(int j=0; j<20; ++j)
            dist_map[i][j] = 99999;
    
    queue<pair<int,int>> q;
    q.push({Ti, Tj});
    dist_map[Ti][Tj] = 0;
    
    while(!q.empty()){
        pair<int,int> curr = q.front();
        q.pop();
        int r = curr.first;
        int c = curr.second;
        
        for(int k=0; k<4; ++k) {
            int nr = r + di[k];
            int nc = c + dj[k];
            
            if (nr >= 0 && nr < 20 && nc >= 0 && nc < 20) {
                // If we can move from r,c to neighbor in direction k,
                // then neighbor is connected to r,c.
                if (can_move(r, c, k)) {
                    if (dist_map[nr][nc] > dist_map[r][c] + 1) {
                        dist_map[nr][nc] = dist_map[r][c] + 1;
                        q.push({nr, nc});
                    }
                }
            }
        }
    }
}

// Heuristic evaluation: Current Expected Score + Potential Future Score
double eval_heuristic(const State& st, int steps_taken) {
    double future_val = 0;
    double move_prob = 1.0 - P_forget;
    
    for(int i=0; i<400; ++i) {
        if (st.probs[i] > 1e-9) {
            int r = i / 20;
            int c = i % 20;
            // Expected steps to reach target from here considering failures
            double expected_rem_steps = dist_map[r][c] / move_prob;
            double arrival_time = steps_taken + expected_rem_steps;
            
            // Linear scoring function, clamped loosely
            if (arrival_time < 400.0) {
                future_val += st.probs[i] * (401.0 - arrival_time);
            }
        }
    }
    return st.expected_score + future_val;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    if (!(cin >> Si >> Sj >> Ti >> Tj >> P_forget)) return 0;
    
    for(int i=0; i<20; ++i) {
        string s; cin >> s;
        for(int j=0; j<19; ++j) H[i][j] = s[j] - '0';
    }
    for(int i=0; i<19; ++i) {
        string s; cin >> s;
        for(int j=0; j<20; ++j) V[i][j] = s[j] - '0';
    }
    
    bfs_dist();
    
    vector<State> beam;
    {
        State initial;
        initial.probs[Si*20 + Sj] = 1.0;
        beam.push_back(initial);
    }
    
    // Beam width setting: trade-off between speed and quality
    int BEAM_WIDTH = 250; 
    
    for (int step = 0; step < 200; ++step) {
        vector<State> next_states;
        next_states.reserve(beam.size() * 4);
        
        double move_p = 1.0 - P_forget;
        
        for (const auto& parent : beam) {
            for (int dir = 0; dir < 4; ++dir) {
                State next_st;
                next_st.s = parent.s;
                next_st.s += dc[dir];
                next_st.expected_score = parent.expected_score;
                
                // Update probability distribution
                for(int i=0; i<400; ++i) {
                    if (parent.probs[i] <= 1e-9) continue;
                    
                    double p_curr = parent.probs[i];
                    
                    // Stay (due to forgetting)
                    next_st.probs[i] += p_curr * P_forget;
                    
                    // Try to Move
                    int r = i / 20;
                    int c = i % 20;
                    
                    if (can_move(r, c, dir)) {
                        int nr = r + di[dir];
                        int nc = c + dj[dir];
                        
                        if (nr == Ti && nc == Tj) {
                            // Reached target: accumulate score
                            next_st.expected_score += p_curr * move_p * (401.0 - (double)(step + 1));
                        } else {
                            // Moved to new cell
                            next_st.probs[nr*20 + nc] += p_curr * move_p;
                        }
                    } else {
                        // Blocked by wall: stay
                        next_st.probs[i] += p_curr * move_p;
                    }
                }
                next_states.push_back(next_st);
            }
        }
        
        // Beam Selection
        vector<pair<double, int>> scores;
        scores.reserve(next_states.size());
        for(int i=0; i<next_states.size(); ++i) {
            scores.push_back({eval_heuristic(next_states[i], step + 1), i});
        }
        
        if (scores.empty()) break;

        int next_k = min((int)scores.size(), BEAM_WIDTH);
        
        // Partial sort to find top K candidates
        nth_element(scores.begin(), scores.begin() + next_k, scores.end(), 
            [](const pair<double, int>& a, const pair<double, int>& b){
                return a.first > b.first;
            });
        
        vector<State> next_beam;
        next_beam.reserve(next_k);
        for(int i=0; i<next_k; ++i) {
            next_beam.push_back(next_states[scores[i].second]);
        }
        beam = move(next_beam);
    }
    
    // Find best final state
    double best_score = -1.0;
    string best_str = "";
    
    for(const auto& st : beam) {
        if (st.expected_score > best_score) {
            best_score = st.expected_score;
            best_str = st.s;
        }
    }
    
    cout << best_str << endl;
    
    return 0;
}