#include <iostream>
#include <vector>
#include <string>
#include <set>
#include <map>
#include <algorithm>
#include <tuple>
#include <vector>

using namespace std;

int R, C;
vector<vector<char>> grid;
int dist[100][100][4];

// N, E, S, W
int dr[] = {-1, 0, 1, 0};
int dc[] = {0, 1, 0, -1};

struct State {
    int r, c, dir;

    bool operator<(const State& other) const {
        return tie(r, c, dir) < tie(other.r, other.c, other.dir);
    }
};

bool is_valid_pos(int r, int c) {
    return r >= 0 && r < R && c >= 0 && c < C && grid[r][c] == '.';
}

State apply_action(const State& s, const string& action) {
    if (action == "left") {
        return {s.r, s.c, (s.dir + 3) % 4};
    }
    if (action == "right") {
        return {s.r, s.c, (s.dir + 1) % 4};
    }
    if (action == "step") {
        return {s.r + dr[s.dir], s.c + dc[s.dir], s.dir};
    }
    return {-1, -1, -1};
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    cin >> R >> C;
    grid.assign(R, vector<char>(C));
    vector<pair<int, int>> open_squares;
    for (int i = 0; i < R; ++i) {
        for (int j = 0; j < C; ++j) {
            cin >> grid[i][j];
            if (grid[i][j] == '.') {
                open_squares.push_back({i, j});
            }
        }
    }

    // Precompute distances
    for (const auto& p : open_squares) {
        int r = p.first;
        int c = p.second;
        for (int dir = 0; dir < 4; ++dir) {
            int d = 0;
            int nr = r + dr[dir];
            int nc = c + dc[dir];
            while (is_valid_pos(nr, nc)) {
                d++;
                nr += dr[dir];
                nc += dc[dir];
            }
            dist[r][c][dir] = d;
        }
    }

    // Bisimulation precomputation
    vector<State> all_states;
    map<State, int> state_to_idx;
    int state_idx_counter = 0;
    for (const auto& p : open_squares) {
        for (int dir = 0; dir < 4; ++dir) {
            State s = {p.first, p.second, dir};
            all_states.push_back(s);
            state_to_idx[s] = state_idx_counter++;
        }
    }
    int num_total_states = all_states.size();
    if (num_total_states == 0) return 0;
    
    vector<int> eq_class(num_total_states);

    // Initial partition based on distance
    map<int, int> dist_to_class;
    int num_classes = 0;
    for (int i = 0; i < num_total_states; ++i) {
        State s = all_states[i];
        int d = dist[s.r][s.c][s.dir];
        if (dist_to_class.find(d) == dist_to_class.end()) {
            dist_to_class[d] = num_classes++;
        }
        eq_class[i] = dist_to_class[d];
    }
    
    // Partition refinement
    while (true) {
        map<tuple<int, int, int, int>, int> signature_to_new_class;
        int new_num_classes = 0;
        vector<int> new_eq_class(num_total_states);

        for (int i = 0; i < num_total_states; ++i) {
            State s = all_states[i];
            
            int current_c = eq_class[i];
            
            State next_left = apply_action(s, "left");
            int left_c = eq_class[state_to_idx[next_left]];

            State next_right = apply_action(s, "right");
            int right_c = eq_class[state_to_idx[next_right]];

            int step_c = -1;
            if (dist[s.r][s.c][s.dir] > 0) {
                State next_step = apply_action(s, "step");
                step_c = eq_class[state_to_idx[next_step]];
            }

            tuple<int, int, int, int> signature = {current_c, left_c, right_c, step_c};

            if (signature_to_new_class.find(signature) == signature_to_new_class.end()) {
                signature_to_new_class[signature] = new_num_classes++;
            }
            new_eq_class[i] = signature_to_new_class[signature];
        }

        if (new_num_classes == num_classes) {
            break;
        }
        eq_class = new_eq_class;
        num_classes = new_num_classes;
    }

    // Interaction
    vector<State> possible_states = all_states;

    while (true) {
        int d;
        cin >> d;
        if (d == -1) {
            break;
        }

        // Filter states
        vector<State> next_possible_states;
        for (const auto& s : possible_states) {
            if (dist[s.r][s.c][s.dir] == d) {
                next_possible_states.push_back(s);
            }
        }
        possible_states = next_possible_states;

        // Check for solution
        set<pair<int, int>> possible_positions;
        for (const auto& s : possible_states) {
            possible_positions.insert({s.r, s.c});
        }

        if (possible_positions.size() == 1) {
            auto pos = *possible_positions.begin();
            cout << "yes " << pos.first + 1 << " " << pos.second + 1 << endl;
            cout.flush();
            return 0;
        }

        // Check for impossibility
        if (possible_positions.size() > 1) {
            map<pair<int, int>, map<int, int>> pos_signatures;
            for (const auto& s : possible_states) {
                pos_signatures[{s.r, s.c}][eq_class[state_to_idx[s]]]++;
            }
            
            bool all_same = true;
            auto it = pos_signatures.begin();
            auto const& first_sig = it->second;
            it++;
            for (; it != pos_signatures.end(); ++it) {
                if (it->second != first_sig) {
                    all_same = false;
                    break;
                }
            }
            if (all_same) {
                cout << "no" << endl;
                cout.flush();
                return 0;
            }
        }

        // Choose best action
        string best_action = "";
        pair<int, int> best_score = {1000000000, 1000000000};
        vector<string> actions = {"left", "right"};

        if (possible_states.empty()) {
             cout << "no" << endl; cout.flush(); return 0;
        }
        bool can_step = true;
        for (const auto& s : possible_states) {
            if (dist[s.r][s.c][s.dir] == 0) {
                can_step = false;
                break;
            }
        }
        if (can_step) {
            actions.push_back("step");
        }

        for (const auto& action : actions) {
            map<int, vector<State>> partitions;
            for (const auto& s : possible_states) {
                State next_s = apply_action(s, action);
                int observed_d = dist[next_s.r][next_s.c][next_s.dir];
                partitions[observed_d].push_back(s);
            }

            int max_pos_count = 0;
            int max_state_count = 0;
            for (auto const& [obs_d, states_in_partition] : partitions) {
                set<pair<int, int>> positions_in_partition;
                for (const auto& s : states_in_partition) {
                    positions_in_partition.insert({s.r, s.c});
                }
                if ((int)positions_in_partition.size() > max_pos_count) {
                    max_pos_count = positions_in_partition.size();
                }
                if ((int)states_in_partition.size() > max_state_count) {
                    max_state_count = states_in_partition.size();
                }
            }
            
            pair<int, int> current_score = {max_pos_count, max_state_count};
            if (current_score < best_score) {
                best_score = current_score;
                best_action = action;
            } else if (current_score == best_score) {
                if (action < best_action) {
                    best_action = action;
                }
            }
        }
        if (best_action.empty() && !actions.empty()) {
            best_action = actions[0];
        }

        cout << best_action << endl;
        cout.flush();
    }

    return 0;
}