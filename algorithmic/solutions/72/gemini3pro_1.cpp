#include <iostream>
#include <vector>
#include <string>
#include <queue>
#include <map>
#include <algorithm>

using namespace std;

// Structure to hold static properties of a vehicle
struct Vehicle {
    int id;
    int len;
    char orientation; // 'H' or 'V'
    int fixed_idx;    // row index for Horizontal, col index for Vertical
};

// Global vehicle definitions
int N_VEHICLES = 0;
vector<Vehicle> vehicles;

// Encodes the variable positions (col for H, row for V) of all vehicles into a 64-bit integer.
// Each position is in range [0, 5], so 3 bits are sufficient.
// Max 10 vehicles => 30 bits.
long long encode_state(const vector<int>& positions) {
    long long state = 0;
    for (int p : positions) {
        state = (state << 3) | p;
    }
    return state;
}

// Decodes the state integer back into a vector of positions
vector<int> decode_state(long long state) {
    vector<int> positions(N_VEHICLES);
    for (int i = N_VEHICLES - 1; i >= 0; --i) {
        positions[i] = state & 7;
        state >>= 3;
    }
    return positions;
}

// Helper to fill a grid based on vehicle positions to check for collisions
void fill_grid(const vector<int>& positions, vector<vector<int>>& grid) {
    for (int r = 0; r < 6; ++r) {
        for (int c = 0; c < 6; ++c) grid[r][c] = 0;
    }
    for (int i = 0; i < N_VEHICLES; ++i) {
        int r, c;
        if (vehicles[i].orientation == 'H') {
            r = vehicles[i].fixed_idx;
            c = positions[i];
            for (int k = 0; k < vehicles[i].len; ++k) grid[r][c + k] = vehicles[i].id;
        } else {
            c = vehicles[i].fixed_idx;
            r = positions[i];
            for (int k = 0; k < vehicles[i].len; ++k) grid[r + k][c] = vehicles[i].id;
        }
    }
}

// Info stored for BFS traversal from start
struct StateInfo {
    long long prev_state;
    int vehicle_moved; // ID of vehicle moved to reach this state
    int move_dir;      // -1 or +1
    int dist_from_start;
};

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    vector<vector<int>> input_grid(6, vector<int>(6));
    map<int, vector<pair<int,int>>> v_cells;
    int max_id = 0;

    // Read input
    for (int r = 0; r < 6; ++r) {
        for (int c = 0; c < 6; ++c) {
            cin >> input_grid[r][c];
            if (input_grid[r][c] > 0) {
                v_cells[input_grid[r][c]].push_back({r, c});
                max_id = max(max_id, input_grid[r][c]);
            }
        }
    }

    N_VEHICLES = max_id;
    vehicles.resize(N_VEHICLES);
    vector<int> start_positions(N_VEHICLES);

    // Parse vehicles
    for (auto& entry : v_cells) {
        int id = entry.first;
        vector<pair<int,int>>& cells = entry.second;
        
        bool horz = (cells[0].first == cells[1].first);
        int idx = id - 1; // 0-based index for vehicle ID
        
        vehicles[idx].id = id;
        vehicles[idx].len = cells.size();
        vehicles[idx].orientation = horz ? 'H' : 'V';
        
        if (horz) {
            vehicles[idx].fixed_idx = cells[0].first; // row
            // Find min col
            int min_c = 6;
            for(auto p : cells) min_c = min(min_c, p.second);
            start_positions[idx] = min_c;
        } else {
            vehicles[idx].fixed_idx = cells[0].second; // col
            // Find min row
            int min_r = 6;
            for(auto p : cells) min_r = min(min_r, p.first);
            start_positions[idx] = min_r;
        }
    }

    long long start_state = encode_state(start_positions);

    // Forward BFS to find all reachable states
    map<long long, StateInfo> visited; // Stores reachable states and path info
    queue<long long> q;
    vector<long long> all_reachable_states;

    visited[start_state] = {-1, -1, 0, 0};
    q.push(start_state);
    
    vector<vector<int>> temp_grid(6, vector<int>(6));

    while(!q.empty()) {
        long long curr_enc = q.front();
        q.pop();
        all_reachable_states.push_back(curr_enc);
        
        vector<int> current_pos = decode_state(curr_enc);
        fill_grid(current_pos, temp_grid);

        for (int i = 0; i < N_VEHICLES; ++i) {
            int len = vehicles[i].len;
            char orient = vehicles[i].orientation;
            int curr_val = current_pos[i];
            
            // Try move -1
            if (curr_val > 0) {
                int check_r, check_c;
                if (orient == 'H') { check_r = vehicles[i].fixed_idx; check_c = curr_val - 1; }
                else { check_r = curr_val - 1; check_c = vehicles[i].fixed_idx; }
                
                if (temp_grid[check_r][check_c] == 0) {
                    vector<int> next_pos = current_pos;
                    next_pos[i]--;
                    long long next_enc = encode_state(next_pos);
                    if (visited.find(next_enc) == visited.end()) {
                        visited[next_enc] = {curr_enc, vehicles[i].id, -1, visited[curr_enc].dist_from_start + 1};
                        q.push(next_enc);
                    }
                }
            }

            // Try move +1
            if (curr_val + len < 6) {
                int check_r, check_c;
                if (orient == 'H') { check_r = vehicles[i].fixed_idx; check_c = curr_val + len; }
                else { check_r = curr_val + len; check_c = vehicles[i].fixed_idx; }

                if (temp_grid[check_r][check_c] == 0) {
                    vector<int> next_pos = current_pos;
                    next_pos[i]++;
                    long long next_enc = encode_state(next_pos);
                    if (visited.find(next_enc) == visited.end()) {
                        visited[next_enc] = {curr_enc, vehicles[i].id, 1, visited[curr_enc].dist_from_start + 1};
                        q.push(next_enc);
                    }
                }
            }
        }
    }

    // Backward BFS (Multi-Source) to find distance to solution for all reachable states
    // Target states: Red car (ID 1, index 0) at column 4
    map<long long, int> dist_to_solve;
    queue<long long> bq;

    for (long long s : all_reachable_states) {
        vector<int> p = decode_state(s);
        // Vehicle 1 is red car. For len 2, if at col 4, it occupies 4,5. Exit is to the right.
        if (p[0] == 4) {
            dist_to_solve[s] = 2; // 1 step to move to 5, 1 step to move out completely
            bq.push(s);
        }
    }

    while (!bq.empty()) {
        long long curr_enc = bq.front();
        bq.pop();
        int d = dist_to_solve[curr_enc];

        vector<int> current_pos = decode_state(curr_enc);
        fill_grid(current_pos, temp_grid);

        for (int i = 0; i < N_VEHICLES; ++i) {
            int len = vehicles[i].len;
            char orient = vehicles[i].orientation;
            int curr_val = current_pos[i];
            
            // Generate neighbors. Graph is undirected.
            // Move -1
            if (curr_val > 0) {
                int check_r, check_c;
                if (orient == 'H') { check_r = vehicles[i].fixed_idx; check_c = curr_val - 1; }
                else { check_r = curr_val - 1; check_c = vehicles[i].fixed_idx; }
                
                if (temp_grid[check_r][check_c] == 0) {
                    vector<int> next_pos = current_pos;
                    next_pos[i]--;
                    long long next_enc = encode_state(next_pos);
                    // We only care about states that are reachable from start
                    if (visited.count(next_enc)) {
                        if (dist_to_solve.find(next_enc) == dist_to_solve.end()) {
                            dist_to_solve[next_enc] = d + 1;
                            bq.push(next_enc);
                        }
                    }
                }
            }
            
            // Move +1
            if (curr_val + len < 6) {
                int check_r, check_c;
                if (orient == 'H') { check_r = vehicles[i].fixed_idx; check_c = curr_val + len; }
                else { check_r = curr_val + len; check_c = vehicles[i].fixed_idx; }
                
                if (temp_grid[check_r][check_c] == 0) {
                    vector<int> next_pos = current_pos;
                    next_pos[i]++;
                    long long next_enc = encode_state(next_pos);
                    if (visited.count(next_enc)) {
                        if (dist_to_solve.find(next_enc) == dist_to_solve.end()) {
                            dist_to_solve[next_enc] = d + 1;
                            bq.push(next_enc);
                        }
                    }
                }
            }
        }
    }

    // Find the state with maximum minimum steps to solve
    long long best_state = start_state;
    int max_steps = 0;
    
    if (!dist_to_solve.empty()) {
        for (auto const& [state, d] : dist_to_solve) {
            if (d > max_steps) {
                max_steps = d;
                best_state = state;
            }
        }
    }

    // Output results
    vector<pair<int, string>> moves;
    long long curr = best_state;
    while (curr != start_state) {
        StateInfo info = visited[curr];
        int vid = info.vehicle_moved;
        int dir = info.move_dir;
        string dstr;
        // determine char based on orientation and dir
        // vid is 1-based ID, vector is 0-based
        if (vehicles[vid-1].orientation == 'H') {
            dstr = (dir == -1 ? "L" : "R");
        } else {
            dstr = (dir == -1 ? "U" : "D");
        }
        moves.push_back({vid, dstr});
        curr = info.prev_state;
    }
    reverse(moves.begin(), moves.end());

    cout << max_steps << " " << moves.size() << "\n";
    for (const auto& m : moves) {
        cout << m.first << " " << m.second << "\n";
    }

    return 0;
}