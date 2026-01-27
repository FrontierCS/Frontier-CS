#include <iostream>
#include <vector>
#include <string>
#include <set>
#include <map>
#include <algorithm>
#include <tuple>

using namespace std;

int R, C;
vector<string> grid;
int dists[100][100][4];
int dr[] = {-1, 0, 1, 0}; // N, E, S, W
int dc[] = {0, 1, 0, -1};

struct State {
    int r, c, dir;

    bool operator<(const State& other) const {
        if (r != other.r) return r < other.r;
        if (c != other.c) return c < other.c;
        return dir < other.dir;
    }
};

void precompute_dists() {
    for (int i = 0; i < R; ++i) {
        for (int j = 0; j < C; ++j) {
            if (grid[i][j] == '#') continue;
            for (int k = 0; k < 4; ++k) {
                int d = 0;
                int cr = i + dr[k];
                int cc = j + dc[k];
                while (cr >= 0 && cr < R && cc >= 0 && cc < C && grid[cr][cc] == '.') {
                    d++;
                    cr += dr[k];
                    cc += dc[k];
                }
                dists[i][j][k] = d;
            }
        }
    }
}

State apply_action(State s, const string& action) {
    if (action == "left") {
        s.dir = (s.dir + 3) % 4;
    } else if (action == "right") {
        s.dir = (s.dir + 1) % 4;
    } else if (action == "step") {
        s.r += dr[s.dir];
        s.c += dc[s.dir];
    }
    return s;
}

bool is_safe_to_step(const vector<State>& possible_states) {
    if (possible_states.empty()) return false;
    for (const auto& s : possible_states) {
        if (dists[s.r][s.c][s.dir] == 0) {
            return false;
        }
    }
    return true;
}

// For "no" case
vector<State> all_initial_states;
vector<int> partitions;
int wall_state_idx;

State state_from_idx(int idx) {
    if (idx == wall_state_idx) return {-1, -1, -1};
    return all_initial_states[idx];
}

int idx_from_state(const State& s) {
    if (s.r < 0) return wall_state_idx;
    auto it = lower_bound(all_initial_states.begin(), all_initial_states.end(), s);
    return distance(all_initial_states.begin(), it);
}

void precompute_partitions() {
    for (int i = 0; i < R; ++i) {
        for (int j = 0; j < C; ++j) {
            if (grid[i][j] == '.') {
                for (int d = 0; d < 4; ++d) {
                    all_initial_states.push_back({i, j, d});
                }
            }
        }
    }
    sort(all_initial_states.begin(), all_initial_states.end());
    
    int num_states = all_initial_states.size();
    if (num_states == 0) return;
    wall_state_idx = num_states;
    partitions.resize(num_states + 1);

    map<int, int> dist_to_part;
    int next_part_id = 0;
    for (int i = 0; i < num_states; ++i) {
        State s = all_initial_states[i];
        int d = dists[s.r][s.c][s.dir];
        if (dist_to_part.find(d) == dist_to_part.end()) {
            dist_to_part[d] = next_part_id++;
        }
        partitions[i] = dist_to_part[d];
    }
    partitions[wall_state_idx] = next_part_id++;

    while (true) {
        bool changed = false;
        map<vector<int>, int> sig_to_part;
        vector<int> new_partitions(num_states + 1);
        int current_part_id = 0;

        for (int i = 0; i < num_states; ++i) {
            State s = all_initial_states[i];
            vector<int> signature;
            signature.push_back(partitions[i]);

            State s_left = apply_action(s, "left");
            signature.push_back(partitions[idx_from_state(s_left)]);
            
            State s_right = apply_action(s, "right");
            signature.push_back(partitions[idx_from_state(s_right)]);

            if (dists[s.r][s.c][s.dir] > 0) {
                State s_step = apply_action(s, "step");
                signature.push_back(partitions[idx_from_state(s_step)]);
            } else {
                signature.push_back(partitions[wall_state_idx]);
            }

            if (sig_to_part.find(signature) == sig_to_part.end()) {
                sig_to_part[signature] = current_part_id++;
            }
            new_partitions[i] = sig_to_part[signature];
        }
        new_partitions[wall_state_idx] = current_part_id++;

        if (current_part_id > next_part_id) {
            partitions = new_partitions;
            next_part_id = current_part_id;
            changed = true;
        }

        if (!changed) break;
    }
}

bool are_positions_indistinguishable(int r1, int c1, int r2, int c2) {
    vector<int> p1_parts, p2_parts;
    for(int d=0; d<4; ++d) {
        p1_parts.push_back(partitions[idx_from_state({r1, c1, d})]);
        p2_parts.push_back(partitions[idx_from_state({r2, c2, d})]);
    }
    sort(p1_parts.begin(), p1_parts.end());
    sort(p2_parts.begin(), p2_parts.end());
    return p1_parts == p2_parts;
}


int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    cin >> R >> C;
    grid.resize(R);
    for (int i = 0; i < R; ++i) {
        cin >> grid[i];
    }

    precompute_dists();
    precompute_partitions();

    vector<State> possible_states;
    for (int i = 0; i < R; ++i) {
        for (int j = 0; j < C; ++j) {
            if (grid[i][j] == '.') {
                for (int k = 0; k < 4; ++k) {
                    possible_states.push_back({i, j, k});
                }
            }
        }
    }
    
    int rounds = 0;

    while (true) {
        int d;
        cin >> d;
        if (d == -1) break;

        vector<State> next_possible_states;
        for (const auto& s : possible_states) {
            if (dists[s.r][s.c][s.dir] == d) {
                next_possible_states.push_back(s);
            }
        }
        possible_states = next_possible_states;

        set<pair<int, int>> possible_positions;
        if (!possible_states.empty()){
            for (const auto& s : possible_states) {
                possible_positions.insert({s.r, s.c});
            }
        }

        if (possible_positions.size() == 1) {
            auto pos = *possible_positions.begin();
            cout << "yes " << pos.first + 1 << " " << pos.second + 1 << endl;
            break;
        }

        if (possible_positions.size() > 1) {
            bool impossible = true;
            vector<pair<int,int>> pos_vec(possible_positions.begin(), possible_positions.end());
            for(size_t i = 0; i < pos_vec.size(); ++i) {
                for(size_t j = i + 1; j < pos_vec.size(); ++j) {
                    if (!are_positions_indistinguishable(pos_vec[i].first, pos_vec[i].second, pos_vec[j].first, pos_vec[j].second)) {
                        impossible = false;
                        break;
                    }
                }
                if (!impossible) break;
            }
            if (impossible) {
                cout << "no" << endl;
                break;
            }
        }
        
        rounds++;
        if (rounds > 4 * R * C + 5) {
            cout << "no" << endl;
            break;
        }

        string best_action = "left";
        tuple<int, long long> best_score = {1e9, 1e18};

        vector<string> actions_to_consider;
        actions_to_consider.push_back("left");
        actions_to_consider.push_back("right");
        if (is_safe_to_step(possible_states)) {
            actions_to_consider.push_back("step");
        }
        
        map<string, int> pref = {{"step", 0}, {"right", 1}, {"left", 2}};

        for (const auto& action : actions_to_consider) {
            map<int, vector<State>> groups;
            for (const auto& s : possible_states) {
                State next_s = apply_action(s, action);
                groups[dists[next_s.r][next_s.c][next_s.dir]].push_back(next_s);
            }

            int worst_case_size = 0;
            long long sum_sq = 0;
            for (const auto& p : groups) {
                worst_case_size = max(worst_case_size, (int)p.second.size());
                sum_sq += (long long)p.second.size() * p.second.size();
            }

            tuple<int, long long> current_score = {worst_case_size, sum_sq};
            
            if (current_score < best_score) {
                best_score = current_score;
                best_action = action;
            } else if (current_score == best_score) {
                if (pref.count(action) && pref.count(best_action) && pref[action] < pref[best_action]) {
                    best_action = action;
                }
            }
        }

        cout << best_action << endl;
        
        vector<State> temp_states;
        for (const auto& s : possible_states) {
            temp_states.push_back(apply_action(s, best_action));
        }
        possible_states = temp_states;
    }

    return 0;
}