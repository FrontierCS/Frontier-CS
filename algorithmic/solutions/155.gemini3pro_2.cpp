#include <iostream>
#include <vector>
#include <string>
#include <queue>
#include <tuple>
#include <algorithm>
#include <cmath>
#include <iomanip>

using namespace std;

// Global variables for grid and problem parameters
int SI, SJ, TI, TJ;
double P_err;
int H[20][19];
int V[19][20];

// BFS distances from target
int dist_to_target[20][20];

// Directions: U, D, L, R
const int DR[] = {-1, 1, 0, 0};
const int DC[] = {0, 0, -1, 1};
const char DCHAR[] = {'U', 'D', 'L', 'R'};

// Check if a move is blocked by walls or boundary
bool is_blocked(int r, int c, int dir) {
    int nr = r + DR[dir];
    int nc = c + DC[dir];
    
    // Boundary check
    if (nr < 0 || nr >= 20 || nc < 0 || nc >= 20) return true;
    
    // Wall check
    if (dir == 0) { // U: check wall between r-1 and r (V[r-1][c])
        if (V[nr][c] == 1) return true;
    } else if (dir == 1) { // D: check wall between r and r+1 (V[r][c])
        if (V[r][c] == 1) return true;
    } else if (dir == 2) { // L: check wall between c-1 and c (H[r][c-1])
        if (H[r][nc] == 1) return true;
    } else if (dir == 3) { // R: check wall between c and c+1 (H[r][c])
        if (H[r][c] == 1) return true;
    }
    return false;
}

// Compute shortest path distances from target to all cells using BFS
void bfs() {
    for (int i = 0; i < 20; ++i)
        for (int j = 0; j < 20; ++j)
            dist_to_target[i][j] = 1000000;
            
    queue<pair<int, int>> q;
    dist_to_target[TI][TJ] = 0;
    q.push({TI, TJ});
    
    while (!q.empty()) {
        auto [r, c] = q.front();
        q.pop();
        
        for (int d = 0; d < 4; ++d) {
            int nr = r + DR[d];
            int nc = c + DC[d];
            
            // Reverse direction to check wall from neighbor to current
            int inv_d = (d == 0) ? 1 : (d == 1) ? 0 : (d == 2) ? 3 : 2;
            
            if (nr >= 0 && nr < 20 && nc >= 0 && nc < 20) {
                if (!is_blocked(nr, nc, inv_d)) {
                    if (dist_to_target[nr][nc] > dist_to_target[r][c] + 1) {
                        dist_to_target[nr][nc] = dist_to_target[r][c] + 1;
                        q.push({nr, nc});
                    }
                }
            }
        }
    }
}

struct State {
    // Flattened 20x20 probability distribution
    vector<double> probs; 
    
    double current_score; // Expected score accumulated so far
    double prob_finished; // Probability mass that has reached target
    string path;
    
    State() : probs(400, 0.0), current_score(0.0), prob_finished(0.0), path("") {}
};

// Evaluate heuristic for beam search ranking
double evaluate(const State& s, int step) {
    // Heuristic combines accumulated score and estimated future score.
    // Estimated future score considers remaining probability mass and expected steps to reach target.
    // Expected steps to cross distance D is D / (1 - P_err).
    
    double expected_dist_sum = 0;
    for (int i = 0; i < 400; ++i) {
        if (s.probs[i] > 1e-12) {
            expected_dist_sum += s.probs[i] * dist_to_target[i / 20][i % 20];
        }
    }
    
    // Score formula contribution:
    // Current accumulated score + 
    // (Prob remaining) * (Score if we finish now) - (Cost of remaining steps)
    // Cost of remaining steps approx (Prob remaining) * (Avg Distance / (1-p))
    return s.current_score + (1.0 - s.prob_finished) * (401.0 - step) - expected_dist_sum / (1.0 - P_err);
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> SI >> SJ >> TI >> TJ >> P_err)) return 0;
    
    for (int i = 0; i < 20; ++i) {
        string row; cin >> row;
        for (int j = 0; j < 19; ++j) {
            H[i][j] = row[j] - '0';
        }
    }
    for (int i = 0; i < 19; ++i) {
        string row; cin >> row;
        for (int j = 0; j < 20; ++j) {
            V[i][j] = row[j] - '0';
        }
    }

    bfs();

    vector<State> beam;
    beam.reserve(1000);
    State initial;
    initial.probs[SI * 20 + SJ] = 1.0;
    beam.push_back(initial);

    // Beam width parameter. Larger is better but slower.
    // 500 fits within 2s for 200 steps.
    int BEAM_WIDTH = 500; 

    for (int step = 0; step < 200; ++step) {
        vector<pair<double, int>> candidates; 
        vector<State> next_states_storage;
        next_states_storage.reserve(beam.size() * 4);

        for (const auto& s : beam) {
            for (int d = 0; d < 4; ++d) {
                State next_s;
                next_s.path = s.path + DCHAR[d];
                next_s.current_score = s.current_score;
                next_s.prob_finished = s.prob_finished;
                next_s.probs.assign(400, 0.0);

                double new_finished_prob = 0.0;
                
                // Update probability distribution
                for (int i = 0; i < 400; ++i) {
                    if (s.probs[i] <= 1e-15) continue;
                    
                    int r = i / 20;
                    int c = i % 20;
                    double p = s.probs[i];

                    // Case 1: Forgetting the command (stay) - Prob P_err
                    next_s.probs[i] += p * P_err;

                    // Case 2: Attempting to move - Prob 1 - P_err
                    if (is_blocked(r, c, d)) {
                        // Blocked by wall/boundary -> stay
                        next_s.probs[i] += p * (1.0 - P_err);
                    } else {
                        // Move successful
                        int nr = r + DR[d];
                        int nc = c + DC[d];
                        if (nr == TI && nc == TJ) {
                            // Reached target (absorbing state)
                            new_finished_prob += p * (1.0 - P_err);
                        } else {
                            next_s.probs[nr * 20 + nc] += p * (1.0 - P_err);
                        }
                    }
                }
                
                // Update accumulated score based on probability of finishing at this exact step
                next_s.current_score += new_finished_prob * (401.0 - (step + 1));
                next_s.prob_finished += new_finished_prob;
                
                next_states_storage.push_back(next_s);
                double h = evaluate(next_s, step + 1);
                candidates.push_back({h, (int)next_states_storage.size() - 1});
            }
        }

        // Selection of top BEAM_WIDTH candidates
        if (candidates.size() > BEAM_WIDTH) {
            nth_element(candidates.begin(), candidates.begin() + BEAM_WIDTH, candidates.end(), 
                        [](const pair<double, int>& a, const pair<double, int>& b) {
                            return a.first > b.first;
                        });
            candidates.resize(BEAM_WIDTH);
        }
        
        sort(candidates.begin(), candidates.end(), [](const pair<double, int>& a, const pair<double, int>& b) {
            return a.first > b.first;
        });

        beam.clear();
        for (const auto& p : candidates) {
            beam.push_back(next_states_storage[p.second]);
        }
    }

    // Output the path corresponding to the best state found
    cout << beam[0].path << endl;

    return 0;
}