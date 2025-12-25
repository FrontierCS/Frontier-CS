#include <iostream>
#include <vector>
#include <string>
#include <queue>
#include <iomanip>
#include <algorithm>

using namespace std;

const int N = 20;

int si, sj, ti, tj;
double p;
vector<string> h(N);
vector<string> v(N - 1);

int dist[N][N];
double prob[N][N];
double next_prob[N][N];

// U, D, L, R
int dr[] = {-1, 1, 0, 0};
int dc[] = {0, 0, -1, 1};
char move_char[] = {'U', 'D', 'L', 'R'};

bool is_valid(int r, int c) {
    return r >= 0 && r < N && c >= 0 && c < N;
}

pair<int, int> get_next_pos(int r, int c, char move) {
    int move_idx = -1;
    if (move == 'U') move_idx = 0;
    else if (move == 'D') move_idx = 1;
    else if (move == 'L') move_idx = 2;
    else if (move == 'R') move_idx = 3;
    
    int nr = r + dr[move_idx];
    int nc = c + dc[move_idx];

    if (!is_valid(nr, nc)) {
        return {r, c};
    }

    if (move == 'U' && v[r - 1][c] == '1') return {r, c};
    if (move == 'D' && v[r][c] == '1') return {r, c};
    if (move == 'L' && h[r][c - 1] == '1') return {r, c};
    if (move == 'R' && h[r][c] == '1') return {r, c};

    return {nr, nc};
}

void bfs_dist() {
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            dist[i][j] = -1;
        }
    }

    queue<pair<int, int>> q;
    q.push({ti, tj});
    dist[ti][tj] = 0;

    while (!q.empty()) {
        pair<int, int> curr = q.front();
        q.pop();
        int r = curr.first;
        int c = curr.second;

        for (int i = 0; i < 4; ++i) {
            int pr = r + dr[i];
            int pc = c + dc[i];

            if (!is_valid(pr, pc)) continue;

            char move_to_curr;
            if (dr[i] == -1) move_to_curr = 'D';
            else if (dr[i] == 1) move_to_curr = 'U';
            else if (dc[i] == -1) move_to_curr = 'R';
            else move_to_curr = 'L';
            
            pair<int, int> next_pos = get_next_pos(pr, pc, move_to_curr);

            if (next_pos.first == r && next_pos.second == c) {
                if (dist[pr][pc] == -1) {
                    dist[pr][pc] = dist[r][c] + 1;
                    q.push({pr, pc});
                }
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
    
    bfs_dist();

    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            prob[i][j] = 0.0;
        }
    }
    prob[si][sj] = 1.0;

    string ans = "";
    char preferred_moves[] = {'D', 'R', 'U', 'L'};

    for (int t = 0; t < 200; ++t) {
        char best_move = ' ';
        double min_exp_dist = 1e18;
        
        for(char move : preferred_moves) {
            double current_exp_dist_sum = 0;
            double remaining_prob_mass = 0;

            for (int r = 0; r < N; ++r) {
                for (int c = 0; c < N; ++c) {
                    if (prob[r][c] > 1e-18) {
                        // Forgot case
                        current_exp_dist_sum += prob[r][c] * p * dist[r][c];
                        remaining_prob_mass += prob[r][c] * p;

                        // Move case
                        pair<int, int> next_pos = get_next_pos(r, c, move);
                        if (next_pos.first == ti && next_pos.second == tj) {
                            // Reached target
                        } else {
                            current_exp_dist_sum += prob[r][c] * (1 - p) * dist[next_pos.first][next_pos.second];
                            remaining_prob_mass += prob[r][c] * (1 - p);
                        }
                    }
                }
            }
            
            double current_exp_dist = 0;
            if (remaining_prob_mass > 1e-18) {
                current_exp_dist = current_exp_dist_sum / remaining_prob_mass;
            }
            
            if (current_exp_dist < min_exp_dist) {
                min_exp_dist = current_exp_dist;
                best_move = move;
            }
        }
        
        if (best_move == ' ') {
            best_move = preferred_moves[0];
        }

        ans += best_move;

        for (int i = 0; i < N; ++i) {
            for (int j = 0; j < N; ++j) {
                next_prob[i][j] = 0.0;
            }
        }

        for (int r = 0; r < N; ++r) {
            for (int c = 0; c < N; ++c) {
                if (prob[r][c] > 1e-18) {
                    // Forgot case
                    next_prob[r][c] += prob[r][c] * p;
                    
                    // Move case
                    pair<int, int> next_pos = get_next_pos(r, c, best_move);
                    if (next_pos.first != ti || next_pos.second != tj) {
                        next_prob[next_pos.first][next_pos.second] += prob[r][c] * (1 - p);
                    }
                }
            }
        }

        for (int i = 0; i < N; ++i) {
            for (int j = 0; j < N; ++j) {
                prob[i][j] = next_prob[i][j];
            }
        }
    }

    cout << ans << endl;

    return 0;
}