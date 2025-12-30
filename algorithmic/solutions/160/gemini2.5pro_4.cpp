#include <iostream>
#include <vector>
#include <string>
#include <numeric>
#include <algorithm>
#include <map>

const int N = 10;

struct GameState {
    std::vector<std::vector<int>> grid;

    GameState() : grid(N, std::vector<int>(N, 0)) {}

    void tilt(char dir) {
        if (dir == 'F') {
            for (int j = 0; j < N; ++j) {
                std::vector<int> temp;
                for (int i = 0; i < N; ++i) {
                    if (grid[i][j] != 0) temp.push_back(grid[i][j]);
                }
                for (size_t i = 0; i < temp.size(); ++i) grid[i][j] = temp[i];
                for (size_t i = temp.size(); i < N; ++i) grid[i][j] = 0;
            }
        } else if (dir == 'B') {
            for (int j = 0; j < N; ++j) {
                std::vector<int> temp;
                for (int i = 0; i < N; ++i) {
                    if (grid[i][j] != 0) temp.push_back(grid[i][j]);
                }
                for (size_t i = 0; i < temp.size(); ++i) grid[N - temp.size() + i][j] = temp[i];
                for (int i = 0; i < N - (int)temp.size(); ++i) grid[i][j] = 0;
            }
        } else if (dir == 'L') {
            for (int i = 0; i < N; ++i) {
                std::vector<int> temp;
                for (int j = 0; j < N; ++j) {
                    if (grid[i][j] != 0) temp.push_back(grid[i][j]);
                }
                for (size_t j = 0; j < temp.size(); ++j) grid[i][j] = temp[j];
                for (size_t j = temp.size(); j < N; ++j) grid[i][j] = 0;
            }
        } else if (dir == 'R') {
            for (int i = 0; i < N; ++i) {
                std::vector<int> temp;
                for (int j = 0; j < N; ++j) {
                    if (grid[i][j] != 0) temp.push_back(grid[i][j]);
                }
                for (size_t j = 0; j < temp.size(); ++j) grid[i][N - temp.size() + j] = temp[j];
                for (int j = 0; j < N - (int)temp.size(); ++j) grid[i][j] = 0;
            }
        }
    }

    long long calculate_score() const {
        std::vector<std::vector<bool>> visited(N, std::vector<bool>(N, false));
        long long total_score = 0;
        for (int i = 0; i < N; ++i) {
            for (int j = 0; j < N; ++j) {
                if (grid[i][j] != 0 && !visited[i][j]) {
                    long long component_size = 0;
                    int flavor = grid[i][j];
                    std::vector<std::pair<int, int>> q;
                    q.push_back({i, j});
                    visited[i][j] = true;
                    int head = 0;
                    while(head < (int)q.size()){
                        auto [r, c] = q[head++];
                        component_size++;
                        int dr[] = {-1, 1, 0, 0};
                        int dc[] = {0, 0, -1, 1};
                        for (int k = 0; k < 4; ++k) {
                            int nr = r + dr[k];
                            int nc = c + dc[k];
                            if (nr >= 0 && nr < N && nc >= 0 && nc < N &&
                                !visited[nr][nc] && grid[nr][nc] == flavor) {
                                visited[nr][nc] = true;
                                q.push_back({nr, nc});
                            }
                        }
                    }
                    total_score += component_size * component_size;
                }
            }
        }
        return total_score;
    }
};

void place_candy(GameState& state, int flavor, int p) {
    int empty_count = 0;
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            if (state.grid[i][j] == 0) {
                empty_count++;
                if (empty_count == p) {
                    state.grid[i][j] = flavor;
                    return;
                }
            }
        }
    }
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    std::vector<int> flavors(100);
    std::map<int, int> flavor_counts;
    for (int i = 0; i < 100; ++i) {
        std::cin >> flavors[i];
        flavor_counts[flavors[i]]++;
    }

    double C_base = 20.0;
    long long d_sq_sum = 0;
    for(int i = 1; i <= 3; ++i) {
        d_sq_sum += (long long)flavor_counts[i] * flavor_counts[i];
    }
    double C = (d_sq_sum > 0) ? (C_base / d_sq_sum) : 0;

    GameState state;

    for (int t = 1; t <= 100; ++t) {
        int p;
        std::cin >> p;
        place_candy(state, flavors[t - 1], p);

        if (t == 100) {
            break;
        }

        char best_move = 'F';
        double max_eval = -1e18;
        
        std::map<int, std::map<char, int>> costs;
        const char DIRS[] = {'F', 'B', 'L', 'R'};
        for (int f = 1; f <= 3; ++f) {
            for (char dir : DIRS) {
                int current_cost = 0;
                for (int i = 0; i < N; ++i) {
                    for (int j = 0; j < N; ++j) {
                        if (state.grid[i][j] == f) {
                            if (dir == 'F') current_cost += i;
                            else if (dir == 'B') current_cost += (N - 1 - i);
                            else if (dir == 'L') current_cost += j;
                            else if (dir == 'R') current_cost += (N - 1 - j);
                        }
                    }
                }
                costs[f][dir] = current_cost;
            }
        }

        std::vector<char> p_dirs = {'F', 'B', 'L', 'R'};
        std::sort(p_dirs.begin(), p_dirs.end());
        long long min_total_cost = -1;
        std::map<int, char> best_homes;

        do {
            long long current_total_cost = (long long)costs[1][p_dirs[0]] + costs[2][p_dirs[1]] + costs[3][p_dirs[2]];
            if (min_total_cost == -1 || current_total_cost < min_total_cost) {
                min_total_cost = current_total_cost;
                best_homes[1] = p_dirs[0];
                best_homes[2] = p_dirs[1];
                best_homes[3] = p_dirs[2];
            }
        } while (std::next_permutation(p_dirs.begin(), p_dirs.end()));

        for (char dir : DIRS) {
            GameState temp_state = state;
            temp_state.tilt(dir);
            long long score = temp_state.calculate_score();
            
            long long penalty = 0;
            for (int i = 0; i < N; ++i) {
                for (int j = 0; j < N; ++j) {
                    int f = temp_state.grid[i][j];
                    if (f > 0) {
                        char home_dir = best_homes[f];
                        if (home_dir == 'F') penalty += i;
                        else if (home_dir == 'B') penalty += (N - 1 - i);
                        else if (home_dir == 'L') penalty += j;
                        else if (home_dir == 'R') penalty += (N - 1 - j);
                    }
                }
            }
            
            double eval = (double)score - C * (101 - t) * penalty;

            if (eval > max_eval) {
                max_eval = eval;
                best_move = dir;
            }
        }

        std::cout << best_move << std::endl;
        state.tilt(best_move);
    }

    return 0;
}