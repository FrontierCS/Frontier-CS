#include <iostream>
#include <vector>
#include <string>
#include <numeric>
#include <algorithm>
#include <utility>

const int N = 10;

struct State {
    int grid[N][N];

    State() {
        for (int i = 0; i < N; ++i) {
            for (int j = 0; j < N; ++j) {
                grid[i][j] = 0;
            }
        }
    }
};

std::pair<int, int> p_to_coord(int p, const State& s) {
    int empty_count = 0;
    for (int r = 0; r < N; ++r) {
        for (int c = 0; c < N; ++c) {
            if (s.grid[r][c] == 0) {
                empty_count++;
                if (empty_count == p) {
                    return {r, c};
                }
            }
        }
    }
    return {-1, -1};
}

State simulate_tilt(const State& current_state, char dir) {
    State next_state = current_state;
    if (dir == 'F') {
        for (int c = 0; c < N; ++c) {
            int empty_r = 0;
            for (int r = 0; r < N; ++r) {
                if (next_state.grid[r][c] != 0) {
                    if (r != empty_r) {
                        next_state.grid[empty_r][c] = next_state.grid[r][c];
                        next_state.grid[r][c] = 0;
                    }
                    empty_r++;
                }
            }
        }
    } else if (dir == 'B') {
        for (int c = 0; c < N; ++c) {
            int empty_r = N - 1;
            for (int r = N - 1; r >= 0; --r) {
                if (next_state.grid[r][c] != 0) {
                    if (r != empty_r) {
                        next_state.grid[empty_r][c] = next_state.grid[r][c];
                        next_state.grid[r][c] = 0;
                    }
                    empty_r--;
                }
            }
        }
    } else if (dir == 'L') {
        for (int r = 0; r < N; ++r) {
            int empty_c = 0;
            for (int c = 0; c < N; ++c) {
                if (next_state.grid[r][c] != 0) {
                    if (c != empty_c) {
                        next_state.grid[r][empty_c] = next_state.grid[r][c];
                        next_state.grid[r][c] = 0;
                    }
                    empty_c++;
                }
            }
        }
    } else if (dir == 'R') {
        for (int r = 0; r < N; ++r) {
            int empty_c = N - 1;
            for (int c = N - 1; c >= 0; --c) {
                if (next_state.grid[r][c] != 0) {
                    if (c != empty_c) {
                        next_state.grid[r][empty_c] = next_state.grid[r][c];
                        next_state.grid[r][c] = 0;
                    }
                    empty_c--;
                }
            }
        }
    }
    return next_state;
}

const int dr[] = {-1, 1, 0, 0};
const int dc[] = {0, 0, -1, 1};

long long calculate_cluster_score(const State& s) {
    bool visited[N][N] = {false};
    long long total_score = 0;
    for (int r = 0; r < N; ++r) {
        for (int c = 0; c < N; ++c) {
            if (s.grid[r][c] != 0 && !visited[r][c]) {
                int flavor = s.grid[r][c];
                long long component_size = 0;
                std::vector<std::pair<int, int>> q;
                q.push_back({r, c});
                visited[r][c] = true;
                int head = 0;
                while(head < (int)q.size()){
                    auto [curr_r, curr_c] = q[head++];
                    component_size++;
                    for (int i = 0; i < 4; ++i) {
                        int nr = curr_r + dr[i];
                        int nc = curr_c + dc[i];
                        if (nr >= 0 && nr < N && nc >= 0 && nc < N && !visited[nr][nc] && s.grid[nr][nc] == flavor) {
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

int flavor_to_min_row[4], flavor_to_max_row[4];

long long calculate_target_score(const State& s) {
    long long dist = 0;
    for (int r = 0; r < N; ++r) {
        for (int c = 0; c < N; ++c) {
            if (s.grid[r][c] != 0) {
                int flavor = s.grid[r][c];
                int min_r = flavor_to_min_row[flavor];
                int max_r = flavor_to_max_row[flavor];
                if (r < min_r) dist += min_r - r;
                if (r > max_r) dist += r - max_r;
            }
        }
    }
    return -dist;
}

void setup_target_regions(const std::vector<int>& f) {
    std::vector<int> counts(4, 0);
    for (int flavor : f) {
        counts[flavor]++;
    }

    std::vector<std::pair<int, int>> flavor_counts;
    for (int i = 1; i <= 3; ++i) {
        flavor_counts.push_back({counts[i], i});
    }
    std::sort(flavor_counts.rbegin(), flavor_counts.rend());

    int flavor_a = flavor_counts[0].second, count_a = flavor_counts[0].first;
    int flavor_b = flavor_counts[1].second, count_b = flavor_counts[1].first;
    int flavor_c = flavor_counts[2].second, count_c = flavor_counts[2].first;
    
    int ordered_flavors[] = {flavor_a, flavor_c, flavor_b};
    int ordered_counts[] = {count_a, count_c, count_b};

    std::vector<int> rows_per_flavor(3);
    int total_base_rows = 0;
    for(int i = 0; i < 3; ++i) {
        rows_per_flavor[i] = ordered_counts[i] / N;
        total_base_rows += rows_per_flavor[i];
    }
    
    std::vector<std::pair<int, int>> remainders;
    for(int i = 0; i < 3; ++i) {
        remainders.push_back({ordered_counts[i] % N, i});
    }
    std::sort(remainders.rbegin(), remainders.rend());

    int rem_rows_to_distribute = N - total_base_rows;
    for(int i = 0; i < rem_rows_to_distribute; ++i) {
        rows_per_flavor[remainders[i].second]++;
    }
    
    int current_row = 0;
    for(int i = 0; i < 3; ++i) {
        int flav = ordered_flavors[i];
        int num_rows = rows_per_flavor[i];
        if (num_rows > 0) {
            flavor_to_min_row[flav] = current_row;
            flavor_to_max_row[flav] = current_row + num_rows - 1;
            current_row += num_rows;
        } else {
            flavor_to_min_row[flav] = -1; // Should not happen in this problem
            flavor_to_max_row[flav] = -1;
        }
    }
}


int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    std::vector<int> f(100);
    for (int i = 0; i < 100; ++i) {
        std::cin >> f[i];
    }
    
    setup_target_regions(f);

    State current_state;

    for (int t = 0; t < 100; ++t) {
        int p;
        std::cin >> p;

        auto [r, c] = p_to_coord(p, current_state);
        current_state.grid[r][c] = f[t];

        char best_dir = 'F';
        long long max_cluster_score = -1;
        long long max_target_score = -2e18; 

        const char dirs[] = {'F', 'B', 'L', 'R'};
        for (char dir : dirs) {
            State next_state = simulate_tilt(current_state, dir);
            long long cluster_score = calculate_cluster_score(next_state);
            
            if (cluster_score > max_cluster_score) {
                max_cluster_score = cluster_score;
                max_target_score = calculate_target_score(next_state);
                best_dir = dir;
            } else if (cluster_score == max_cluster_score) {
                long long target_score = calculate_target_score(next_state);
                if (target_score > max_target_score) {
                    max_target_score = target_score;
                    best_dir = dir;
                }
            }
        }
        
        std::cout << best_dir << std::endl;
        
        current_state = simulate_tilt(current_state, best_dir);
    }

    return 0;
}