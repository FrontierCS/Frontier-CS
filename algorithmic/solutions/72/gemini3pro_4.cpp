#include <iostream>
#include <vector>
#include <queue>
#include <map>
#include <algorithm>
#include <tuple>

using namespace std;

// Vehicle structure
struct Vehicle {
    int id;
    int len;
    int fixed_coord; // row for H, col for V
    int orientation; // 0: H, 1: V
    int var_coord;   // current variable coordinate (col for H, row for V)
};

// Global vehicle definitions
int num_vehicles = 0;
vector<Vehicle> vehicles;

// Encodes the current variable coordinates of all vehicles into a single integer
unsigned int encode_state(const vector<int>& vars) {
    unsigned int state = 0;
    for (int i = 0; i < num_vehicles; ++i) {
        state |= ((unsigned int)vars[i] << (3 * i));
    }
    return state;
}

vector<int> decode_state(unsigned int state) {
    vector<int> vars(num_vehicles);
    for (int i = 0; i < num_vehicles; ++i) {
        vars[i] = (state >> (3 * i)) & 7;
    }
    return vars;
}

// Check collision
bool is_valid(const vector<int>& vars) {
    int grid[6][6];
    // We only need to check collisions, so filling with 1s is enough
    for(int r=0; r<6; ++r) 
        for(int c=0; c<6; ++c) grid[r][c] = 0;

    for (int i = 0; i < num_vehicles; ++i) {
        int r, c;
        if (vehicles[i].orientation == 0) { // Horizontal
            r = vehicles[i].fixed_coord;
            int c_start = vars[i];
            
            // Check bounds
            if (i == 0) {
                // Car 1 can go beyond 5 (to 6)
                // If it is >6, it's invalid for our state space logic except 6
                if (c_start > 6) return false; 
                if (c_start < 0) return false;
            } else {
                if (c_start < 0 || c_start + vehicles[i].len > 6) return false;
            }

            for (int k = 0; k < vehicles[i].len; ++k) {
                int cc = c_start + k;
                if (cc >= 0 && cc < 6) {
                    if (grid[r][cc] != 0) return false; 
                    grid[r][cc] = 1;
                }
            }
        } else { // Vertical
            c = vehicles[i].fixed_coord;
            int r_start = vars[i];
            if (r_start < 0 || r_start + vehicles[i].len > 6) return false;
            
            for (int k = 0; k < vehicles[i].len; ++k) {
                int rr = r_start + k;
                if (rr >= 0 && rr < 6) {
                    if (grid[rr][c] != 0) return false; 
                    grid[rr][c] = 1;
                }
            }
        }
    }
    return true;
}

struct StateInfo {
    int dist_from_start;
    int parent_idx;
    int move_vehicle_idx;
    int move_dir; // -1 for dec, 1 for inc
};

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int board[6][6];
    map<int, vector<pair<int, int>>> vehicle_cells;
    int max_id = 0;

    for (int r = 0; r < 6; ++r) {
        for (int c = 0; c < 6; ++c) {
            cin >> board[r][c];
            if (board[r][c] > 0) {
                vehicle_cells[board[r][c]].push_back({r, c});
                max_id = max(max_id, board[r][c]);
            }
        }
    }

    num_vehicles = max_id;
    vehicles.resize(num_vehicles);
    vector<int> initial_vars(num_vehicles);

    for (auto const& [id, cells] : vehicle_cells) {
        int idx = id - 1;
        vehicles[idx].id = id;
        
        int min_r = 6, max_r = -1, min_c = 6, max_c = -1;
        for (auto p : cells) {
            min_r = min(min_r, p.first);
            max_r = max(max_r, p.first);
            min_c = min(min_c, p.second);
            max_c = max(max_c, p.second);
        }

        if (max_r > min_r) {
            // Vertical
            vehicles[idx].orientation = 1;
            vehicles[idx].len = max_r - min_r + 1;
            vehicles[idx].fixed_coord = min_c;
            vehicles[idx].var_coord = min_r;
        } else {
            // Horizontal
            vehicles[idx].orientation = 0;
            vehicles[idx].len = max_c - min_c + 1;
            vehicles[idx].fixed_coord = min_r;
            vehicles[idx].var_coord = min_c;
        }
        initial_vars[idx] = vehicles[idx].var_coord;
    }

    // BFS 1: Reachable states from Start
    map<unsigned int, int> state_to_idx;
    vector<unsigned int> idx_to_state;
    vector<StateInfo> reach_info;

    unsigned int start_state = encode_state(initial_vars);
    
    queue<int> q;
    state_to_idx[start_state] = 0;
    idx_to_state.push_back(start_state);
    reach_info.push_back({0, -1, 0, 0});
    q.push(0);

    while (!q.empty()) {
        int u_idx = q.front();
        q.pop();
        
        unsigned int u_enc = idx_to_state[u_idx];
        vector<int> u_vars = decode_state(u_enc);

        for (int i = 0; i < num_vehicles; ++i) {
            int dirs[] = {-1, 1};
            for (int d : dirs) {
                int original = u_vars[i];
                int next_val = original + d;
                
                if (i == 0) {
                    if (next_val < 0 || next_val > 6) continue;
                } else {
                    if (next_val < 0 || next_val > 6 - vehicles[i].len) continue;
                }

                u_vars[i] = next_val;
                if (is_valid(u_vars)) {
                    unsigned int v_enc = encode_state(u_vars);
                    if (state_to_idx.find(v_enc) == state_to_idx.end()) {
                        int v_idx = idx_to_state.size();
                        state_to_idx[v_enc] = v_idx;
                        idx_to_state.push_back(v_enc);
                        reach_info.push_back({reach_info[u_idx].dist_from_start + 1, u_idx, i, d});
                        q.push(v_idx);
                    }
                }
                u_vars[i] = original; 
            }
        }
    }

    // BFS 2: Distance to Solved
    int num_states = idx_to_state.size();
    vector<int> dist_to_solved(num_states, -1);
    queue<int> q2;

    for (int i = 0; i < num_states; ++i) {
        vector<int> vars = decode_state(idx_to_state[i]);
        if (vars[0] == 6) {
            dist_to_solved[i] = 0;
            q2.push(i);
        }
    }

    while (!q2.empty()) {
        int u_idx = q2.front();
        q2.pop();
        
        unsigned int u_enc = idx_to_state[u_idx];
        vector<int> u_vars = decode_state(u_enc);

        for (int i = 0; i < num_vehicles; ++i) {
            int dirs[] = {-1, 1};
            for (int d : dirs) {
                int original = u_vars[i];
                int next_val = original + d;

                if (i == 0) {
                    if (next_val < 0 || next_val > 6) continue;
                } else {
                    if (next_val < 0 || next_val > 6 - vehicles[i].len) continue;
                }

                u_vars[i] = next_val;
                // Optimization: is_valid check is fast enough, but we can also rely on the fact 
                // that we are traversing edges of existing graph.
                // But since we don't store adjacency list, we must regenerate valid neighbors
                // and check if they exist in state_to_idx.
                if (is_valid(u_vars)) {
                    unsigned int v_enc = encode_state(u_vars);
                    auto it = state_to_idx.find(v_enc);
                    if (it != state_to_idx.end()) {
                        int v_idx = it->second;
                        if (dist_to_solved[v_idx] == -1) {
                            dist_to_solved[v_idx] = dist_to_solved[u_idx] + 1;
                            q2.push(v_idx);
                        }
                    }
                }
                u_vars[i] = original;
            }
        }
    }

    int max_dist = -1;
    int best_state_idx = -1;

    for (int i = 0; i < num_states; ++i) {
        if (dist_to_solved[i] != -1) {
            // We want to maximize steps to solve (max_dist)
            if (dist_to_solved[i] > max_dist) {
                max_dist = dist_to_solved[i];
                best_state_idx = i;
            }
        }
    }

    cout << max_dist << " " << reach_info[best_state_idx].dist_from_start << endl;

    vector<pair<int, char>> moves;
    int curr = best_state_idx;
    while (curr != 0) { 
        int p = reach_info[curr].parent_idx;
        int veh = reach_info[curr].move_vehicle_idx;
        int d = reach_info[curr].move_dir;
        
        char dir_char;
        if (vehicles[veh].orientation == 0) {
            dir_char = (d == -1) ? 'L' : 'R';
        } else {
            dir_char = (d == -1) ? 'U' : 'D';
        }
        moves.push_back({vehicles[veh].id, dir_char});
        curr = p;
    }
    reverse(moves.begin(), moves.end());

    for (auto m : moves) {
        cout << m.first << " " << m.second << endl;
    }

    return 0;
}