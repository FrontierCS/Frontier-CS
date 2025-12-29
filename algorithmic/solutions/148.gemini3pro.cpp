#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <random>
#include <chrono>
#include <cstring>

using namespace std;

// Constants and Globals
const int N = 50;
int si, sj;
int T[N][N];
int P[N][N];
int M = 0; 

// Visited token array to track visited tiles efficiently
// Max tiles is 50*50 = 2500, so 2505 is sufficient.
int visited_token[2505];
int current_token = 0;

// Directions: U, D, L, R
const int dr[4] = {-1, 1, 0, 0};
const int dc[4] = {0, 0, -1, 1};
const char dchar[4] = {'U', 'D', 'L', 'R'};

// Random Number Generator
mt19937 rng(121);

// Time control
auto start_time = chrono::high_resolution_clock::now();
const double TIME_LIMIT = 1.95;

struct Candidate {
    int r, c, dir;
    double weight;
};

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    // Input processing
    if (!(cin >> si >> sj)) return 0;
    
    int max_id = 0;
    for (int i = 0; i < N; i++) {
        for (int j = 0; j < N; j++) {
            cin >> T[i][j];
            max_id = max(max_id, T[i][j]);
        }
    }
    M = max_id + 1;
    for (int i = 0; i < N; i++) {
        for (int j = 0; j < N; j++) {
            cin >> P[i][j];
        }
    }

    string best_path = "";
    int best_score = -1;

    memset(visited_token, 0, sizeof(visited_token));

    int iterations = 0;
    
    // Main search loop: Randomized Greedy with restarts
    while (true) {
        iterations++;
        // Check time periodically (every 64 iterations)
        if ((iterations & 63) == 0) {
            auto now = chrono::high_resolution_clock::now();
            chrono::duration<double> diff = now - start_time;
            if (diff.count() > TIME_LIMIT) break;
        }

        current_token++;
        int curr_r = si;
        int curr_c = sj;
        int curr_score = P[si][sj];
        
        string curr_path;
        curr_path.reserve(2500);

        // Mark start tile as visited
        visited_token[T[curr_r][curr_c]] = current_token;

        // Path construction
        while (true) {
            // Collect valid candidates
            vector<Candidate> candidates;
            candidates.reserve(4);

            for (int i = 0; i < 4; i++) {
                int nr = curr_r + dr[i];
                int nc = curr_c + dc[i];

                // Check bounds
                if (nr >= 0 && nr < N && nc >= 0 && nc < N) {
                    int tid = T[nr][nc];
                    // Constraint: Tile not visited yet in this path
                    if (visited_token[tid] != current_token) {
                        // Heuristic Calculation
                        // We use a combination of current value, lookahead value, and degree (future options)
                        int p_val = P[nr][nc];
                        int max_next = 0;
                        int degree = 0;
                        
                        // Check neighbors of the candidate to assess quality
                        for (int j = 0; j < 4; j++) {
                            int nnr = nr + dr[j];
                            int nnc = nc + dc[j];
                            if (nnr >= 0 && nnr < N && nnc >= 0 && nnc < N) {
                                int next_tid = T[nnr][nnc];
                                // A valid next step must be unvisited and NOT the same tile as the candidate
                                if (visited_token[next_tid] != current_token && next_tid != tid) {
                                    max_next = max(max_next, P[nnr][nnc]);
                                    degree++;
                                }
                            }
                        }
                        
                        // Weight formula
                        // degree is heavily weighted to prevent dead ends
                        double h = (double)p_val + 0.7 * max_next + 15.0 * degree;
                        
                        // Add randomness to explore different paths across restarts
                        double noise = (rng() % 200) * 0.1; // 0.0 to 20.0
                        h += noise;
                        
                        candidates.push_back({nr, nc, i, h});
                    }
                }
            }

            if (candidates.empty()) break;

            // Greedy choice based on randomized weights
            sort(candidates.begin(), candidates.end(), [](const Candidate& a, const Candidate& b){
                return a.weight > b.weight;
            });

            const auto& best_move = candidates[0];

            // Execute move
            curr_r = best_move.r;
            curr_c = best_move.c;
            visited_token[T[curr_r][curr_c]] = current_token;
            curr_score += P[curr_r][curr_c];
            curr_path += dchar[best_move.dir];
        }

        // Keep the best solution found so far
        if (curr_score > best_score) {
            best_score = curr_score;
            best_path = curr_path;
        }
    }

    cout << best_path << endl;

    return 0;
}