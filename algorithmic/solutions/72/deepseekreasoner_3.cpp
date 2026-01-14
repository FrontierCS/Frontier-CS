#include <iostream>
#include <vector>
#include <queue>
#include <unordered_map>
#include <unordered_set>
#include <algorithm>
#include <cstring>

using namespace std;

struct Vehicle {
    int id;
    char orient; // 'H' or 'V'
    int len;
    int fixed; // row for H, col for V
    int init_pos; // leftmost col for H, topmost row for V
};

vector<Vehicle> veh; // vehicles, index 0 is the red car
int n; // number of vehicles

// pack state into 32-bit integer (3 bits per vehicle)
uint32_t pack(const vector<int>& pos) {
    uint32_t key = 0;
    for (int i = 0; i < n; ++i) {
        key |= (pos[i] << (3 * i));
    }
    return key;
}

vector<int> unpack(uint32_t key) {
    vector<int> pos(n);
    for (int i = 0; i < n; ++i) {
        pos[i] = (key >> (3 * i)) & 7;
    }
    return pos;
}

// generate all possible moves from a given state
vector<pair<int, char>> generate_moves(const vector<int>& pos) {
    bool occ[6][6] = {false};
    for (int i = 0; i < n; ++i) {
        const Vehicle& v = veh[i];
        int p = pos[i];
        if (v.orient == 'H') {
            for (int c = p; c < p + v.len; ++c)
                occ[v.fixed][c] = true;
        } else {
            for (int r = p; r < p + v.len; ++r)
                occ[r][v.fixed] = true;
        }
    }
    vector<pair<int, char>> moves;
    for (int i = 0; i < n; ++i) {
        const Vehicle& v = veh[i];
        int p = pos[i];
        if (v.orient == 'H') {
            // left
            if (p > 0 && !occ[v.fixed][p - 1])
                moves.push_back({i, 'L'});
            // right
            if (p + v.len < 6 && !occ[v.fixed][p + v.len])
                moves.push_back({i, 'R'});
        } else {
            // up
            if (p > 0 && !occ[p - 1][v.fixed])
                moves.push_back({i, 'U'});
            // down
            if (p + v.len < 6 && !occ[p + v.len][v.fixed])
                moves.push_back({i, 'D'});
        }
    }
    return moves;
}

int main() {
    // read board
    int board[6][6];
    int max_id = 0;
    for (int r = 0; r < 6; ++r)
        for (int c = 0; c < 6; ++c) {
            cin >> board[r][c];
            if (board[r][c] > max_id) max_id = board[r][c];
        }

    // identify vehicles
    unordered_map<int, vector<pair<int, int>>> cells;
    for (int r = 0; r < 6; ++r)
        for (int c = 0; c < 6; ++c) {
            int id = board[r][c];
            if (id != 0)
                cells[id].push_back({r, c});
        }

    // create vehicle structures
    for (int id = 1; id <= max_id; ++id) {
        if (cells.find(id) == cells.end()) continue;
        auto& list = cells[id];
        // determine orientation
        bool same_row = true, same_col = true;
        int r0 = list[0].first, c0 = list[0].second;
        for (auto& p : list) {
            if (p.first != r0) same_row = false;
            if (p.second != c0) same_col = false;
        }
        char orient;
        if (same_row) orient = 'H';
        else if (same_col) orient = 'V';
        // should be one of them
        int len = list.size();
        int fixed, init_pos;
        if (orient == 'H') {
            int min_c = 6, max_c = -1;
            for (auto& p : list) {
                min_c = min(min_c, p.second);
                max_c = max(max_c, p.second);
            }
            fixed = r0;
            init_pos = min_c;
        } else {
            int min_r = 6, max_r = -1;
            for (auto& p : list) {
                min_r = min(min_r, p.first);
                max_r = max(max_r, p.first);
            }
            fixed = c0;
            init_pos = min_r;
        }
        veh.push_back({id, orient, len, fixed, init_pos});
    }
    n = veh.size();
    // reorder so that red car (id=1) is index 0
    for (int i = 0; i < n; ++i) {
        if (veh[i].id == 1) {
            swap(veh[i], veh[0]);
            break;
        }
    }

    // initial state positions
    vector<int> init_pos(n);
    for (int i = 0; i < n; ++i)
        init_pos[i] = veh[i].init_pos;
    uint32_t init_key = pack(init_pos);

    // BFS from initial state to collect all reachable states
    unordered_set<uint32_t> visited;
    unordered_map<uint32_t, uint32_t> parent_key;
    unordered_map<uint32_t, pair<int, char>> parent_move;
    unordered_map<uint32_t, int> depth_map;
    queue<pair<uint32_t, int>> q; // (state_key, depth)
    vector<uint32_t> goal_states;

    visited.insert(init_key);
    depth_map[init_key] = 0;
    q.push({init_key, 0});

    while (!q.empty()) {
        auto [key, depth] = q.front(); q.pop();
        vector<int> pos = unpack(key);
        // check if this is a goal state (red car at exit position)
        if (pos[0] == 4) { // leftmost column of red car is 4 (0-indexed)
            goal_states.push_back(key);
        }
        auto moves = generate_moves(pos);
        for (auto& mv : moves) {
            int idx = mv.first;
            char dir = mv.second;
            vector<int> new_pos = pos;
            if (dir == 'L') new_pos[idx]--;
            else if (dir == 'R') new_pos[idx]++;
            else if (dir == 'U') new_pos[idx]--;
            else if (dir == 'D') new_pos[idx]++;
            uint32_t new_key = pack(new_pos);
            if (visited.find(new_key) == visited.end()) {
                visited.insert(new_key);
                parent_key[new_key] = key;
                parent_move[new_key] = {idx, dir};
                depth_map[new_key] = depth + 1;
                q.push({new_key, depth + 1});
            }
        }
    }

    // Multi-source BFS from all goal states to compute distances
    unordered_map<uint32_t, int> dist;
    queue<uint32_t> qdist;
    for (uint32_t g : goal_states) {
        dist[g] = 0;
        qdist.push(g);
    }
    while (!qdist.empty()) {
        uint32_t key = qdist.front(); qdist.pop();
        int d = dist[key];
        vector<int> pos = unpack(key);
        auto moves = generate_moves(pos);
        for (auto& mv : moves) {
            int idx = mv.first;
            char dir = mv.second;
            vector<int> new_pos = pos;
            if (dir == 'L') new_pos[idx]--;
            else if (dir == 'R') new_pos[idx]++;
            else if (dir == 'U') new_pos[idx]--;
            else if (dir == 'D') new_pos[idx]++;
            uint32_t new_key = pack(new_pos);
            if (visited.find(new_key) != visited.end() && dist.find(new_key) == dist.end()) {
                dist[new_key] = d + 1;
                qdist.push(new_key);
            }
        }
    }

    // Find state with maximum solution steps (dist + 1)
    uint32_t best_key = init_key;
    int best_solution_steps = 0;
    for (uint32_t key : visited) {
        if (dist.find(key) != dist.end()) {
            int sol_steps = dist[key] + 1; // include the final exit move
            if (sol_steps > best_solution_steps) {
                best_solution_steps = sol_steps;
                best_key = key;
            }
        }
    }

    // Reconstruct the transformation path
    vector<pair<int, char>> seq;
    uint32_t cur = best_key;
    while (cur != init_key) {
        auto& mv = parent_move[cur];
        int idx = mv.first;
        char dir = mv.second;
        seq.push_back({veh[idx].id, dir});
        cur = parent_key[cur];
    }
    reverse(seq.begin(), seq.end());

    // Output
    cout << best_solution_steps << " " << seq.size() << endl;
    for (auto& p : seq) {
        cout << p.first << " " << p.second << endl;
    }

    return 0;
}