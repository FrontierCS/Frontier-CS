#include <iostream>
#include <vector>
#include <string>
#include <tuple>
#include <set>
#include <map>
#include <algorithm>
#include <functional>

using namespace std;

int R, C;
vector<string> grid;
int dist[100][100][4];
int dr[] = {-1, 0, 1, 0}; // N, E, S, W
int dc[] = {0, 1, 0, -1};

int state_to_idx(int r, int c, int dir) {
    return r * C * 4 + c * 4 + dir;
}

tuple<int, int, int> idx_to_state(int idx) {
    int dir = idx % 4;
    idx /= 4;
    int c = idx % C;
    int r = idx / C;
    return {r, c, dir};
}

void precompute_dist() {
    for (int j = 0; j < C; ++j) {
        int last_wall = -1;
        for (int i = 0; i < R; ++i) {
            if (grid[i][j] == '#') {
                last_wall = i;
            } else {
                dist[i][j][0] = i - last_wall - 1;
            }
        }
        last_wall = R;
        for (int i = R - 1; i >= 0; --i) {
            if (grid[i][j] == '#') {
                last_wall = i;
            } else {
                dist[i][j][2] = last_wall - i - 1;
            }
        }
    }
    for (int i = 0; i < R; ++i) {
        int last_wall = -1;
        for (int j = 0; j < C; ++j) {
            if (grid[i][j] == '#') {
                last_wall = j;
            } else {
                dist[i][j][3] = j - last_wall - 1;
            }
        }
        last_wall = C;
        for (int j = C - 1; j >= 0; --j) {
            if (grid[i][j] == '#') {
                last_wall = j;
            } else {
                dist[i][j][1] = last_wall - j - 1;
            }
        }
    }
}

bool check_impossible() {
    int total_states = R * C * 4;
    int wall_state_idx = total_states;

    vector<bool> is_valid(total_states, false);
    for (int r = 0; r < R; ++r) {
        for (int c = 0; c < C; ++c) {
            if (grid[r][c] == '.') {
                for (int dir = 0; dir < 4; ++dir) {
                    is_valid[state_to_idx(r, c, dir)] = true;
                }
            }
        }
    }

    auto get_next_state = [&](int idx, int action) {
        if (idx == wall_state_idx) return wall_state_idx;
        auto [r, c, dir] = idx_to_state(idx);
        if (action == 0) { // left
            return state_to_idx(r, c, (dir + 3) % 4);
        }
        if (action == 1) { // right
            return state_to_idx(r, c, (dir + 1) % 4);
        }
        // step
        int nr = r + dr[dir];
        int nc = c + dc[dir];
        if (nr < 0 || nr >= R || nc < 0 || nc >= C || grid[nr][nc] == '#') {
            return wall_state_idx;
        }
        return state_to_idx(nr, nc, dir);
    };

    vector<int> eq_class(total_states + 1);
    map<int, int> dist_to_class;
    int num_classes = 0;
    
    eq_class[wall_state_idx] = num_classes++;

    for (int i = 0; i < total_states; ++i) {
        if (is_valid[i]) {
            auto [r, c, dir] = idx_to_state(i);
            int d = dist[r][c][dir];
            if (dist_to_class.find(d) == dist_to_class.end()) {
                dist_to_class[d] = num_classes++;
            }
            eq_class[i] = dist_to_class[d];
        }
    }

    bool changed = true;
    while (changed) {
        map<tuple<int, int, int, int>, int> new_class_map;
        int next_new_class_id = 0;
        vector<int> next_eq_class = eq_class;

        auto get_key = [&](int i) {
            if (i == wall_state_idx) {
                int c = eq_class[wall_state_idx];
                return make_tuple(c, c, c, c);
            }
            int c_old = eq_class[i];
            int c_left = eq_class[get_next_state(i, 0)];
            int c_right = eq_class[get_next_state(i, 1)];
            int c_step = eq_class[get_next_state(i, 2)];
            return make_tuple(c_old, c_left, c_right, c_step);
        };

        for (int i = 0; i < total_states; ++i) {
            if (is_valid[i]) {
                auto key = get_key(i);
                if (new_class_map.find(key) == new_class_map.end()) {
                    new_class_map[key] = next_new_class_id++;
                }
                next_eq_class[i] = new_class_map[key];
            }
        }
        auto wall_key = get_key(wall_state_idx);
        if (new_class_map.find(wall_key) == new_class_map.end()) {
            new_class_map[wall_key] = next_new_class_id++;
        }
        next_eq_class[wall_state_idx] = new_class_map[wall_key];
        
        if (next_new_class_id > num_classes) {
            changed = true;
            num_classes = next_new_class_id;
            eq_class = next_eq_class;
        } else {
            changed = false;
        }
    }

    map<int, set<pair<int, int>>> class_to_pos;
    for (int i = 0; i < total_states; ++i) {
        if (is_valid[i]) {
            auto [r, c, dir] = idx_to_state(i);
            class_to_pos[eq_class[i]].insert({r, c});
        }
    }

    for (auto const& [cl, pos_set] : class_to_pos) {
        if (pos_set.size() > 1) {
            return true;
        }
    }

    return false;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    cin >> R >> C;
    grid.resize(R);
    vector<pair<int, int>> open_squares;
    for (int i = 0; i < R; ++i) {
        cin >> grid[i];
        for (int j = 0; j < C; ++j) {
            if (grid[i][j] == '.') {
                open_squares.push_back({i, j});
            }
        }
    }

    precompute_dist();
    if (check_impossible()) {
        cout << "no" << endl;
        return 0;
    }

    vector<tuple<int, int, int>> S;
    for (auto p : open_squares) {
        for (int dir = 0; dir < 4; ++dir) {
            S.emplace_back(p.first, p.second, dir);
        }
    }

    while (true) {
        int d;
        cin >> d;
        if (d == -1) break;

        vector<tuple<int, int, int>> next_S;
        for (const auto& state : S) {
            auto [r, c, dir] = state;
            if (dist[r][c][dir] == d) {
                next_S.push_back(state);
            }
        }
        S = next_S;

        set<pair<int, int>> P;
        for (const auto& state : S) {
            P.insert({get<0>(state), get<1>(state)});
        }

        if (P.size() == 1) {
            cout << "yes " << P.begin()->first + 1 << " " << P.begin()->second + 1 << endl;
            break;
        }

        tuple<int, int, int> best_score = {1000000000, 0, 10};
        string best_action = "";

        // Try left
        map<int, vector<tuple<int, int, int>>> partitions_left;
        for (const auto& state : S) {
            auto [r, c, dir] = state;
            int new_dir = (dir + 3) % 4;
            partitions_left[dist[r][c][new_dir]].emplace_back(r, c, new_dir);
        }
        int max_pos_count_left = 0;
        for (auto const& [obs, states] : partitions_left) {
            set<pair<int, int>> p_set;
            for (const auto& st : states) p_set.insert({get<0>(st), get<1>(st)});
            if ((int)p_set.size() > max_pos_count_left) max_pos_count_left = p_set.size();
        }
        tuple<int, int, int> score_left = {max_pos_count_left, -(int)partitions_left.size(), 1};
        if (score_left < best_score) {
            best_score = score_left;
            best_action = "left";
        }

        // Try right
        map<int, vector<tuple<int, int, int>>> partitions_right;
        for (const auto& state : S) {
            auto [r, c, dir] = state;
            int new_dir = (dir + 1) % 4;
            partitions_right[dist[r][c][new_dir]].emplace_back(r, c, new_dir);
        }
        int max_pos_count_right = 0;
        for (auto const& [obs, states] : partitions_right) {
            set<pair<int, int>> p_set;
            for (const auto& st : states) p_set.insert({get<0>(st), get<1>(st)});
            if ((int)p_set.size() > max_pos_count_right) max_pos_count_right = p_set.size();
        }
        tuple<int, int, int> score_right = {max_pos_count_right, -(int)partitions_right.size(), 2};
        if (score_right < best_score) {
            best_score = score_right;
            best_action = "right";
        }

        // Try step
        bool can_step = true;
        for (const auto& state : S) {
            auto [r, c, dir] = state;
            int nr = r + dr[dir];
            int nc = c + dc[dir];
            if (nr < 0 || nr >= R || nc < 0 || nc >= C || grid[nr][nc] == '#') {
                can_step = false;
                break;
            }
        }

        if (can_step) {
            map<int, vector<tuple<int, int, int>>> partitions_step;
            for (const auto& state : S) {
                auto [r, c, dir] = state;
                int nr = r + dr[dir];
                int nc = c + dc[dir];
                partitions_step[dist[nr][nc][dir]].emplace_back(nr, nc, dir);
            }
            int max_pos_count_step = 0;
            for (auto const& [obs, states] : partitions_step) {
                set<pair<int, int>> p_set;
                for (const auto& st : states) p_set.insert({get<0>(st), get<1>(st)});
                if ((int)p_set.size() > max_pos_count_step) max_pos_count_step = p_set.size();
            }
            tuple<int, int, int> score_step = {max_pos_count_step, -(int)partitions_step.size(), 0};
            if (score_step < best_score) {
                best_score = score_step;
                best_action = "step";
            }
        }
        
        cout << best_action << endl;

        next_S.clear();
        if (best_action == "left") {
            for (const auto& state : S) {
                auto [r, c, dir] = state;
                next_S.emplace_back(r, c, (dir + 3) % 4);
            }
        } else if (best_action == "right") {
            for (const auto& state : S) {
                auto [r, c, dir] = state;
                next_S.emplace_back(r, c, (dir + 1) % 4);
            }
        } else { // step
            for (const auto& state : S) {
                auto [r, c, dir] = state;
                next_S.emplace_back(r + dr[dir], c + dc[dir], dir);
            }
        }
        S = next_S;
    }

    return 0;
}