#include <iostream>
#include <vector>
#include <string>
#include <chrono>
#include <random>
#include <numeric>
#include <algorithm>
#include <cmath>

const int N = 50;
int si, sj;
int t[N][N];
int p[N][N];
int M = 0;

int dr[] = {-1, 1, 0, 0};
int dc[] = {0, 0, -1, 1};
char move_chars[] = {'U', 'D', 'L', 'R'};

std::mt19937 rng;

struct Move {
    int r, c;
    int move_idx;
    double weighted_eval;
};

void solve() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    
    std::cin >> si >> sj;
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            std::cin >> t[i][j];
            M = std::max(M, t[i][j]);
        }
    }
    M++;
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            std::cin >> p[i][j];
        }
    }

    auto start_time = std::chrono::steady_clock::now();

    std::string best_path = "";
    long long best_score = 0;

    const double initial_alpha = 0.5;
    const double power = 2.0;

    while (true) {
        auto current_time = std::chrono::steady_clock::now();
        std::chrono::duration<double> elapsed = current_time - start_time;
        if (elapsed.count() > 1.95) {
            break;
        }

        int cr = si;
        int cc = sj;
        std::vector<bool> visited(M, false);
        visited[t[si][sj]] = true;
        std::string current_path = "";
        long long current_score = p[si][sj];
        int visited_count = 1;

        while (true) {
            std::vector<Move> possible_moves;
            double total_weighted_eval = 0;
            
            double alpha = initial_alpha * (double)(M - visited_count) / M;

            for (int i = 0; i < 4; ++i) {
                int nr = cr + dr[i];
                int nc = cc + dc[i];

                if (nr >= 0 && nr < N && nc >= 0 && nc < N && !visited[t[nr][nc]]) {
                    double current_p = p[nr][nc];
                    double future_p = 0;
                    
                    visited[t[nr][nc]] = true;
                    for (int j = 0; j < 4; ++j) {
                        int nnr = nr + dr[j];
                        int nnc = nc + dc[j];
                        if (nnr >= 0 && nnr < N && nnc >= 0 && nnc < N && !visited[t[nnr][nnc]]) {
                            future_p += p[nnr][nnc];
                        }
                    }
                    visited[t[nr][nc]] = false;

                    double eval = current_p + 1.0 + alpha * future_p;
                    double weighted_eval = std::pow(eval, power);
                    possible_moves.push_back({nr, nc, i, weighted_eval});
                    total_weighted_eval += weighted_eval;
                }
            }

            if (possible_moves.empty()) {
                break;
            }
            
            Move chosen_move = possible_moves.back();
            if (total_weighted_eval < 1e-9) {
                std::uniform_int_distribution<> dist_idx(0, possible_moves.size() - 1);
                chosen_move = possible_moves[dist_idx(rng)];
            } else {
                std::uniform_real_distribution<> dist(0, total_weighted_eval);
                double r = dist(rng);

                for (const auto& move : possible_moves) {
                    r -= move.weighted_eval;
                    if (r <= 0) {
                        chosen_move = move;
                        break;
                    }
                }
            }
            
            cr = chosen_move.r;
            cc = chosen_move.c;
            current_path += move_chars[chosen_move.move_idx];
            visited[t[cr][cc]] = true;
            current_score += p[cr][cc];
            visited_count++;
        }

        if (current_score > best_score) {
            best_score = current_score;
            best_path = current_path;
        }
    }

    std::cout << best_path << std::endl;
}

int main() {
    std::random_device rd;
    rng.seed(rd());
    solve();
    return 0;
}