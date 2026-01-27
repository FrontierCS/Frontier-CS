#include <iostream>
#include <vector>
#include <string>
#include <tuple>
#include <set>
#include <map>
#include <algorithm>
#include <functional>

void solve() {
    int r, c;
    std::cin >> r >> c;
    std::vector<std::string> grid(r);
    for (int i = 0; i < r; ++i) {
        std::cin >> grid[i];
    }

    int dist[100][100][4];
    int di[] = {-1, 0, 1, 0}; // N, E, S, W
    int dj[] = {0, 1, 0, -1};

    for (int i = 0; i < r; ++i) {
        for (int j = 0; j < c; ++j) {
            if (grid[i][j] == '#') continue;
            for (int k = 0; k < 4; ++k) {
                int d_val = 0;
                int ni = i + di[k];
                int nj = j + dj[k];
                while (ni >= 0 && ni < r && nj >= 0 && nj < c && grid[ni][nj] == '.') {
                    d_val++;
                    ni += di[k];
                    nj += dj[k];
                }
                dist[i][j][k] = d_val;
            }
        }
    }

    std::vector<std::tuple<int, int, int>> possible_states;
    for (int i = 0; i < r; ++i) {
        for (int j = 0; j < c; ++j) {
            if (grid[i][j] == '.') {
                for (int k = 0; k < 4; ++k) {
                    possible_states.emplace_back(i, j, k);
                }
            }
        }
    }

    int d;
    while (std::cin >> d && d != -1) {
        std::vector<std::tuple<int, int, int>> next_possible_states;
        for (const auto& state : possible_states) {
            if (dist[std::get<0>(state)][std::get<1>(state)][std::get<2>(state)] == d) {
                next_possible_states.push_back(state);
            }
        }
        possible_states = next_possible_states;

        std::set<std::pair<int, int>> possible_positions;
        for (const auto& state : possible_states) {
            possible_positions.insert({std::get<0>(state), std::get<1>(state)});
        }
        if (possible_positions.size() == 1) {
            auto [fr, fc] = *possible_positions.begin();
            std::cout << "yes " << fr + 1 << " " << fc + 1 << std::endl;
            return;
        }
        
        if (possible_positions.empty()) {
            std::cout << "no" << std::endl;
            return;
        }


        bool stuck = true;
        if (possible_positions.size() > 1) {
            std::set<int> outcomes_left;
            for (const auto& state : possible_states) {
                auto [cr, cc, cdir] = state;
                int ndir = (cdir + 3) % 4;
                outcomes_left.insert(dist[cr][cc][ndir]);
            }
            if (outcomes_left.size() > 1) stuck = false;
            
            if (stuck) {
                std::set<int> outcomes_right;
                for (const auto& state : possible_states) {
                    auto [cr, cc, cdir] = state;
                    int ndir = (cdir + 1) % 4;
                    outcomes_right.insert(dist[cr][cc][ndir]);
                }
                if (outcomes_right.size() > 1) stuck = false;
            }

            if (stuck && d > 0) {
                std::set<int> outcomes_step;
                for (const auto& state : possible_states) {
                    auto [cr, cc, cdir] = state;
                    int nr = cr + di[cdir];
                    int nc = cc + dj[cdir];
                    outcomes_step.insert(dist[nr][nc][cdir]);
                }
                if (outcomes_step.size() > 1) stuck = false;
            }
        } else {
            stuck = false;
        }

        if (stuck) {
            std::cout << "no" << std::endl;
            return;
        }

        std::vector<std::tuple<std::pair<int, int>, int, std::string>> action_scores;

        std::map<int, std::vector<std::tuple<int, int, int>>> outcomes_left_map;
        for (const auto& state : possible_states) {
            auto [cr, cc, cdir] = state;
            int ndir = (cdir + 3) % 4;
            outcomes_left_map[dist[cr][cc][ndir]].emplace_back(cr, cc, ndir);
        }
        int worst_size_left = 0;
        for (auto const& [dist_val, states] : outcomes_left_map) {
            std::set<std::pair<int, int>> positions;
            for (const auto& state : states) {
                positions.insert({std::get<0>(state), std::get<1>(state)});
            }
            worst_size_left = std::max(worst_size_left, (int)positions.size());
        }
        action_scores.emplace_back(std::make_pair(worst_size_left, -(int)outcomes_left_map.size()), -1, "left");

        std::map<int, std::vector<std::tuple<int, int, int>>> outcomes_right_map;
        for (const auto& state : possible_states) {
            auto [cr, cc, cdir] = state;
            int ndir = (cdir + 1) % 4;
            outcomes_right_map[dist[cr][cc][ndir]].emplace_back(cr, cc, ndir);
        }
        int worst_size_right = 0;
        for (auto const& [dist_val, states] : outcomes_right_map) {
            std::set<std::pair<int, int>> positions;
            for (const auto& state : states) {
                positions.insert({std::get<0>(state), std::get<1>(state)});
            }
            worst_size_right = std::max(worst_size_right, (int)positions.size());
        }
        action_scores.emplace_back(std::make_pair(worst_size_right, -(int)outcomes_right_map.size()), 0, "right");

        if (d > 0) {
            std::map<int, std::vector<std::tuple<int, int, int>>> outcomes_step_map;
            for (const auto& state : possible_states) {
                auto [cr, cc, cdir] = state;
                int nr = cr + di[cdir];
                int nc = cc + dj[cdir];
                outcomes_step_map[dist[nr][nc][cdir]].emplace_back(nr, nc, cdir);
            }
            int worst_size_step = 0;
            for (auto const& [dist_val, states] : outcomes_step_map) {
                std::set<std::pair<int, int>> positions;
                for (const auto& state : states) {
                    positions.insert({std::get<0>(state), std::get<1>(state)});
                }
                worst_size_step = std::max(worst_size_step, (int)positions.size());
            }
            action_scores.emplace_back(std::make_pair(worst_size_step, -(int)outcomes_step_map.size()), -2, "step");
        }
        
        std::sort(action_scores.begin(), action_scores.end());
        std::string best_action_str = std::get<2>(action_scores[0]);

        std::cout << best_action_str << std::endl;

        std::vector<std::tuple<int, int, int>> temp_states;
        if (best_action_str == "left") {
            for (const auto& state : possible_states) {
                auto [cr, cc, cdir] = state;
                temp_states.emplace_back(cr, cc, (cdir + 3) % 4);
            }
        } else if (best_action_str == "right") {
            for (const auto& state : possible_states) {
                auto [cr, cc, cdir] = state;
                temp_states.emplace_back(cr, cc, (cdir + 1) % 4);
            }
        } else { // step
            for (const auto& state : possible_states) {
                auto [cr, cc, cdir] = state;
                temp_states.emplace_back(cr + di[cdir], cc + dj[cdir], cdir);
            }
        }
        possible_states = temp_states;
    }
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    solve();
    return 0;
}