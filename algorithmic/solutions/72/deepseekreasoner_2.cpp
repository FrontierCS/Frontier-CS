#include <iostream>
#include <vector>
#include <queue>
#include <unordered_map>
#include <algorithm>
#include <utility>
#include <functional>
#include <string>
#include <cstdint>

using namespace std;

// Global vehicle data
int n; // number of vehicles
vector<int> orig_id;        // index -> original id
vector<bool> horiz;         // true if horizontal
vector<int> len;            // length (2 or 3)
vector<int> fixed_coord;    // row for horizontal, column for vertical
vector<int> init_var;       // initial variable coordinate (left col for horiz, top row for vert)

// Encode state: each variable coordinate uses 3 bits (0..7)
uint32_t encode(const vector<int>& var) {
    uint32_t code = 0;
    for (int i = 0; i < n; ++i) {
        code |= (var[i] << (3 * i));
    }
    return code;
}

// Decode state into var array
void decode(uint32_t code, vector<int>& var) {
    var.resize(n);
    for (int i = 0; i < n; ++i) {
        var[i] = (code >> (3 * i)) & 7;
    }
}

// Check if vehicle idx can move one step in direction dir.
// If yes, fill new_var and return true.
bool can_move(const vector<int>& var, int idx, char dir, vector<int>& new_var) {
    new_var = var;
    int delta = 0;
    if (horiz[idx]) {
        if (dir == 'L') delta = -1;
        else if (dir == 'R') delta = 1;
        else return false;
    } else {
        if (dir == 'U') delta = -1;
        else if (dir == 'D') delta = 1;
        else return false;
    }
    int v = var[idx] + delta;

    // Boundary checks
    if (horiz[idx]) {
        if (v < 0) return false;
        if (idx == 0) { // red car
            if (v > 6) return false;
            if (v == 6) { // moving off the board
                new_var[idx] = v;
                return true;
            }
        } else {
            if (v + len[idx] > 6) return false; // must stay on board
        }
    } else { // vertical
        if (v < 0) return false;
        if (v + len[idx] > 6) return false;
    }

    // Compute new on‑board cells for vehicle idx
    vector<pair<int, int>> cells;
    if (horiz[idx]) {
        int r = fixed_coord[idx];
        for (int k = 0; k < len[idx]; ++k) {
            int c = v + k;
            if (c >= 0 && c < 6) {
                cells.push_back({r, c});
            }
        }
    } else {
        int c = fixed_coord[idx];
        for (int k = 0; k < len[idx]; ++k) {
            int r = v + k;
            if (r >= 0 && r < 6) {
                cells.push_back({r, c});
            }
        }
    }

    // Check overlap with other vehicles
    for (int j = 0; j < n; ++j) {
        if (j == idx) continue;
        // Cells of vehicle j at var[j]
        if (horiz[j]) {
            int rj = fixed_coord[j];
            int lj = var[j];
            for (int k = 0; k < len[j]; ++k) {
                int cj = lj + k;
                if (cj >= 6) continue;
                for (const auto& cell : cells) {
                    if (cell.first == rj && cell.second == cj) {
                        return false;
                    }
                }
            }
        } else {
            int cj = fixed_coord[j];
            int tj = var[j];
            for (int k = 0; k < len[j]; ++k) {
                int rj = tj + k;
                if (rj >= 6) continue;
                for (const auto& cell : cells) {
                    if (cell.first == rj && cell.second == cj) {
                        return false;
                    }
                }
            }
        }
    }

    new_var[idx] = v;
    return true;
}

// Generate all goal states (red car off) and initialize BFS queue and distance map.
void generate_goals(queue<uint32_t>& q, unordered_map<uint32_t, int>& dist) {
    vector<int> cur_var(n);
    cur_var[0] = 6; // red car off

    function<void(int)> dfs = [&](int idx) {
        if (idx == n) {
            uint32_t code = encode(cur_var);
            dist[code] = 0;
            q.push(code);
            return;
        }
        if (idx == 0) {
            dfs(1);
            return;
        }
        int min_val = 0;
        int max_val = (horiz[idx] ? 6 - len[idx] : 6 - len[idx]);
        for (int v = min_val; v <= max_val; ++v) {
            cur_var[idx] = v;
            // Check overlap with already placed vehicles (indices 1..idx-1)
            bool ok = true;
            // Cells of vehicle idx at v
            vector<pair<int, int>> cells_idx;
            if (horiz[idx]) {
                int r = fixed_coord[idx];
                for (int k = 0; k < len[idx]; ++k) {
                    int c = v + k;
                    if (c < 6) cells_idx.push_back({r, c});
                }
            } else {
                int c = fixed_coord[idx];
                for (int k = 0; k < len[idx]; ++k) {
                    int r = v + k;
                    if (r < 6) cells_idx.push_back({r, c});
                }
            }
            for (int j = 1; j < idx; ++j) {
                if (horiz[j]) {
                    int rj = fixed_coord[j];
                    int lj = cur_var[j];
                    for (int k = 0; k < len[j]; ++k) {
                        int cj = lj + k;
                        if (cj >= 6) continue;
                        for (const auto& cell : cells_idx) {
                            if (cell.first == rj && cell.second == cj) {
                                ok = false;
                                break;
                            }
                        }
                        if (!ok) break;
                    }
                } else {
                    int cj = fixed_coord[j];
                    int tj = cur_var[j];
                    for (int k = 0; k < len[j]; ++k) {
                        int rj = tj + k;
                        if (rj >= 6) continue;
                        for (const auto& cell : cells_idx) {
                            if (cell.first == rj && cell.second == cj) {
                                ok = false;
                                break;
                            }
                        }
                        if (!ok) break;
                    }
                }
                if (!ok) break;
            }
            if (ok) {
                dfs(idx + 1);
            }
        }
    };
    dfs(1);
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(nullptr);

    // Read board
    vector<vector<int>> board(6, vector<int>(6));
    for (int i = 0; i < 6; ++i) {
        for (int j = 0; j < 6; ++j) {
            cin >> board[i][j];
        }
    }

    // Extract vehicles
    unordered_map<int, vector<pair<int, int>>> groups;
    for (int i = 0; i < 6; ++i) {
        for (int j = 0; j < 6; ++j) {
            int id = board[i][j];
            if (id != 0) {
                groups[id].push_back({i, j});
            }
        }
    }
    n = groups.size();

    orig_id.resize(n);
    horiz.resize(n);
    len.resize(n);
    fixed_coord.resize(n);
    init_var.resize(n);

    // Index 0 is reserved for the red car (id = 1)
    int red_idx = -1;
    for (const auto& p : groups) {
        if (p.first == 1) {
            red_idx = 0;
            break;
        }
    }
    if (red_idx == -1) {
        // According to problem, red car always exists.
        return 1;
    }

    // Assign indices: 0 for red car, others arbitrarily
    vector<int> ids_in_order(n);
    ids_in_order[0] = 1;
    int cur_idx = 1;
    for (const auto& p : groups) {
        if (p.first != 1) {
            ids_in_order[cur_idx++] = p.first;
        }
    }

    // Fill data structures
    for (int i = 0; i < n; ++i) {
        int id = ids_in_order[i];
        const auto& cells = groups[id];
        orig_id[i] = id;

        // Determine orientation and length
        bool same_row = true, same_col = true;
        int r0 = cells[0].first, c0 = cells[0].second;
        for (const auto& cell : cells) {
            if (cell.first != r0) same_row = false;
            if (cell.second != c0) same_col = false;
        }
        if (same_row && !same_col) {
            horiz[i] = true;
            fixed_coord[i] = r0;
            // leftmost column
            int min_c = c0;
            for (const auto& cell : cells) min_c = min(min_c, cell.second);
            init_var[i] = min_c;
        } else if (same_col && !same_row) {
            horiz[i] = false;
            fixed_coord[i] = c0;
            // topmost row
            int min_r = r0;
            for (const auto& cell : cells) min_r = min(min_r, cell.first);
            init_var[i] = min_r;
        } else {
            // Should not happen
            return 1;
        }
        len[i] = cells.size();
    }

    // Step 1: Multi‑source BFS from all goal states (red car off)
    queue<uint32_t> q;
    unordered_map<uint32_t, int> dist; // distance to goal
    if (n == 1) {
        // Only the red car
        vector<int> goal_var = {6};
        uint32_t goal_code = encode(goal_var);
        dist[goal_code] = 0;
        q.push(goal_code);
    } else {
        generate_goals(q, dist);
    }

    while (!q.empty()) {
        uint32_t cur_code = q.front(); q.pop();
        int cur_dist = dist[cur_code];
        vector<int> var;
        decode(cur_code, var);

        // Generate all possible moves from this state
        for (int i = 0; i < n; ++i) {
            vector<char> dirs;
            if (horiz[i]) dirs = {'L', 'R'};
            else dirs = {'U', 'D'};

            for (char dir : dirs) {
                vector<int> new_var;
                if (can_move(var, i, dir, new_var)) {
                    uint32_t new_code = encode(new_var);
                    if (dist.find(new_code) == dist.end()) {
                        dist[new_code] = cur_dist + 1;
                        q.push(new_code);
                    }
                }
            }
        }
    }

    // Step 2: BFS from initial state to find reachable state with maximum d(S)
    queue<uint32_t> q2;
    unordered_map<uint32_t, int> depth_from_start;
    unordered_map<uint32_t, pair<uint32_t, pair<int, char>>> parent; // prev state, (vehicle_index, direction)

    uint32_t start_code = encode(init_var);
    depth_from_start[start_code] = 0;
    parent[start_code] = {0, {-1, ' '}}; // dummy
    q2.push(start_code);

    int best_solve = -1;
    uint32_t best_state = 0;

    while (!q2.empty()) {
        uint32_t cur_code = q2.front(); q2.pop();
        int cur_depth = depth_from_start[cur_code];

        // Get solving distance for this state
        auto it = dist.find(cur_code);
        if (it == dist.end()) continue; // should not happen
        int solve_dist = it->second;
        if (solve_dist > best_solve) {
            best_solve = solve_dist;
            best_state = cur_code;
        }

        vector<int> var;
        decode(cur_code, var);
        // Generate moves
        for (int i = 0; i < n; ++i) {
            vector<char> dirs;
            if (horiz[i]) dirs = {'L', 'R'};
            else dirs = {'U', 'D'};
            for (char dir : dirs) {
                vector<int> new_var;
                if (can_move(var, i, dir, new_var)) {
                    uint32_t new_code = encode(new_var);
                    if (depth_from_start.find(new_code) == depth_from_start.end()) {
                        depth_from_start[new_code] = cur_depth + 1;
                        parent[new_code] = {cur_code, {i, dir}};
                        q2.push(new_code);
                    }
                }
            }
        }
    }

    // Output results
    int transform_steps = depth_from_start[best_state];
    cout << best_solve << " " << transform_steps << endl;

    // Reconstruct transformation moves
    if (transform_steps > 0) {
        vector<pair<int, char>> moves;
        uint32_t cur = best_state;
        while (cur != start_code) {
            auto& p = parent[cur];
            int idx = p.second.first;
            char dir = p.second.second;
            moves.push_back({idx, dir});
            cur = p.first;
        }
        reverse(moves.begin(), moves.end());
        for (const auto& m : moves) {
            cout << orig_id[m.first] << " " << m.second << endl;
        }
    }

    return 0;
}