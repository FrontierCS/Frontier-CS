#include <iostream>
#include <vector>
#include <string>
#include <queue>
#include <iomanip>
#include <cmath>
#include <algorithm>

const int N = 20;

int si, sj, ti, tj;
double p;
bool h_wall[N][N - 1];
bool v_wall[N - 1][N];
int dist[N][N];

// Moves: U, D, L, R
int dr[] = {-1, 1, 0, 0};
int dc[] = {0, 0, -1, 1};
char move_char[] = {'U', 'D', 'L', 'R'};

struct State {
    int r, c;
};

// Check if move from (r, c) in direction dir_idx is blocked
bool is_blocked(int r, int c, int dir_idx) {
    if (dir_idx == 0) { // U
        return r == 0 || v_wall[r - 1][c];
    }
    if (dir_idx == 1) { // D
        return r == N - 1 || v_wall[r][c];
    }
    if (dir_idx == 2) { // L
        return c == 0 || h_wall[r][c - 1];
    }
    if (dir_idx == 3) { // R
        return c == N - 1 || h_wall[r][c];
    }
    return true; // Should not happen
}

// Get next position after attempting a move
State get_next_pos(int r, int c, int dir_idx) {
    if (is_blocked(r, c, dir_idx)) {
        return {r, c};
    }
    return {r + dr[dir_idx], c + dc[dir_idx]};
}

void precompute_distances() {
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            dist[i][j] = -1;
        }
    }

    std::queue<State> q;
    q.push({ti, tj});
    dist[ti][tj] = 0;

    while (!q.empty()) {
        State curr = q.front();
        q.pop();

        for (int i = 0; i < 4; ++i) { // For each direction
            State neighbor = {curr.r + dr[i], curr.c + dc[i]};

            if (neighbor.r < 0 || neighbor.r >= N || neighbor.c < 0 || neighbor.c >= N) continue;

            int opposite_dir;
            if (i == 0) opposite_dir = 1; // U -> D
            else if (i == 1) opposite_dir = 0; // D -> U
            else if (i == 2) opposite_dir = 3; // L -> R
            else opposite_dir = 2; // R -> L

            if (is_blocked(neighbor.r, neighbor.c, opposite_dir)) continue;
            
            if (dist[neighbor.r][neighbor.c] == -1) {
                dist[neighbor.r][neighbor.c] = dist[curr.r][curr.c] + 1;
                q.push(neighbor);
            }
        }
    }
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    std::cin >> si >> sj >> ti >> tj >> p;
    std::vector<std::string> h_walls_str(N);
    std::vector<std::string> v_walls_str(N - 1);
    for (int i = 0; i < N; ++i) std::cin >> h_walls_str[i];
    for (int i = 0; i < N - 1; ++i) std::cin >> v_walls_str[i];

    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N - 1; ++j) {
            h_wall[i][j] = (h_walls_str[i][j] == '1');
        }
    }
    for (int i = 0; i < N - 1; ++i) {
        for (int j = 0; j < N; ++j) {
            v_wall[i][j] = (v_walls_str[i][j] == '1');
        }
    }

    precompute_distances();

    std::vector<std::vector<long double>> prob(N, std::vector<long double>(N, 0.0));
    prob[si][sj] = 1.0;

    std::string ans = "";
    const double EPS = 1e-12;

    for (int k = 0; k < 200; ++k) {
        char best_move = '?';
        long double max_metric = -1e18;
        std::vector<std::vector<long double>> best_next_prob(N, std::vector<long double>(N, 0.0));

        for (int move_idx = 0; move_idx < 4; ++move_idx) {
            std::vector<std::vector<long double>> next_prob(N, std::vector<long double>(N, 0.0));
            long double p_reach_this_turn = 0.0;

            for (int r = 0; r < N; ++r) {
                for (int c = 0; c < N; ++c) {
                    if (prob[r][c] < EPS) continue;

                    // Stay part (forget move)
                    next_prob[r][c] += prob[r][c] * p;

                    // Move part
                    State next_pos = get_next_pos(r, c, move_idx);
                    if (next_pos.r == ti && next_pos.c == tj) {
                        p_reach_this_turn += prob[r][c] * (1.0 - p);
                    } else {
                        next_prob[next_pos.r][next_pos.c] += prob[r][c] * (1.0 - p);
                    }
                }
            }
            
            long double expected_dist_future = 0.0;
            for (int r = 0; r < N; ++r) {
                for (int c = 0; c < N; ++c) {
                    if (next_prob[r][c] > EPS && dist[r][c] != -1) {
                         expected_dist_future += next_prob[r][c] * dist[r][c];
                    }
                }
            }

            long double metric = p_reach_this_turn - expected_dist_future / (1.0 - p);
            
            if (metric > max_metric) {
                max_metric = metric;
                best_move = move_char[move_idx];
                best_next_prob = next_prob;
            }
        }

        ans += best_move;
        prob = best_next_prob;
        
        long double total_prob_left = 0;
        for(int r = 0; r < N; ++r) {
            for(int c = 0; c < N; ++c) {
                total_prob_left += prob[r][c];
            }
        }
        if (total_prob_left < EPS) {
            break;
        }
    }

    std::cout << ans << std::endl;

    return 0;
}