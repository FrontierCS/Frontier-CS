#include <bits/stdc++.h>
using namespace std;

struct Vehicle {
    bool horizontal;
    int length;
    int fixed; // row if horizontal, col if vertical
};

struct Move {
    int id; // 0-based index
    char dir; // 'L','R','U','D'
};

static const int N = 6;

int nVehicles;
vector<Vehicle> vehicles;

inline char opposite(char d) {
    if (d == 'L') return 'R';
    if (d == 'R') return 'L';
    if (d == 'U') return 'D';
    return 'U';
}

uint64_t pack_pos(const vector<int>& pos) {
    uint64_t code = 0;
    for (int i = 0; i < (int)pos.size(); ++i) {
        code |= (uint64_t)(pos[i] & 7) << (i * 3);
    }
    return code;
}

void unpack_pos(uint64_t code, vector<int>& pos) {
    for (int i = 0; i < (int)pos.size(); ++i) {
        pos[i] = (int)((code >> (i * 3)) & 7ULL);
    }
}

void build_board(const vector<int>& pos, int board[N][N]) {
    for (int r = 0; r < N; ++r) for (int c = 0; c < N; ++c) board[r][c] = 0;
    for (int i = 0; i < nVehicles; ++i) {
        const Vehicle& v = vehicles[i];
        if (v.horizontal) {
            int r = v.fixed;
            int c = pos[i];
            for (int k = 0; k < v.length; ++k) board[r][c + k] = i + 1;
        } else {
            int c = v.fixed;
            int r = pos[i];
            for (int k = 0; k < v.length; ++k) board[r + k][c] = i + 1;
        }
    }
}

void apply_move(vector<int>& pos, int board[N][N], int id, char dir) {
    Vehicle &v = vehicles[id];
    if (v.horizontal) {
        int r = v.fixed;
        int c = pos[id];
        if (dir == 'L') {
            // new left cell c-1 becomes id+1, old right cell c+len-1 becomes 0
            board[r][c + v.length - 1] = 0;
            board[r][c - 1] = id + 1;
            pos[id] = c - 1;
        } else if (dir == 'R') {
            board[r][c] = 0;
            board[r][c + v.length] = id + 1;
            pos[id] = c + 1;
        }
    } else {
        int c = v.fixed;
        int r = pos[id];
        if (dir == 'U') {
            board[r + v.length - 1][c] = 0;
            board[r - 1][c] = id + 1;
            pos[id] = r - 1;
        } else if (dir == 'D') {
            board[r][c] = 0;
            board[r + v.length][c] = id + 1;
            pos[id] = r + 1;
        }
    }
}

void list_moves(const vector<int>& pos, const int board[N][N], vector<Move>& moves) {
    moves.clear();
    for (int i = 0; i < nVehicles; ++i) {
        const Vehicle& v = vehicles[i];
        if (v.horizontal) {
            int r = v.fixed;
            int c = pos[i];
            if (c - 1 >= 0 && board[r][c - 1] == 0) moves.push_back({i, 'L'});
            if (c + v.length < N && board[r][c + v.length] == 0) moves.push_back({i, 'R'});
        } else {
            int c = v.fixed;
            int r = pos[i];
            if (r - 1 >= 0 && board[r - 1][c] == 0) moves.push_back({i, 'U'});
            if (r + v.length < N && board[r + v.length][c] == 0) moves.push_back({i, 'D'});
        }
    }
}

// Cache for evaluation
unordered_map<uint64_t, int> eval_cache;

// BFS to compute minimal unit steps to reach red car at [4,5] (pos[0]==4), then +2 to get totally out
int compute_difficulty_from_pos(const vector<int>& start_pos) {
    uint64_t start_code = pack_pos(start_pos);
    auto it = eval_cache.find(start_code);
    if (it != eval_cache.end()) return it->second;

    if (start_pos[0] == 4) {
        int res = 2; // two extra steps to get totally out
        eval_cache[start_code] = res;
        return res;
    }

    queue<uint64_t> q;
    unordered_map<uint64_t, int> dist;
    q.push(start_code);
    dist[start_code] = 0;

    vector<int> pos(nVehicles);
    int board[N][N];
    vector<Move> mv;

    while (!q.empty()) {
        uint64_t code = q.front(); q.pop();
        int d = dist[code];
        unpack_pos(code, pos);
        if (pos[0] == 4) {
            int res = d + 2;
            eval_cache[start_code] = res;
            return res;
        }
        build_board(pos, board);
        list_moves(pos, board, mv);
        for (const auto& m : mv) {
            vector<int> npos = pos;
            int nboard[N][N];
            // Copy board to nboard efficiently
            for (int r = 0; r < N; ++r) for (int c = 0; c < N; ++c) nboard[r][c] = board[r][c];
            apply_move(npos, nboard, m.id, m.dir);
            uint64_t ncode = pack_pos(npos);
            if (dist.find(ncode) == dist.end()) {
                dist[ncode] = d + 1;
                q.push(ncode);
            }
        }
    }

    // Should always be solvable; fallback
    int res = INT_MAX / 2;
    eval_cache[start_code] = res;
    return res;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int A[N][N];
    for (int r = 0; r < N; ++r) for (int c = 0; c < N; ++c) {
        if (!(cin >> A[r][c])) return 0;
    }

    // Determine number of vehicles
    int maxId = 0;
    for (int r = 0; r < N; ++r) for (int c = 0; c < N; ++c) maxId = max(maxId, A[r][c]);
    nVehicles = maxId;
    vehicles.resize(nVehicles);

    // Collect cells by id
    vector<vector<pair<int,int>>> cells(nVehicles + 1);
    for (int r = 0; r < N; ++r) for (int c = 0; c < N; ++c) {
        int id = A[r][c];
        if (id > 0) cells[id].push_back({r, c});
    }

    // Infer vehicle properties
    for (int id = 1; id <= nVehicles; ++id) {
        auto &v = vehicles[id - 1];
        auto &list = cells[id];
        // Determine orientation
        bool horiz = false;
        if (list.size() >= 2) {
            if (list[0].first == list[1].first) horiz = true;
            else horiz = false;
        } else {
            // Should not happen
            horiz = true;
        }
        v.horizontal = horiz;
        v.length = (int)list.size();
        if (horiz) {
            int row = list[0].first;
            for (auto &p : list) row = p.first; // they should be same
            v.fixed = row;
        } else {
            int col = list[0].second;
            for (auto &p : list) col = p.second; // they should be same
            v.fixed = col;
        }
    }

    // Initial positions
    vector<int> init_pos(nVehicles, 0);
    for (int id = 1; id <= nVehicles; ++id) {
        auto &v = vehicles[id - 1];
        if (v.horizontal) {
            int row = v.fixed;
            int minc = 6;
            for (int c = 0; c < N; ++c) if (A[row][c] == id) minc = min(minc, c);
            init_pos[id - 1] = (minc == 6 ? 0 : minc);
        } else {
            int col = v.fixed;
            int minr = 6;
            for (int r = 0; r < N; ++r) if (A[r][col] == id) minr = min(minr, r);
            init_pos[id - 1] = (minr == 6 ? 0 : minr);
        }
    }

    // Setup board for current state
    vector<int> cur_pos = init_pos;
    int board[N][N];
    build_board(cur_pos, board);

    // Random walk to find a hard state
    mt19937_64 rng(chrono::steady_clock::now().time_since_epoch().count());

    vector<Move> best_moves; // moves from initial to best state
    int best_difficulty = compute_difficulty_from_pos(cur_pos);

    vector<Move> path_moves; // current path from initial
    vector<uint64_t> path_states; // codes along the path, including initial state
    path_states.push_back(pack_pos(cur_pos));

    vector<Move> available_moves;

    auto start_time = chrono::steady_clock::now();
    const double TIME_LIMIT = 1.90; // seconds

    int steps_since_eval = 0;
    int reset_threshold = 800;

    while (true) {
        auto now = chrono::steady_clock::now();
        double elapsed = chrono::duration<double>(now - start_time).count();
        if (elapsed > TIME_LIMIT) break;

        list_moves(cur_pos, board, available_moves);

        // Avoid immediate backtracking
        if (!path_moves.empty()) {
            Move last = path_moves.back();
            // remove inverse move if exists
            for (size_t i = 0; i < available_moves.size(); ++i) {
                if (available_moves[i].id == last.id && available_moves[i].dir == opposite(last.dir)) {
                    // swap erase
                    available_moves.erase(available_moves.begin() + i);
                    break;
                }
            }
        }

        if (available_moves.empty()) {
            // Reset to initial
            cur_pos = init_pos;
            build_board(cur_pos, board);
            path_moves.clear();
            path_states.clear();
            path_states.push_back(pack_pos(cur_pos));
            continue;
        }

        uniform_int_distribution<int> disti(0, (int)available_moves.size() - 1);
        Move chosen = available_moves[disti(rng)];
        apply_move(cur_pos, board, chosen.id, chosen.dir);
        path_moves.push_back(chosen);
        path_states.push_back(pack_pos(cur_pos));

        steps_since_eval++;

        // Evaluate periodically
        if (steps_since_eval >= 3) {
            steps_since_eval = 0;
            int diff = compute_difficulty_from_pos(cur_pos);
            if (diff > best_difficulty) {
                best_difficulty = diff;
                best_moves = path_moves;
            }
        }

        if ((int)path_moves.size() >= reset_threshold) {
            // Reset to initial to avoid extremely long formation sequence
            cur_pos = init_pos;
            build_board(cur_pos, board);
            path_moves.clear();
            path_states.clear();
            path_states.push_back(pack_pos(cur_pos));
        }
    }

    // If no improvements found, best_moves may be empty; that's ok.
    // Compress best_moves by removing loops (states revisited)
    // We'll simulate from initial and remove cycles.
    vector<Move> compressed;
    vector<int> sim_pos = init_pos;
    int sim_board[N][N];
    build_board(sim_pos, sim_board);
    vector<uint64_t> state_stack;
    state_stack.push_back(pack_pos(sim_pos));
    unordered_map<uint64_t, int> pos_index; // code -> index in state_stack
    pos_index[state_stack.back()] = 0;

    for (size_t i = 0; i < best_moves.size(); ++i) {
        Move m = best_moves[i];
        apply_move(sim_pos, sim_board, m.id, m.dir);
        uint64_t code = pack_pos(sim_pos);
        auto it = pos_index.find(code);
        if (it != pos_index.end()) {
            int j = it->second;
            // Remove moves/states after j
            while ((int)state_stack.size() - 1 > j) {
                uint64_t remc = state_stack.back();
                pos_index.erase(remc);
                state_stack.pop_back();
                compressed.pop_back();
            }
            // Now code already exists at end; nothing to add
        } else {
            compressed.push_back(m);
            state_stack.push_back(code);
            pos_index[code] = (int)state_stack.size() - 1;
        }
    }

    // Output result
    cout << best_difficulty << " " << compressed.size() << "\n";
    for (auto &m : compressed) {
        cout << (m.id + 1) << " " << m.dir << "\n";
    }

    return 0;
}