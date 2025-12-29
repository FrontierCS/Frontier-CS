#include <iostream>
#include <vector>
#include <string>
#include <queue>
#include <cmath>
#include <iomanip>
#include <algorithm>

using namespace std;

const int N = 20;

int si, sj, ti, tj;
double p;
vector<string> h(N);
vector<string> v(N - 1);

// Movement deltas and characters for U, D, L, R
int di[] = {-1, 1, 0, 0};
int dj[] = {0, 0, -1, 1};
char move_char[] = {'U', 'D', 'L', 'R'};

int dist[N][N];
double prob[N][N];

bool is_valid(int r, int c) {
    return r >= 0 && r < N && c >= 0 && c < N;
}

// Checks for a wall between adjacent cells (r1, c1) and (r2, c2)
bool has_wall(int r1, int c1, int r2, int c2) {
    if (r1 == r2) { // Horizontal move
        if (c1 > c2) swap(c1, c2); // Ensure c1 < c2
        return h[r1][c1] == '1';
    } else { // Vertical move
        if (r1 > r2) swap(r1, r2); // Ensure r1 < r2
        return v[r1][c1] == '1';
    }
}

// BFS from the target to compute shortest path distance from all cells
void bfs_from_target() {
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            dist[i][j] = -1;
        }
    }
    queue<pair<int, int>> q;

    dist[ti][tj] = 0;
    q.push({ti, tj});

    while (!q.empty()) {
        auto [r, c] = q.front();
        q.pop();

        for (int i = 0; i < 4; ++i) {
            int nr = r + di[i];
            int nc = c + dj[i];

            if (is_valid(nr, nc) && dist[nr][nc] == -1 && !has_wall(r, c, nr, nc)) {
                dist[nr][nc] = dist[r][c] + 1;
                q.push({nr, nc});
            }
        }
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    cin >> si >> sj >> ti >> tj >> p;
    for (int i = 0; i < N; ++i) cin >> h[i];
    for (int i = 0; i < N - 1; ++i) cin >> v[i];
    
    bfs_from_target();

    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            prob[i][j] = 0.0;
        }
    }
    prob[si][sj] = 1.0;

    string path = "";

    for (int k = 1; k <= 200; ++k) {
        char best_move = '?';
        double max_score_heuristic = -1e18;
        
        // Evaluate each of the 4 possible moves
        for (int move_idx = 0; move_idx < 4; ++move_idx) {
            double prob_reach_m = 0;
            vector<vector<double>> next_prob_m(N, vector<double>(N, 0.0));
            
            for (int i = 0; i < N; ++i) {
                for (int j = 0; j < N; ++j) {
                    if (prob[i][j] < 1e-18) continue;
                    
                    // Case 1: Forget move, stay at (i, j)
                    next_prob_m[i][j] += p * prob[i][j];
                    
                    // Case 2: Remember move
                    int ni = i + di[move_idx];
                    int nj = j + dj[move_idx];

                    if (!is_valid(ni, nj) || has_wall(i, j, ni, nj)) {
                        ni = i;
                        nj = j;
                    }

                    if (ni == ti && nj == tj) {
                        prob_reach_m += (1.0 - p) * prob[i][j];
                    } else {
                        next_prob_m[ni][nj] += (1.0 - p) * prob[i][j];
                    }
                }
            }

            double expected_dist_term = 0;
            for (int i = 0; i < N; ++i) {
                for (int j = 0; j < N; ++j) {
                    if (dist[i][j] != -1) {
                        expected_dist_term += next_prob_m[i][j] * dist[i][j];
                    }
                }
            }
            
            double current_score_heuristic = prob_reach_m - expected_dist_term / (1.0 - p);
            
            if (current_score_heuristic > max_score_heuristic) {
                max_score_heuristic = current_score_heuristic;
                best_move = move_char[move_idx];
            }
        }
        
        path += best_move;
        
        // Update probability distribution based on the chosen best move
        int best_move_idx = 0;
        for(int i = 0; i < 4; ++i) {
            if (move_char[i] == best_move) {
                best_move_idx = i;
                break;
            }
        }
        
        vector<vector<double>> next_prob(N, vector<double>(N, 0.0));
        for (int i = 0; i < N; ++i) {
            for (int j = 0; j < N; ++j) {
                if (prob[i][j] < 1e-18) continue;
                
                // Case 1: Forget
                next_prob[i][j] += p * prob[i][j];
                
                // Case 2: Remember
                int ni = i + di[best_move_idx];
                int nj = j + dj[best_move_idx];
                
                if (!is_valid(ni, nj) || has_wall(i, j, ni, nj)) {
                    ni = i;
                    nj = j;
                }
                
                if (!(ni == ti && nj == tj)) {
                    next_prob[ni][nj] += (1.0 - p) * prob[i][j];
                }
            }
        }
        
        for (int i = 0; i < N; ++i) {
            for (int j = 0; j < N; ++j) {
                prob[i][j] = next_prob[i][j];
            }
        }
    }

    cout << path << endl;

    return 0;
}