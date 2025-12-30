#include <iostream>
#include <vector>
#include <string>
#include <cmath>
#include <numeric>
#include <queue>
#include <algorithm>
#include <iomanip>

using namespace std;

const int N = 20;
long long h[N][N];
vector<pair<int, int>> pos_squares;
vector<pair<int, int>> neg_squares;
vector<string> commands;

int cur_r = 0, cur_c = 0;
int dist_to_sink[N][N];

int dr[] = {-1, 1, 0, 0};
int dc[] = {0, 0, -1, 1};

void move_to(int r, int c) {
    while (cur_r < r) {
        commands.push_back("D");
        cur_r++;
    }
    while (cur_r > r) {
        commands.push_back("U");
        cur_r--;
    }
    while (cur_c < c) {
        commands.push_back("R");
        cur_c++;
    }
    while (cur_c > c) {
        commands.push_back("L");
        cur_c--;
    }
}

void load(long long d) {
    if (d == 0) return;
    commands.push_back("+" + to_string(d));
}

void unload(long long d) {
    if (d == 0) return;
    commands.push_back("-" + to_string(d));
}

void compute_dist_to_sinks() {
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            dist_to_sink[i][j] = 1e9;
        }
    }
    queue<pair<int, int>> q;
    for (const auto& p : neg_squares) {
        dist_to_sink[p.first][p.second] = 0;
        q.push(p);
    }

    while (!q.empty()) {
        pair<int, int> curr = q.front();
        q.pop();
        int r = curr.first;
        int c = curr.second;

        for (int i = 0; i < 4; ++i) {
            int nr = r + dr[i];
            int nc = c + dc[i];
            if (nr >= 0 && nr < N && nc >= 0 && nc < N && dist_to_sink[nr][nc] > dist_to_sink[r][c] + 1) {
                dist_to_sink[nr][nc] = dist_to_sink[r][c] + 1;
                q.push({nr, nc});
            }
        }
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n_dummy;
    cin >> n_dummy;

    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            cin >> h[i][j];
            if (h[i][j] > 0) {
                pos_squares.push_back({i, j});
            } else if (h[i][j] < 0) {
                neg_squares.push_back({i, j});
            }
        }
    }

    while (!pos_squares.empty()) {
        if (!neg_squares.empty()) {
            compute_dist_to_sinks();
        }

        int best_pos_idx = -1;
        long double min_score = -1.0;

        for (int i = 0; i < pos_squares.size(); ++i) {
            int r_s = pos_squares[i].first;
            int c_s = pos_squares[i].second;
            
            long long move_to_dist = abs(cur_r - r_s) + abs(cur_c - c_s);
            long long move_from_dist = neg_squares.empty() ? (N - 1 - r_s + N - 1 - c_s) : dist_to_sink[r_s][c_s];
            
            long double current_score = ((long double)move_to_dist * 100.0) / h[r_s][c_s] + 
                                        (long double)move_from_dist * (1.0 + 100.0 / h[r_s][c_s]);

            if (best_pos_idx == -1 || current_score < min_score) {
                min_score = current_score;
                best_pos_idx = i;
            }
        }

        int r_s = pos_squares[best_pos_idx].first;
        int c_s = pos_squares[best_pos_idx].second;

        move_to(r_s, c_s);

        long long load_amount = h[r_s][c_s];
        load(load_amount);
        h[r_s][c_s] = 0;
        pos_squares[best_pos_idx] = pos_squares.back();
        pos_squares.pop_back();

        long long truck_load = load_amount;

        while (truck_load > 0) {
            if (neg_squares.empty()) {
                break;
            }

            int best_neg_idx = -1;
            int min_dist = 1e9;
            for (int i = 0; i < neg_squares.size(); ++i) {
                int r = neg_squares[i].first;
                int c = neg_squares[i].second;
                int dist = abs(cur_r - r) + abs(cur_c - c);
                if (dist < min_dist) {
                    min_dist = dist;
                    best_neg_idx = i;
                }
            }

            int r_d = neg_squares[best_neg_idx].first;
            int c_d = neg_squares[best_neg_idx].second;

            move_to(r_d, c_d);

            long long unload_amount = min((long long)abs(h[r_d][c_d]), truck_load);
            unload(unload_amount);
            h[r_d][c_d] += unload_amount;
            truck_load -= unload_amount;

            if (h[r_d][c_d] == 0) {
                neg_squares[best_neg_idx] = neg_squares.back();
                neg_squares.pop_back();
            }
        }
    }
    
    for (const auto& cmd : commands) {
        cout << cmd << "\n";
    }

    return 0;
}