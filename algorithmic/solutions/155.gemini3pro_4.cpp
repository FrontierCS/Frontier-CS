#include <iostream>
#include <vector>
#include <string>
#include <queue>
#include <cmath>
#include <algorithm>

using namespace std;

// Constants
const int N = 20;
const int MAX_STEPS = 200;
const int BEAM_WIDTH = 1500;
const double EPS = 1e-9;

// Inputs
int Si, Sj, Ti, Tj;
double P;
int H[N][N-1];
int V[N-1][N];

// Graph and Logic
int adj[N*N][4]; 
int dist[N*N];
int dr[] = {-1, 1, 0, 0};
int dc[] = {0, 0, -1, 1};
char dirs[] = {'U', 'D', 'L', 'R'};

struct State {
    vector<pair<int, double>> probs; 
    double current_score;
    string path;
    double heuristic; 
};

inline int idx(int r, int c) {
    return r * N + c;
}

// Global buffers for performance
double temp_probs[N*N]; 
int active_indices[N*N];
int visited_token[N*N];
int token_counter = 0;

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    // Input parsing
    if (!(cin >> Si >> Sj >> Ti >> Tj >> P)) return 0;
    for (int i = 0; i < N; ++i) {
        string s; cin >> s;
        for (int j = 0; j < N - 1; ++j) H[i][j] = s[j] - '0';
    }
    for (int i = 0; i < N - 1; ++i) {
        string s; cin >> s;
        for (int j = 0; j < N; ++j) V[i][j] = s[j] - '0';
    }

    // Build adjacency graph (next state logic)
    for (int r = 0; r < N; ++r) {
        for (int c = 0; c < N; ++c) {
            int u = idx(r, c);
            // U
            if (r > 0 && V[r-1][c] == 0) adj[u][0] = idx(r-1, c);
            else adj[u][0] = u;
            // D
            if (r < N-1 && V[r][c] == 0) adj[u][1] = idx(r+1, c);
            else adj[u][1] = u;
            // L
            if (c > 0 && H[r][c-1] == 0) adj[u][2] = idx(r, c-1);
            else adj[u][2] = u;
            // R
            if (c < N-1 && H[r][c] == 0) adj[u][3] = idx(r, c+1);
            else adj[u][3] = u;
        }
    }

    // Compute BFS distances from target for heuristic
    fill(dist, dist + N*N, 1e9);
    int target = idx(Ti, Tj);
    dist[target] = 0;
    
    queue<int> q;
    q.push(target);
    
    // Reverse BFS to fill dist
    while (!q.empty()) {
        int u = q.front();
        q.pop();
        
        int r = u / N;
        int c = u % N;
        
        // Check neighbors that can reach u (undirected edges for walls)
        // From Up (r-1, c) to Down (r, c)
        if (r > 0 && V[r-1][c] == 0) {
            int v = idx(r-1, c);
            if (dist[v] > dist[u] + 1) {
                dist[v] = dist[u] + 1;
                q.push(v);
            }
        }
        // From Down (r+1, c) to Up (r, c)
        if (r < N-1 && V[r][c] == 0) {
            int v = idx(r+1, c);
            if (dist[v] > dist[u] + 1) {
                dist[v] = dist[u] + 1;
                q.push(v);
            }
        }
        // From Left (r, c-1) to Right (r, c)
        if (c > 0 && H[r][c-1] == 0) {
            int v = idx(r, c-1);
            if (dist[v] > dist[u] + 1) {
                dist[v] = dist[u] + 1;
                q.push(v);
            }
        }
        // From Right (r, c+1) to Left (r, c)
        if (c < N-1 && H[r][c] == 0) {
            int v = idx(r, c+1);
            if (dist[v] > dist[u] + 1) {
                dist[v] = dist[u] + 1;
                q.push(v);
            }
        }
    }

    double inv_prob_move = 1.0 / (1.0 - P);

    // Beam Search initialization
    vector<State> beam;
    State initial;
    initial.probs.push_back({idx(Si, Sj), 1.0});
    initial.current_score = 0;
    initial.path = "";
    initial.heuristic = 0;
    beam.push_back(initial);
    
    for (int step = 1; step <= MAX_STEPS; ++step) {
        vector<State> candidates;
        candidates.reserve(beam.size() * 4);
        
        for (const auto& s : beam) {
            if (s.probs.empty()) {
                State next_s = s;
                next_s.path += 'U'; // Dummy move
                // Heuristic remains same or decreases slightly due to step? 
                // Since current_score is fixed and probs empty, heuristic = current_score.
                // It should compete fairly.
                candidates.push_back(next_s);
                continue;
            }

            for (int d = 0; d < 4; ++d) {
                token_counter++;
                int active_count = 0;
                double new_mass_at_target = 0;
                
                // Calculate next distribution
                for (auto& p : s.probs) {
                    int u = p.first;
                    double prob = p.second;
                    
                    // Probability of staying (forgetting)
                    if (visited_token[u] != token_counter) {
                        visited_token[u] = token_counter;
                        temp_probs[u] = 0;
                        active_indices[active_count++] = u;
                    }
                    temp_probs[u] += prob * P;
                    
                    // Probability of moving
                    int v = adj[u][d];
                    if (v == target) {
                        new_mass_at_target += prob * (1.0 - P);
                    } else {
                        if (visited_token[v] != token_counter) {
                            visited_token[v] = token_counter;
                            temp_probs[v] = 0;
                            active_indices[active_count++] = v;
                        }
                        temp_probs[v] += prob * (1.0 - P);
                    }
                }
                
                State next_s;
                next_s.path = s.path + dirs[d];
                // Score update
                next_s.current_score = s.current_score + new_mass_at_target * (401 - step);
                next_s.probs.reserve(active_count);
                
                double potential = 0;
                for (int i = 0; i < active_count; ++i) {
                    int u = active_indices[i];
                    double p_val = temp_probs[u];
                    if (p_val > EPS) {
                        next_s.probs.push_back({u, p_val});
                        // Heuristic: expected value of arrival
                        double est_turns = step + dist[u] * inv_prob_move;
                        potential += p_val * (401 - est_turns);
                    }
                }
                
                next_s.heuristic = next_s.current_score + potential;
                candidates.push_back(next_s);
            }
        }
        
        // Selection
        if (candidates.size() > BEAM_WIDTH) {
            nth_element(candidates.begin(), candidates.begin() + BEAM_WIDTH, candidates.end(), 
                [](const State& a, const State& b) {
                    return a.heuristic > b.heuristic;
                });
            candidates.resize(BEAM_WIDTH);
        }
        
        beam = move(candidates);
    }
    
    // Find best final state
    string best_path = "";
    double max_h = -1e18; // Initialize very low
    
    for (const auto& s : beam) {
        if (s.heuristic > max_h) {
            max_h = s.heuristic;
            best_path = s.path;
        }
    }
    
    cout << best_path << endl;

    return 0;
}