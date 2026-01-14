#include <iostream>
#include <vector>
#include <unordered_map>
#include <unordered_set>
#include <queue>
#include <algorithm>
#include <cstdint>
#include <utility>
#include <string>

using namespace std;

struct VehicleInfo {
    int id;
    bool isRed;
    bool horizontal;
    int length;
};

struct Move {
    int vid;   // index in vehicles array
    char dir;
};

struct State {
    vector<short> rows;
    vector<short> cols;
};

// Global variables
vector<VehicleInfo> infos;   // vehicle attributes, index 0 is red car
int n;                       // number of vehicles

// Encode state to a 64-bit integer
uint64_t encode(const State& s) {
    uint64_t key = 0;
    int shift = 0;
    // red car column (0..6)
    key |= (uint64_t)(s.cols[0]) << shift;
    shift += 3;
    // other vehicles: row (0..5) and column (0..5)
    for (int i = 1; i < n; ++i) {
        key |= (uint64_t)(s.rows[i]) << shift;
        shift += 3;
        key |= (uint64_t)(s.cols[i]) << shift;
        shift += 3;
    }
    return key;
}

// Decode a 64-bit integer back to state
State decode(uint64_t key) {
    State s;
    s.rows.resize(n);
    s.cols.resize(n);
    int shift = 0;
    s.cols[0] = (key >> shift) & 0x7;
    shift += 3;
    for (int i = 1; i < n; ++i) {
        s.rows[i] = (key >> shift) & 0x7;
        shift += 3;
        s.cols[i] = (key >> shift) & 0x7;
        shift += 3;
    }
    // red car row is always 2 (0-indexed third row)
    s.rows[0] = 2;
    return s;
}

// Return the on-board cells occupied by vehicle vid at its given position
vector<pair<int, int>> get_cells(const State& s, int vid) {
    const VehicleInfo& vi = infos[vid];
    int row = s.rows[vid];
    int col = s.cols[vid];
    vector<pair<int, int>> cells;
    if (vid == 0) { // red car
        if (col == 6) return cells; // completely off board
        if (col == 5) {
            cells.push_back({row, 5});
        } else {
            cells.push_back({row, col});
            cells.push_back({row, col + 1});
        }
    } else {
        if (vi.horizontal) {
            for (int k = 0; k < vi.length; ++k) {
                cells.push_back({row, col + k});
            }
        } else {
            for (int k = 0; k < vi.length; ++k) {
                cells.push_back({row + k, col});
            }
        }
    }
    return cells;
}

// Compute occupancy mask for the whole state
uint64_t compute_full_occupancy(const State& s) {
    uint64_t mask = 0;
    for (int i = 0; i < n; ++i) {
        auto cells = get_cells(s, i);
        for (auto& cell : cells) {
            int r = cell.first, c = cell.second;
            if (r >= 0 && r < 6 && c >= 0 && c < 6) {
                mask |= (1ULL << (r * 6 + c));
            }
        }
    }
    return mask;
}

// Check if moving vehicle vid in direction dir is legal from state s
bool can_move(const State& s, int vid, char dir, uint64_t occ_excl) {
    const VehicleInfo& vi = infos[vid];
    int row = s.rows[vid];
    int col = s.cols[vid];
    int new_row = row, new_col = col;

    // Bounds checking
    if (vi.horizontal) {
        if (dir == 'L') {
            new_col = col - 1;
            if (new_col < 0) return false;
        } else if (dir == 'R') {
            new_col = col + 1;
            if (vid == 0) { // red car
                if (new_col > 6) return false;
            } else {
                if (new_col + vi.length - 1 > 5) return false;
            }
        } else return false;
    } else { // vertical
        if (dir == 'U') {
            new_row = row - 1;
            if (new_row < 0) return false;
        } else if (dir == 'D') {
            new_row = row + 1;
            if (new_row + vi.length - 1 > 5) return false;
        } else return false;
    }

    // Simulate the move and check new cells against occupancy
    State new_s = s;
    new_s.rows[vid] = new_row;
    new_s.cols[vid] = new_col;
    auto new_cells = get_cells(new_s, vid);
    for (auto& cell : new_cells) {
        int r = cell.first, c = cell.second;
        if (r < 0 || r >= 6 || c < 0 || c >= 6) continue; // off-board cells are fine
        if (occ_excl & (1ULL << (r * 6 + c))) {
            return false;
        }
    }
    return true;
}

// Generate all legal moves from state s
vector<Move> generate_moves(const State& s) {
    vector<Move> moves;
    uint64_t full_occ = compute_full_occupancy(s);
    for (int vid = 0; vid < n; ++vid) {
        const VehicleInfo& vi = infos[vid];
        // Remove vehicle's own cells from occupancy
        uint64_t occ_excl = full_occ;
        auto cells = get_cells(s, vid);
        for (auto& cell : cells) {
            int r = cell.first, c = cell.second;
            if (r >= 0 && r < 6 && c >= 0 && c < 6) {
                occ_excl &= ~(1ULL << (r * 6 + c));
            }
        }
        if (vi.horizontal) {
            if (can_move(s, vid, 'L', occ_excl)) moves.push_back({vid, 'L'});
            if (can_move(s, vid, 'R', occ_excl)) moves.push_back({vid, 'R'});
        } else {
            if (can_move(s, vid, 'U', occ_excl)) moves.push_back({vid, 'U'});
            if (can_move(s, vid, 'D', occ_excl)) moves.push_back({vid, 'D'});
        }
    }
    return moves;
}

// Apply a move to a state and return the new state
State apply_move(const State& s, int vid, char dir) {
    State t = s;
    if (infos[vid].horizontal) {
        if (dir == 'L') t.cols[vid]--;
        else if (dir == 'R') t.cols[vid]++;
    } else {
        if (dir == 'U') t.rows[vid]--;
        else if (dir == 'D') t.rows[vid]++;
    }
    return t;
}

int main() {
    // Read board
    vector<vector<int>> board(6, vector<int>(6));
    for (int r = 0; r < 6; ++r) {
        for (int c = 0; c < 6; ++c) {
            cin >> board[r][c];
        }
    }

    // Parse vehicles
    unordered_map<int, vector<pair<int, int>>> cells_by_id;
    for (int r = 0; r < 6; ++r) {
        for (int c = 0; c < 6; ++c) {
            int id = board[r][c];
            if (id != 0) {
                cells_by_id[id].push_back({r, c});
            }
        }
    }

    // Build vehicle info list, red car first
    vector<pair<VehicleInfo, pair<int, int>>> vehicles; // info and (row, col)
    for (auto& entry : cells_by_id) {
        int id = entry.first;
        auto& cells = entry.second;
        // Determine orientation
        bool horizontal = true;
        int row0 = cells[0].first;
        for (auto& p : cells) {
            if (p.first != row0) {
                horizontal = false;
                break;
            }
        }
        if (!horizontal) {
            int col0 = cells[0].second;
            for (auto& p : cells) {
                if (p.second != col0) {
                    // should not happen
                    horizontal = true; // fallback
                    break;
                }
            }
        }
        int length = cells.size();
        // Determine top-left / leftmost position
        int row, col;
        if (horizontal) {
            row = row0;
            vector<int> cols;
            for (auto& p : cells) cols.push_back(p.second);
            sort(cols.begin(), cols.end());
            col = cols[0];
        } else {
            col = cells[0].second;
            vector<int> rows;
            for (auto& p : cells) rows.push_back(p.first);
            sort(rows.begin(), rows.end());
            row = rows[0];
        }
        VehicleInfo vi{id, id == 1, horizontal, length};
        vehicles.push_back({vi, {row, col}});
    }

    // Sort by id, but red car (id=1) must be first
    sort(vehicles.begin(), vehicles.end(),
         [](const auto& a, const auto& b) {
             if (a.first.id == 1) return true;
             if (b.first.id == 1) return false;
             return a.first.id < b.first.id;
         });

    n = vehicles.size();
    infos.resize(n);
    State initial;
    initial.rows.resize(n);
    initial.cols.resize(n);
    for (int i = 0; i < n; ++i) {
        infos[i] = vehicles[i].first;
        initial.rows[i] = vehicles[i].second.first;
        initial.cols[i] = vehicles[i].second.second;
    }
    // red car row is fixed at 2 (third row)
    initial.rows[0] = 2;

    // Forward BFS to explore all reachable states
    unordered_set<uint64_t> visited;
    unordered_map<uint64_t, pair<uint64_t, Move>> parent; // child -> (parent, move)
    queue<State> q;
    vector<uint64_t> goal_keys;

    uint64_t init_key = encode(initial);
    visited.insert(init_key);
    q.push(initial);

    while (!q.empty()) {
        State s = q.front(); q.pop();
        uint64_t key = encode(s);
        // Check if goal state (red car completely out)
        if (s.cols[0] == 6) {
            goal_keys.push_back(key);
        }
        vector<Move> moves = generate_moves(s);
        for (Move& mv : moves) {
            State t = apply_move(s, mv.vid, mv.dir);
            uint64_t t_key = encode(t);
            if (!visited.count(t_key)) {
                visited.insert(t_key);
                parent[t_key] = {key, mv};
                q.push(t);
            }
        }
    }

    // Backward BFS to compute distances to goal
    unordered_map<uint64_t, int> dist;
    queue<uint64_t> dq;
    for (uint64_t gk : goal_keys) {
        dist[gk] = 0;
        dq.push(gk);
    }
    while (!dq.empty()) {
        uint64_t key = dq.front(); dq.pop();
        int d = dist[key];
        State s = decode(key);
        vector<Move> moves = generate_moves(s);
        for (Move& mv : moves) {
            State t = apply_move(s, mv.vid, mv.dir);
            uint64_t t_key = encode(t);
            if (visited.count(t_key) && dist.find(t_key) == dist.end()) {
                dist[t_key] = d + 1;
                dq.push(t_key);
            }
        }
    }

    // Find state with maximum distance
    int max_dist = -1;
    uint64_t best_key = init_key;
    for (uint64_t key : visited) {
        auto it = dist.find(key);
        if (it != dist.end()) {
            if (it->second > max_dist) {
                max_dist = it->second;
                best_key = key;
            }
        }
    }

    // Reconstruct path from initial to best state
    vector<Move> path;
    uint64_t cur = best_key;
    while (cur != init_key) {
        auto& p = parent[cur];
        path.push_back(p.second);
        cur = p.first;
    }
    reverse(path.begin(), path.end());

    // Output
    cout << max_dist << " " << path.size() << endl;
    for (Move& mv : path) {
        cout << infos[mv.vid].id << " " << mv.dir << endl;
    }

    return 0;
}