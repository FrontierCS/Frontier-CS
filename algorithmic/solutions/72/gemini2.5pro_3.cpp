#include <iostream>
#include <vector>
#include <string>
#include <queue>
#include <map>
#include <set>
#include <algorithm>
#include <utility>

using namespace std;

struct Vehicle {
    int id;
    int r, c; // fixed coordinate (r for horizontal, c for vertical)
    int len;
    bool is_horizontal;
};

// State is represented by a vector of variable coordinates
using State = vector<int>;

vector<Vehicle> vehicles;
set<State> valid_states;

bool check_overlap(int k, const State& pos) {
    const auto& vk = vehicles[k];
    int rk, ck;
    if (vk.is_horizontal) {
        rk = vk.r;
        ck = pos[k];
    } else {
        rk = pos[k];
        ck = vk.c;
    }

    for (int i = 0; i < k; ++i) {
        const auto& vi = vehicles[i];
        int ri, ci;
        if (vi.is_horizontal) {
            ri = vi.r;
            ci = pos[i];
        } else {
            ri = pos[i];
            ci = vi.c;
        }

        if (vk.is_horizontal && vi.is_horizontal) {
            if (rk == ri && max(ck, ci) < min(ck + vk.len, ci + vi.len)) return true;
        } else if (!vk.is_horizontal && !vi.is_horizontal) {
            if (ck == ci && max(rk, ri) < min(rk + vk.len, ri + vi.len)) return true;
        } else if (vk.is_horizontal && !vi.is_horizontal) {
            if (ck <= ci && ci < ck + vk.len && ri <= rk && rk < ri + vi.len) return true;
        } else { // !vk.is_horizontal && vi.is_horizontal
            if (ci <= ck && ck < ci + vi.len && rk <= ri && ri < rk + vk.len) return true;
        }
    }
    return false;
}

void generate_states(int k, State& pos) {
    if (k == (int)vehicles.size()) {
        valid_states.insert(pos);
        return;
    }

    int max_pos = 6 - vehicles[k].len;
    for (int p = 0; p <= max_pos; ++p) {
        pos[k] = p;
        if (!check_overlap(k, pos)) {
            generate_states(k + 1, pos);
        }
    }
}

bool is_clear(const State& s) {
    bool grid[6][6] = {false};
    for (size_t i = 1; i < vehicles.size(); ++i) {
        const auto& v = vehicles[i];
        if (v.is_horizontal) {
            for (int j = 0; j < v.len; ++j) {
                grid[v.r][s[i] + j] = true;
            }
        } else {
            for (int j = 0; j < v.len; ++j) {
                grid[s[i] + j][v.c] = true;
            }
        }
    }

    int red_car_c = s[0];
    for (int c = red_car_c + 2; c < 6; ++c) {
        if (grid[2][c]) return false;
    }
    return true;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    map<int, vector<pair<int, int>>> vehicle_coords;
    for (int i = 0; i < 6; ++i) {
        for (int j = 0; j < 6; ++j) {
            int id;
            cin >> id;
            if (id > 0) {
                vehicle_coords[id].push_back({i, j});
            }
        }
    }

    for (auto const& [id, coords] : vehicle_coords) {
        Vehicle v;
        v.id = id;
        v.len = coords.size();
        int r_min = 6, c_min = 6;
        for (auto const& p : coords) {
            r_min = min(r_min, p.first);
            c_min = min(c_min, p.second);
        }
        v.is_horizontal = (coords.size() > 1 && coords[0].first == coords[1].first);
        if (v.is_horizontal) {
            v.r = r_min;
        } else {
            v.c = c_min;
        }
        vehicles.push_back(v);
    }
    sort(vehicles.begin(), vehicles.end(), [](const Vehicle& a, const Vehicle& b){
        return a.id < b.id;
    });

    State initial_state(vehicles.size());
    for (size_t i = 0; i < vehicles.size(); ++i) {
        int r_min = 6, c_min = 6;
        for (auto const& p : vehicle_coords[vehicles[i].id]) {
            r_min = min(r_min, p.first);
            c_min = min(c_min, p.second);
        }
        if (vehicles[i].is_horizontal) {
            initial_state[i] = c_min;
        } else {
            initial_state[i] = r_min;
        }
    }

    State current_pos(vehicles.size());
    generate_states(0, current_pos);

    map<State, int> moves_to_clear;
    queue<State> q;

    for (const auto& s : valid_states) {
        if (is_clear(s)) {
            moves_to_clear[s] = 0;
            q.push(s);
        }
    }

    while (!q.empty()) {
        State s = q.front();
        q.pop();

        for (size_t i = 0; i < vehicles.size(); ++i) {
            State next_s = s;
            next_s[i]++;
            int max_pos = 6 - vehicles[i].len;
            if (next_s[i] <= max_pos && valid_states.count(next_s) && moves_to_clear.find(next_s) == moves_to_clear.end()) {
                moves_to_clear[next_s] = moves_to_clear[s] + 1;
                q.push(next_s);
            }
            
            next_s = s;
            next_s[i]--;
            if (next_s[i] >= 0 && valid_states.count(next_s) && moves_to_clear.find(next_s) == moves_to_clear.end()) {
                moves_to_clear[next_s] = moves_to_clear[s] + 1;
                q.push(next_s);
            }
        }
    }

    map<State, vector<pair<int, char>>> paths;
    queue<State> q_fwd;

    paths[initial_state] = {};
    q_fwd.push(initial_state);

    int max_dist = -1;
    vector<pair<int, char>> best_path;

    if(moves_to_clear.count(initial_state)){
        max_dist = moves_to_clear[initial_state] + (6 - initial_state[0]);
        best_path = {};
    }


    while (!q_fwd.empty()) {
        State s = q_fwd.front();
        q_fwd.pop();
        
        if (moves_to_clear.count(s)) {
            int dist = moves_to_clear[s] + (6 - s[0]);
            if (dist > max_dist) {
                max_dist = dist;
                best_path = paths[s];
            }
        }

        for (size_t i = 0; i < vehicles.size(); ++i) {
            State next_s = s;
            next_s[i]++;
            int max_pos = 6 - vehicles[i].len;
            if (next_s[i] <= max_pos && valid_states.count(next_s) && paths.find(next_s) == paths.end()) {
                auto new_path = paths[s];
                char dir = vehicles[i].is_horizontal ? 'R' : 'D';
                new_path.push_back({vehicles[i].id, dir});
                paths[next_s] = new_path;
                q_fwd.push(next_s);
            }
            
            next_s = s;
            next_s[i]--;
            if (next_s[i] >= 0 && valid_states.count(next_s) && paths.find(next_s) == paths.end()) {
                auto new_path = paths[s];
                char dir = vehicles[i].is_horizontal ? 'L' : 'U';
                new_path.push_back({vehicles[i].id, dir});
                paths[next_s] = new_path;
                q_fwd.push(next_s);
            }
        }
    }
    
    cout << max_dist << " " << best_path.size() << endl;
    for (const auto& move : best_path) {
        cout << move.first << " " << move.second << endl;
    }

    return 0;
}