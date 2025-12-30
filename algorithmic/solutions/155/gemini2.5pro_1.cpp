#include <iostream>
#include <vector>
#include <string>
#include <queue>
#include <array>
#include <algorithm>
#include <cmath>
#include <iomanip>
#include <functional>

const int N = 20;
const int MAX_L = 200;

int si, sj, ti, tj;
double p;
bool h_walls[N][N - 1];
bool v_walls[N - 1][N];
int dist[N][N];

struct State {
    std::string path;
    double score;
    std::array<std::array<double, N>, N> dp;
    double heuristic_score;
};

bool has_wall(int r, int c, char move) {
    if (move == 'U') return r == 0 || v_walls[r - 1][c];
    if (move == 'D') return r == N - 1 || v_walls[r][c];
    if (move == 'L') return c == 0 || h_walls[r][c - 1];
    if (move == 'R') return c == N - 1 || h_walls[r][c];
    return true;
}

std::pair<int, int> next_pos(int r, int c, char move) {
    if (move == 'U') return {r - 1, c};
    if (move == 'D') return {r + 1, c};
    if (move == 'L') return {r, c - 1};
    if (move == 'R') return {r, c + 1};
    return {r, c};
}

void precompute_dist() {
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            dist[i][j] = -1;
        }
    }

    std::queue<std::pair<int, int>> q;
    q.push({ti, tj});
    dist[ti][tj] = 0;
    
    const char moves[] = "UDLR";

    while (!q.empty()) {
        auto [r, c] = q.front();
        q.pop();

        for (int i = 0; i < 4; ++i) {
            char move = moves[i];
            if (!has_wall(r, c, move)) {
                auto [nr, nc] = next_pos(r, c, move);
                if (dist[nr][nc] == -1) {
                    dist[nr][nc] = dist[r][c] + 1;
                    q.push({nr, nc});
                }
            }
        }
    }
}

void solve() {
    std::cin >> si >> sj >> ti >> tj >> p;
    for (int i = 0; i < N; ++i) {
        std::string row;
        std::cin >> row;
        for (int j = 0; j < N - 1; ++j) {
            h_walls[i][j] = (row[j] == '1');
        }
    }
    for (int i = 0; i < N - 1; ++i) {
        std::string row;
        std::cin >> row;
        for (int j = 0; j < N; ++j) {
            v_walls[i][j] = (row[j] == '1');
        }
    }

    precompute_dist();
    
    const int BEAM_WIDTH = 80;
    
    std::vector<State> beam;
    
    State initial_state;
    initial_state.path = "";
    initial_state.score = 0.0;
    for(auto& row : initial_state.dp) row.fill(0.0);
    initial_state.dp[si][sj] = 1.0;
    
    double future_score = 0.0;
    double estimated_time = dist[si][sj] / (1.0 - p);
    if (estimated_time <= 400.0) {
        future_score = 1.0 * (401.0 - estimated_time);
    }
    initial_state.heuristic_score = initial_state.score + future_score;

    beam.push_back(std::move(initial_state));
    
    const char moves[] = "UDLR";

    for (int t = 1; t <= MAX_L; ++t) {
        std::vector<State> candidates;
        candidates.reserve(beam.size() * 4);
        for (const auto& s : beam) {
            for (char move : moves) {
                State next_s;
                next_s.path = s.path + move;
                
                for(auto& row : next_s.dp) row.fill(0.0);
                
                for(int i=0; i<N; ++i) {
                    for(int j=0; j<N; ++j) {
                        if (s.dp[i][j] < 1e-18) continue;
                        
                        next_s.dp[i][j] += p * s.dp[i][j];
                        
                        if (has_wall(i, j, move)) {
                            next_s.dp[i][j] += (1.0 - p) * s.dp[i][j];
                        } else {
                            auto [ni, nj] = next_pos(i, j, move);
                            next_s.dp[ni][nj] += (1.0 - p) * s.dp[i][j];
                        }
                    }
                }
                
                double p_arrived = next_s.dp[ti][tj];
                if (p_arrived > 0) {
                    next_s.dp[ti][tj] = 0.0;
                }
                
                next_s.score = s.score + p_arrived * (401.0 - t);
                
                future_score = 0.0;
                for (int i = 0; i < N; ++i) {
                    for (int j = 0; j < N; ++j) {
                        if (next_s.dp[i][j] > 1e-18) {
                            double estimated_time_from_now = dist[i][j] / (1.0 - p);
                            if (t + estimated_time_from_now <= 400.0) {
                                future_score += next_s.dp[i][j] * (401.0 - (t + estimated_time_from_now));
                            }
                        }
                    }
                }
                next_s.heuristic_score = next_s.score + future_score;
                candidates.push_back(std::move(next_s));
            }
        }
        
        size_t k = std::min((size_t)candidates.size(), (size_t)BEAM_WIDTH);
        std::partial_sort(candidates.begin(), candidates.begin() + k, candidates.end(), 
            [](const State& a, const State& b){
                return a.heuristic_score > b.heuristic_score;
            });
        
        beam.assign(candidates.begin(), candidates.begin() + k);
    }
    
    std::string best_path = "";
    double max_score = -1.0;
    
    if (!beam.empty()) {
        for(const auto& s : beam) {
            if(s.score > max_score) {
                max_score = s.score;
                best_path = s.path;
            }
        }
    } else {
        // Fallback, though beam should never be empty
        best_path = "D";
    }

    std::cout << best_path << std::endl;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    solve();
    return 0;
}