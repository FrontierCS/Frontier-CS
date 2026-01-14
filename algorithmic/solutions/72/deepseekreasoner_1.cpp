#include <iostream>
#include <vector>
#include <array>
#include <queue>
#include <unordered_map>
#include <algorithm>
#include <cstdint>
#include <tuple>
#include <utility>
#include <cstring>

using namespace std;

const int ROWS = 6;
const int COLS = 6;

struct Vehicle {
    int id;          // original id
    bool horiz;      // true if horizontal
    int len;         // length (2 for car, 3 for truck)
    int fixed;       // row if horizontal, column if vertical
    int var;         // leftmost column if horizontal, top row if vertical
    int index;       // index in the internal array (0-based)
};

vector<Vehicle> vehicles;
int n;              // number of vehicles
int red_index;      // index of the red car (should be 0)

// Precomputed masks for each vehicle and each possible var (0..5)
vector<array<uint64_t, 6>> masks;
vector<array<bool, 6>> valid;

// Encode state (list of vars) into a 30-bit integer
uint32_t encode(const vector<int>& vars) {
    uint32_t code = 0;
    for (int i = 0; i < n; ++i) {
        code |= (vars[i] << (3 * i));
    }
    return code;
}

// Decode state into vars
void decode(uint32_t code, vector<int>& vars) {
    for (int i = 0; i < n; ++i) {
        vars[i] = (code >> (3 * i)) & 7;
    }
}

// Compute mask for a vehicle at a given var
uint64_t compute_mask(const Vehicle& v, int var) {
    uint64_t m = 0;
    if (v.horiz) {
        int r = v.fixed;
        for (int c = var; c < var + v.len; ++c) {
            m |= (1ULL << (r * COLS + c));
        }
    } else {
        int c = v.fixed;
        for (int r = var; r < var + v.len; ++r) {
            m |= (1ULL << (r * COLS + c));
        }
    }
    return m;
}

int main() {
    // Read board
    vector<vector<int>> board(ROWS, vector<int>(COLS));
    for (int r = 0; r < ROWS; ++r) {
        for (int c = 0; c < COLS; ++c) {
            cin >> board[r][c];
        }
    }

    // Find all vehicles
    unordered_map<int, Vehicle> vehicle_map;
    for (int r = 0; r < ROWS; ++r) {
        for (int c = 0; c < COLS; ++c) {
            int id = board[r][c];
            if (id == 0) continue;
            if (vehicle_map.find(id) == vehicle_map.end()) {
                Vehicle v;
                v.id = id;
                v.horiz = true;  // assume horizontal, will check later
                v.len = 0;
                v.fixed = r;
                v.var = c;
                vehicle_map[id] = v;
            }
            // update length and orientation
            Vehicle& v = vehicle_map[id];
            v.len++;
            // check if still consistent orientation
            if (v.horiz && board[r][c] != 0 && r != v.fixed) {
                v.horiz = false;
                v.fixed = c; // for vertical, fixed is column
                v.var = r;   // top row
            }
        }
    }

    // Convert to vector and sort by id, red car (id=1) first
    for (auto& p : vehicle_map) {
        vehicles.push_back(p.second);
    }
    sort(vehicles.begin(), vehicles.end(),
         [](const Vehicle& a, const Vehicle& b) { return a.id < b.id; });
    n = vehicles.size();
    // Assign index and adjust red_index
    for (int i = 0; i < n; ++i) {
        vehicles[i].index = i;
        if (vehicles[i].id == 1) red_index = i;
    }
    // Make sure red car is at index 0 (swap if needed)
    if (red_index != 0) {
        swap(vehicles[0], vehicles[red_index]);
        for (int i = 0; i < n; ++i) vehicles[i].index = i;
        red_index = 0;
    }

    // Precompute masks and valid ranges
    masks.resize(n);
    valid.resize(n);
    for (int i = 0; i < n; ++i) {
        const Vehicle& v = vehicles[i];
        for (int var = 0; var < 6; ++var) {
            bool ok = false;
            if (v.horiz) {
                ok = (var >= 0 && var + v.len - 1 < COLS);
            } else {
                ok = (var >= 0 && var + v.len - 1 < ROWS);
            }
            valid[i][var] = ok;
            if (ok) {
                masks[i][var] = compute_mask(v, var);
            } else {
                masks[i][var] = 0;
            }
        }
    }

    // Multi-source BFS from all goal states (red car var = 4)
    unordered_map<uint32_t, uint16_t> dist_to_goal; // state -> distance to a goal state
    queue<pair<uint32_t, int>> q; // state, distance

    // Recursively generate all goal states
    vector<int> vars(n);
    vars[0] = 4; // red car leftmost column = 4
    uint64_t occupied = masks[0][4];

    // Use iterative stack to avoid deep recursion
    struct StackFrame {
        int idx;
        uint64_t mask;
    };
    vector<StackFrame> stack;
    stack.push_back({1, occupied}); // start with vehicle index 1

    while (!stack.empty()) {
        StackFrame f = stack.back();
        stack.pop_back();
        int idx = f.idx;
        uint64_t mask = f.mask;

        if (idx == n) {
            // All vehicles placed, encode state
            uint32_t code = encode(vars);
            dist_to_goal[code] = 0;
            q.push({code, 0});
            continue;
        }

        // Try all possible var for vehicle idx
        for (int var = 0; var < 6; ++var) {
            if (!valid[idx][var]) continue;
            uint64_t m = masks[idx][var];
            if (m & mask) continue;
            vars[idx] = var;
            stack.push_back({idx + 1, mask | m});
        }
    }

    // Perform multi-source BFS
    while (!q.empty()) {
        auto [code, d] = q.front(); q.pop();
        // Ensure we have the smallest distance
        if (dist_to_goal[code] != d) continue;

        vector<int> cur_vars(n);
        decode(code, cur_vars);
        uint64_t total_mask = 0;
        for (int i = 0; i < n; ++i) {
            total_mask |= masks[i][cur_vars[i]];
        }

        for (int i = 0; i < n; ++i) {
            int var = cur_vars[i];
            uint64_t mask_i = masks[i][var];
            uint64_t other_mask = total_mask ^ mask_i;

            // Generate moves
            vector<pair<int, char>> moves;
            if (vehicles[i].horiz) {
                moves = {{-1, 'L'}, {1, 'R'}};
            } else {
                moves = {{-1, 'U'}, {1, 'D'}};
            }
            for (auto [delta, dir] : moves) {
                int new_var = var + delta;
                if (new_var < 0 || new_var >= 6 || !valid[i][new_var]) continue;
                uint64_t new_mask_i = masks[i][new_var];
                if (new_mask_i & other_mask) continue;

                // Compute new state code
                vector<int> new_vars = cur_vars;
                new_vars[i] = new_var;
                uint32_t new_code = encode(new_vars);

                auto it = dist_to_goal.find(new_code);
                if (it == dist_to_goal.end() || it->second > d + 1) {
                    dist_to_goal[new_code] = d + 1;
                    q.push({new_code, d + 1});
                }
            }
        }
    }

    // Find initial state
    vector<int> init_vars(n);
    for (int i = 0; i < n; ++i) {
        init_vars[i] = vehicles[i].var;
    }
    uint32_t init_code = encode(init_vars);

    // Priority BFS from initial state to find state with maximum solution depth
    using QueueEntry = tuple<int, uint32_t, int>; // (-dist_to_goal, state, dist_from_initial)
    priority_queue<QueueEntry> pq;
    unordered_map<uint32_t, pair<uint32_t, pair<int, char>>> parent; // state -> (parent_state, (vehicle_id, direction))

    int init_dgoal = dist_to_goal[init_code];
    pq.emplace(-init_dgoal, init_code, 0);
    parent[init_code] = {init_code, {-1, ' '}}; // root

    int best_value = init_dgoal + 2; // solution depth = dist_to_goal + 2
    uint32_t best_state = init_code;
    int best_dist_ini = 0;

    while (!pq.empty()) {
        auto [neg_d, code, dist_ini] = pq.top(); pq.pop();
        int d_goal = -neg_d;
        if (d_goal + 2 < best_value) break; // cannot improve

        vector<int> cur_vars(n);
        decode(code, cur_vars);
        uint64_t total_mask = 0;
        for (int i = 0; i < n; ++i) {
            total_mask |= masks[i][cur_vars[i]];
        }

        for (int i = 0; i < n; ++i) {
            int var = cur_vars[i];
            uint64_t mask_i = masks[i][var];
            uint64_t other_mask = total_mask ^ mask_i;

            vector<pair<int, char>> moves;
            if (vehicles[i].horiz) {
                moves = {{-1, 'L'}, {1, 'R'}};
            } else {
                moves = {{-1, 'U'}, {1, 'D'}};
            }
            for (auto [delta, dir] : moves) {
                int new_var = var + delta;
                if (new_var < 0 || new_var >= 6 || !valid[i][new_var]) continue;
                uint64_t new_mask_i = masks[i][new_var];
                if (new_mask_i & other_mask) continue;

                vector<int> new_vars = cur_vars;
                new_vars[i] = new_var;
                uint32_t new_code = encode(new_vars);

                if (dist_to_goal.find(new_code) == dist_to_goal.end()) continue;
                if (parent.find(new_code) != parent.end()) continue;

                int new_dgoal = dist_to_goal[new_code];
                parent[new_code] = {code, {vehicles[i].id, dir}};
                pq.emplace(-new_dgoal, new_code, dist_ini + 1);

                int value = new_dgoal + 2;
                if (value > best_value) {
                    best_value = value;
                    best_state = new_code;
                    best_dist_ini = dist_ini + 1;
                }
            }
        }
    }

    // Reconstruct moves from initial to best_state
    vector<pair<int, char>> moves_seq;
    uint32_t cur = best_state;
    while (cur != init_code) {
        auto& p = parent[cur];
        moves_seq.push_back(p.second);
        cur = p.first;
    }
    reverse(moves_seq.begin(), moves_seq.end());

    // Output
    cout << best_value << " " << best_dist_ini << endl;
    for (auto& move : moves_seq) {
        cout << move.first << " " << move.second << endl;
    }

    return 0;
}