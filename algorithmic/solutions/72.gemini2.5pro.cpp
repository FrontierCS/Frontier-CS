#include <iostream>
#include <vector>
#include <string>
#include <unordered_map>
#include <queue>
#include <algorithm>
#include <map>

using namespace std;

// Vehicle properties
struct VehicleInfo {
    int id;
    int len;
    bool is_horiz;
    int fixed_coord;
};
vector<VehicleInfo> vehicle_infos;
int vehicle_count = 0;

// State representation and conversion
typedef unsigned long long State;

State encode(const vector<int>& s) {
    State res = 0;
    for (size_t i = 0; i < s.size(); ++i) {
        res |= (State)s[i] << (3 * i);
    }
    return res;
}

vector<int> decode(State s) {
    vector<int> res(vehicle_count);
    for (int i = 0; i < vehicle_count; ++i) {
        res[i] = (s >> (3 * i)) & 7;
    }
    return res;
}

unordered_map<State, int> state_to_id;
vector<State> id_to_state;

// Check for collision for a single vehicle placement during state generation
bool has_collision(int k, const vector<int>& s, const vector<vector<bool>>& occupied) {
    const auto& v_info = vehicle_infos[k];
    int r = v_info.is_horiz ? v_info.fixed_coord : s[k];
    int c = v_info.is_horiz ? s[k] : v_info.fixed_coord;
    for (int i = 0; i < v_info.len; ++i) {
        int cur_r = v_info.is_horiz ? r : r + i;
        int cur_c = v_info.is_horiz ? c + i : c;
        if (occupied[cur_r][cur_c]) {
            return true;
        }
    }
    return false;
}

void mark_occupied(int k, const vector<int>& s, vector<vector<bool>>& occupied, bool val) {
    const auto& v_info = vehicle_infos[k];
    int r = v_info.is_horiz ? v_info.fixed_coord : s[k];
    int c = v_info.is_horiz ? s[k] : v_info.fixed_coord;
    for (int i = 0; i < v_info.len; ++i) {
        int cur_r = v_info.is_horiz ? r : r + i;
        int cur_c = v_info.is_horiz ? c + i : c;
        occupied[cur_r][cur_c] = val;
    }
}

void generate_all_states(int k, vector<int>& current_state, vector<vector<bool>>& occupied) {
    if (k == vehicle_count) {
        State s_encoded = encode(current_state);
        if (state_to_id.find(s_encoded) == state_to_id.end()) {
            int new_id = id_to_state.size();
            state_to_id[s_encoded] = new_id;
            id_to_state.push_back(s_encoded);
        }
        return;
    }

    const auto& v_info = vehicle_infos[k];
    int limit = 6 - v_info.len;
    for (int i = 0; i <= limit; ++i) {
        current_state[k] = i;
        if (!has_collision(k, current_state, occupied)) {
            mark_occupied(k, current_state, occupied, true);
            generate_all_states(k + 1, current_state, occupied);
            mark_occupied(k, current_state, occupied, false);
        }
    }
}


int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    vector<vector<int>> board(6, vector<int>(6));
    map<int, vector<pair<int, int>>> vehicle_coords;
    int max_id = 0;

    for (int i = 0; i < 6; ++i) {
        for (int j = 0; j < 6; ++j) {
            cin >> board[i][j];
            if (board[i][j] > 0) {
                vehicle_coords[board[i][j]].push_back({i, j});
                max_id = max(max_id, board[i][j]);
            }
        }
    }
    
    if (max_id == 0) { // Should not happen based on constraints but good practice
        // Red car is ID 1, so max_id must be at least 1. If no cars, it's trivial.
        cout << "2 0" << endl; 
        return 0;
    }

    vehicle_count = max_id;
    vehicle_infos.resize(vehicle_count);
    vector<int> initial_state_vec(vehicle_count);

    for (int id = 1; id <= max_id; ++id) {
        auto& coords = vehicle_coords[id];
        sort(coords.begin(), coords.end());
        
        VehicleInfo v_info;
        v_info.id = id;
        v_info.len = coords.size();
        
        if (coords.size() > 1 && coords[0].first == coords[1].first) { // Horizontal
            v_info.is_horiz = true;
            v_info.fixed_coord = coords[0].first;
            initial_state_vec[id - 1] = coords[0].second;
        } else { // Vertical
            v_info.is_horiz = false;
            v_info.fixed_coord = coords[0].second;
            initial_state_vec[id - 1] = coords[0].first;
        }
        vehicle_infos[id - 1] = v_info;
    }

    vector<int> current_state(vehicle_count);
    vector<vector<bool>> occupied(6, vector<bool>(6, false));
    generate_all_states(0, current_state, occupied);
    
    int total_states = id_to_state.size();
    vector<vector<int>> adj(total_states);
    
    for (int i = 0; i < total_states; ++i) {
        State s_encoded = id_to_state[i];
        vector<int> s_vec = decode(s_encoded);
        
        fill(occupied.begin(), occupied.end(), vector<bool>(6, false));
        for(int k=0; k<vehicle_count; ++k) {
            mark_occupied(k, s_vec, occupied, true);
        }

        for (int k = 0; k < vehicle_count; ++k) {
            mark_occupied(k, s_vec, occupied, false);
            
            const auto& v_info = vehicle_infos[k];
            int pos = s_vec[k];

            if (pos + v_info.len < 6) {
                int r_check = v_info.is_horiz ? v_info.fixed_coord : pos + v_info.len;
                int c_check = v_info.is_horiz ? pos + v_info.len : v_info.fixed_coord;
                if (!occupied[r_check][c_check]) {
                    vector<int> next_s_vec = s_vec;
                    next_s_vec[k]++;
                    State next_s_encoded = encode(next_s_vec);
                    adj[i].push_back(state_to_id[next_s_encoded]);
                }
            }
            if (pos > 0) {
                int r_check = v_info.is_horiz ? v_info.fixed_coord : pos - 1;
                int c_check = v_info.is_horiz ? pos - 1 : v_info.fixed_coord;
                if (!occupied[r_check][c_check]) {
                    vector<int> next_s_vec = s_vec;
                    next_s_vec[k]--;
                    State next_s_encoded = encode(next_s_vec);
                    adj[i].push_back(state_to_id[next_s_encoded]);
                }
            }
            mark_occupied(k, s_vec, occupied, true);
        }
    }

    vector<int> dist_to_solve(total_states, -1);
    queue<int> q_solve;
    
    for (int i = 0; i < total_states; ++i) {
        if (decode(id_to_state[i])[0] == 4) {
            dist_to_solve[i] = 0;
            q_solve.push(i);
        }
    }
    
    while (!q_solve.empty()) {
        int u_id = q_solve.front();
        q_solve.pop();
        for (int v_id : adj[u_id]) {
            if (dist_to_solve[v_id] == -1) {
                dist_to_solve[v_id] = dist_to_solve[u_id] + 1;
                q_solve.push(v_id);
            }
        }
    }

    int initial_s_id = state_to_id[encode(initial_state_vec)];
    vector<int> dist_from_initial(total_states, -1);
    vector<int> parent(total_states, -1);
    
    queue<int> q_initial;
    dist_from_initial[initial_s_id] = 0;
    q_initial.push(initial_s_id);
    
    int max_solve_steps = -1;
    int hardest_state_id = -1;
    
    while(!q_initial.empty()){
        int u_id = q_initial.front();
        q_initial.pop();
        
        int current_solve_dist = dist_to_solve[u_id];
        if (current_solve_dist != -1) {
            int total_solve_steps = current_solve_dist + 2;
            if (total_solve_steps > max_solve_steps) {
                max_solve_steps = total_solve_steps;
                hardest_state_id = u_id;
            } else if (total_solve_steps == max_solve_steps) {
                if (dist_from_initial[u_id] < dist_from_initial[hardest_state_id]) {
                    hardest_state_id = u_id;
                }
            }
        }
        
        for (int v_id : adj[u_id]) {
            if (dist_from_initial[v_id] == -1) {
                dist_from_initial[v_id] = dist_from_initial[u_id] + 1;
                parent[v_id] = u_id;
                q_initial.push(v_id);
            }
        }
    }
    
    if (hardest_state_id == -1) {
      hardest_state_id = initial_s_id;
      max_solve_steps = (dist_to_solve[initial_s_id] != -1) ? (dist_to_solve[initial_s_id] + 2) : 0;
    }


    cout << max_solve_steps << " " << dist_from_initial[hardest_state_id] << endl;
    
    vector<pair<int, char>> moves;
    int curr = hardest_state_id;
    while (parent[curr] != -1) {
        int p = parent[curr];
        vector<int> s_curr = decode(id_to_state[curr]);
        vector<int> s_parent = decode(id_to_state[p]);
        
        int moved_vehicle_idx = -1;
        for (int i = 0; i < vehicle_count; ++i) {
            if (s_curr[i] != s_parent[i]) {
                moved_vehicle_idx = i;
                break;
            }
        }
        
        int vehicle_id = vehicle_infos[moved_vehicle_idx].id;
        char dir;
        int diff = s_curr[moved_vehicle_idx] - s_parent[moved_vehicle_idx];
        if (vehicle_infos[moved_vehicle_idx].is_horiz) {
            dir = (diff > 0) ? 'R' : 'L';
        } else {
            dir = (diff > 0) ? 'D' : 'U';
        }
        moves.push_back({vehicle_id, dir});
        curr = p;
    }
    
    reverse(moves.begin(), moves.end());
    for (const auto& move : moves) {
        cout << move.first << " " << move.second << endl;
    }

    return 0;
}