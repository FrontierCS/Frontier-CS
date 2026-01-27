#include <iostream>
#include <vector>
#include <string>
#include <set>
#include <map>
#include <algorithm>
#include <tuple>

// Fast I/O
void fast_io() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
}

// Globals
int R, C;
std::vector<std::string> grid;
int dist[100][100][4];

// State representation and helpers
struct State {
    int r, c, d;
};
int dr[] = {-1, 0, 1, 0}; // N, E, S, W
int dc[] = {0, 1, 0, -1};

int state_to_idx(const State& s) {
    return s.d * R * C + s.r * C + s.c;
}

State idx_to_state(int idx) {
    int d = idx / (R * C);
    int rem = idx % (R * C);
    int r = rem / C;
    int c = rem % C;
    return {r, c, d};
}

State perform_action(const State& s, const std::string& action) {
    State next_s = s;
    if (action == "left") {
        next_s.d = (s.d + 3) % 4;
    } else if (action == "right") {
        next_s.d = (s.d + 1) % 4;
    } else if (action == "step") {
        next_s.r += dr[s.d];
        next_s.c += dc[s.d];
    }
    return next_s;
}

// Precomputation
void precompute_dist() {
    // North (d=0, i--)
    for (int j = 0; j < C; ++j) {
        int count = 0;
        for (int i = 0; i < R; ++i) {
            if (grid[i][j] == '#') {
                count = 0;
            } else {
                dist[i][j][0] = count;
                count++;
            }
        }
    }
    // South (d=2, i++)
    for (int j = 0; j < C; ++j) {
        int count = 0;
        for (int i = R - 1; i >= 0; --i) {
            if (grid[i][j] == '#') {
                count = 0;
            } else {
                dist[i][j][2] = count;
                count++;
            }
        }
    }
    // West (d=3, j--)
    for (int i = 0; i < R; ++i) {
        int count = 0;
        for (int j = 0; j < C; ++j) {
            if (grid[i][j] == '#') {
                count = 0;
            } else {
                dist[i][j][3] = count;
                count++;
            }
        }
    }
    // East (d=1, j++)
    for (int i = 0; i < R; ++i) {
        int count = 0;
        for (int j = C - 1; j >= 0; --j) {
            if (grid[i][j] == '#') {
                count = 0;
            } else {
                dist[i][j][1] = count;
                count++;
            }
        }
    }
}

// Equivalence classes
std::vector<int> equiv_class;
void compute_equiv_classes() {
    int num_total_states = 4 * R * C;
    equiv_class.resize(num_total_states);
    
    std::map<int, int> dist_to_part_id;
    int next_part_id = 0;
    
    for (int i = 0; i < R; ++i) {
        for (int j = 0; j < C; ++j) {
            for (int d = 0; d < 4; ++d) {
                int idx = state_to_idx({i, j, d});
                if (grid[i][j] == '#') {
                    equiv_class[idx] = -1;
                    continue;
                }
                int current_dist = dist[i][j][d];
                if (dist_to_part_id.find(current_dist) == dist_to_part_id.end()) {
                    dist_to_part_id[current_dist] = next_part_id++;
                }
                equiv_class[idx] = dist_to_part_id[current_dist];
            }
        }
    }

    int num_partitions = next_part_id;
    
    while (true) {
        std::vector<std::pair<std::tuple<int, int, int, int>, int>> signatures;
        for (int i = 0; i < num_total_states; ++i) {
            State s = idx_to_state(i);
            if (grid[s.r][s.c] == '#') continue;

            State s_l = perform_action(s, "left");
            State s_r = perform_action(s, "right");
            
            int part_s = equiv_class[i];
            int part_l = equiv_class[state_to_idx(s_l)];
            int part_r = equiv_class[state_to_idx(s_r)];
            int part_step = -1;
            if (dist[s.r][s.c][s.d] > 0) {
                State s_step = perform_action(s, "step");
                part_step = equiv_class[state_to_idx(s_step)];
            }
            signatures.push_back({std::make_tuple(part_s, part_l, part_r, part_step), i});
        }
        
        std::sort(signatures.begin(), signatures.end());
        
        std::vector<int> new_equiv_class(num_total_states, -1);
        int new_num_partitions = 0;
        if (!signatures.empty()) {
            new_equiv_class[signatures[0].second] = 0;
            for (size_t i = 1; i < signatures.size(); ++i) {
                if (signatures[i].first != signatures[i-1].first) {
                    new_num_partitions++;
                }
                new_equiv_class[signatures[i].second] = new_num_partitions;
            }
        }
        
        if (new_num_partitions + 1 == num_partitions) {
            break;
        }
        
        num_partitions = new_num_partitions + 1;
        equiv_class = new_equiv_class;
    }
}

// Main logic
int main() {
    fast_io();
    std::cin >> R >> C;
    grid.resize(R);
    std::vector<State> possible_states;
    for (int i = 0; i < R; ++i) {
        std::cin >> grid[i];
        for (int j = 0; j < C; ++j) {
            if (grid[i][j] == '.') {
                for (int d = 0; d < 4; ++d) {
                    possible_states.push_back({i, j, d});
                }
            }
        }
    }

    precompute_dist();
    compute_equiv_classes();

    int d_obs;
    std::cin >> d_obs;
    if (d_obs == -1) return 0;
    
    std::vector<State> next_possible_states;
    for (const auto& s : possible_states) {
        if (dist[s.r][s.c][s.d] == d_obs) {
            next_possible_states.push_back(s);
        }
    }
    possible_states = next_possible_states;

    int last_d_obs = d_obs;
    
    while(true) {
        std::set<std::pair<int, int>> positions;
        for (const auto& s : possible_states) {
            positions.insert({s.r, s.c});
        }
        
        if (positions.size() <= 1) {
            if (positions.empty()) {
                std::cout << "no" << std::endl;
            } else {
                auto pos = *positions.begin();
                std::cout << "yes " << pos.first + 1 << " " << pos.second + 1 << std::endl;
            }
            return 0;
        }
        
        std::set<int> eq_classes;
        for (const auto& s : possible_states) {
            eq_classes.insert(equiv_class[state_to_idx(s)]);
        }
        
        if (eq_classes.size() == 1) {
            std::cout << "no" << std::endl;
            return 0;
        }
        
        std::string best_action = "";
        int min_max_partition_size = possible_states.size() + 1;
        
        std::vector<std::string> actions = {"left", "right"};
        if (last_d_obs > 0) {
            actions.push_back("step");
        }
        
        for (const auto& action : actions) {
            std::map<int, int> counts;
            for (const auto& s : possible_states) {
                State next_s = perform_action(s, action);
                int next_dist = dist[next_s.r][next_s.c][next_s.d];
                counts[next_dist]++;
            }
            
            int max_size = 0;
            for(auto const& [dist, count] : counts) {
                max_size = std::max(max_size, count);
            }

            if (max_size < min_max_partition_size) {
                min_max_partition_size = max_size;
                best_action = action;
            }
        }
        
        std::cout << best_action << std::endl;
        
        std::cin >> d_obs;
        if (d_obs == -1) return 0;
        
        last_d_obs = d_obs;
        
        next_possible_states.clear();
        for (const auto& s : possible_states) {
            State next_s = perform_action(s, best_action);
            if (dist[next_s.r][next_s.c][next_s.d] == d_obs) {
                next_possible_states.push_back(next_s);
            }
        }
        possible_states = next_possible_states;
    }
    
    return 0;
}