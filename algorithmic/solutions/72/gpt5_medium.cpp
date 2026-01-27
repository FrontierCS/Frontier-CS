#include <bits/stdc++.h>
using namespace std;

struct Move {
    int id; // 1-based
    char dir; // 'L','R','U','D'
};

static const int NROWS = 6;
static const int NCOLS = 6;

int n; // number of vehicles
vector<int> lenv;       // length of each vehicle
vector<int> orient;     // 0 = horizontal, 1 = vertical
vector<int> fixedCoord; // for H: row; for V: col
// pos[i] = starting coordinate (for H: leftmost col, for V: topmost row)

inline uint64_t packState(const vector<int>& pos) {
    uint64_t key = 0;
    for (int i = n - 1; i >= 0; --i) {
        key <<= 4;
        key |= (uint64_t)(pos[i] & 0xF);
    }
    return key;
}
inline void unpackState(uint64_t key, vector<int>& pos) {
    for (int i = 0; i < n; ++i) {
        pos[i] = key & 0xF;
        key >>= 4;
    }
}

inline void buildGrid(const vector<int>& pos, uint8_t grid[6][6]) {
    for (int r = 0; r < 6; ++r) for (int c = 0; c < 6; ++c) grid[r][c] = 0;
    for (int i = 0; i < n; ++i) {
        if (orient[i] == 0) {
            int r = fixedCoord[i];
            for (int k = 0; k < lenv[i]; ++k) {
                int c = pos[i] + k;
                grid[r][c] = (uint8_t)(i + 1);
            }
        } else {
            int c = fixedCoord[i];
            for (int k = 0; k < lenv[i]; ++k) {
                int r = pos[i] + k;
                grid[r][c] = (uint8_t)(i + 1);
            }
        }
    }
}

inline bool clearToExit(const vector<int>& pos, uint8_t grid[6][6]) {
    int red_idx = 0;
    int s = pos[red_idx];
    int r = fixedCoord[red_idx]; // row 2
    for (int c = s + lenv[red_idx]; c < 6; ++c) {
        if (grid[r][c] != 0) return false;
    }
    return true;
}

unordered_map<uint64_t, int> solve_cache;

int bfs_min_solve_steps(const vector<int>& start_pos) {
    uint64_t start_key = packState(start_pos);
    auto itc = solve_cache.find(start_key);
    if (itc != solve_cache.end()) return itc->second;

    uint8_t grid[6][6];
    vector<int> pos(n);

    unordered_set<uint64_t> visited;
    visited.reserve(100000);
    queue<pair<uint64_t, int>> q;
    q.push({start_key, 0});
    visited.insert(start_key);

    int bestAns = INT_MAX;

    while (!q.empty()) {
        auto [key, dist] = q.front(); q.pop();
        if (bestAns != INT_MAX && dist >= bestAns - 2) break;

        unpackState(key, pos);
        buildGrid(pos, grid);

        // Check if path to exit is clear; if so candidate = dist + (6 - s)
        if (clearToExit(pos, grid)) {
            int s = pos[0];
            int add = 6 - s; // steps to move red fully out
            int cand = dist + add;
            if (cand < bestAns) bestAns = cand;
        }

        // Generate neighbors (unit moves)
        for (int i = 0; i < n; ++i) {
            if (orient[i] == 0) {
                int r = fixedCoord[i];
                // Left
                if (pos[i] - 1 >= 0 && grid[r][pos[i] - 1] == 0) {
                    pos[i]--;
                    uint64_t nk = packState(pos);
                    if (!visited.count(nk)) {
                        visited.insert(nk);
                        q.push({nk, dist + 1});
                    }
                    pos[i]++;
                }
                // Right
                if (pos[i] + lenv[i] <= 5 && grid[r][pos[i] + lenv[i]] == 0) {
                    pos[i]++;
                    uint64_t nk = packState(pos);
                    if (!visited.count(nk)) {
                        visited.insert(nk);
                        q.push({nk, dist + 1});
                    }
                    pos[i]--;
                }
            } else {
                int c = fixedCoord[i];
                // Up
                if (pos[i] - 1 >= 0 && grid[pos[i] - 1][c] == 0) {
                    pos[i]--;
                    uint64_t nk = packState(pos);
                    if (!visited.count(nk)) {
                        visited.insert(nk);
                        q.push({nk, dist + 1});
                    }
                    pos[i]++;
                }
                // Down
                if (pos[i] + lenv[i] <= 5 && grid[pos[i] + lenv[i]][c] == 0) {
                    pos[i]++;
                    uint64_t nk = packState(pos);
                    if (!visited.count(nk)) {
                        visited.insert(nk);
                        q.push({nk, dist + 1});
                    }
                    pos[i]--;
                }
            }
        }
    }

    if (bestAns == INT_MAX) bestAns = 1000000000; // should not happen

    solve_cache[start_key] = bestAns;
    return bestAns;
}

inline void legalMoves(const vector<int>& pos, vector<Move>& outMoves) {
    outMoves.clear();
    uint8_t grid[6][6];
    buildGrid(pos, grid);
    for (int i = 0; i < n; ++i) {
        if (orient[i] == 0) {
            int r = fixedCoord[i];
            if (pos[i] - 1 >= 0 && grid[r][pos[i] - 1] == 0) {
                outMoves.push_back({i + 1, 'L'});
            }
            if (pos[i] + lenv[i] <= 5 && grid[r][pos[i] + lenv[i]] == 0) {
                outMoves.push_back({i + 1, 'R'});
            }
        } else {
            int c = fixedCoord[i];
            if (pos[i] - 1 >= 0 && grid[pos[i] - 1][c] == 0) {
                outMoves.push_back({i + 1, 'U'});
            }
            if (pos[i] + lenv[i] <= 5 && grid[pos[i] + lenv[i]][c] == 0) {
                outMoves.push_back({i + 1, 'D'});
            }
        }
    }
}

inline void applyMove(vector<int>& pos, const Move& mv) {
    int idx = mv.id - 1;
    if (mv.dir == 'L') pos[idx]--;
    else if (mv.dir == 'R') pos[idx]++;
    else if (mv.dir == 'U') pos[idx]--;
    else if (mv.dir == 'D') pos[idx]++;
}

inline char oppositeDir(char d) {
    if (d == 'L') return 'R';
    if (d == 'R') return 'L';
    if (d == 'U') return 'D';
    if (d == 'D') return 'U';
    return d;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int board[6][6];
    for (int r = 0; r < 6; ++r) {
        for (int c = 0; c < 6; ++c) {
            if (!(cin >> board[r][c])) return 0;
        }
    }

    int max_id = 0;
    for (int r = 0; r < 6; ++r) {
        for (int c = 0; c < 6; ++c) {
            max_id = max(max_id, board[r][c]);
        }
    }
    n = max_id;
    if (n == 0) {
        cout << 0 << " " << 0 << "\n";
        return 0;
    }

    vector<int> minR(n + 1, 6), maxR(n + 1, -1), minC(n + 1, 6), maxC(n + 1, -1), cnt(n + 1, 0);
    for (int r = 0; r < 6; ++r) {
        for (int c = 0; c < 6; ++c) {
            int id = board[r][c];
            if (id > 0) {
                cnt[id]++;
                minR[id] = min(minR[id], r);
                maxR[id] = max(maxR[id], r);
                minC[id] = min(minC[id], c);
                maxC[id] = max(maxC[id], c);
            }
        }
    }

    lenv.assign(n, 0);
    orient.assign(n, 0);
    fixedCoord.assign(n, 0);
    vector<int> pos(n, 0);

    for (int id = 1; id <= n; ++id) {
        int i = id - 1;
        if (minR[id] == maxR[id]) {
            orient[i] = 0; // H
            lenv[i] = cnt[id];
            fixedCoord[i] = minR[id];
            pos[i] = minC[id];
        } else {
            orient[i] = 1; // V
            lenv[i] = cnt[id];
            fixedCoord[i] = minC[id];
            pos[i] = minR[id];
        }
    }

    // Prepare RNG and timing
    mt19937 rng((uint32_t)chrono::steady_clock::now().time_since_epoch().count());
    auto start_time = chrono::steady_clock::now();
    const double TIME_LIMIT = 1.90; // seconds
    auto time_now = [&]() {
        return chrono::duration<double>(chrono::steady_clock::now() - start_time).count();
    };

    vector<int> best_pos = pos;
    vector<Move> best_path;
    int best_difficulty = bfs_min_solve_steps(pos);

    const int MAX_STEPS_PER_WALK = 300;
    const int EVAL_PERIOD = 10;

    vector<Move> moves_buf;
    vector<Move> legal;
    legal.reserve(64);

    while (time_now() < TIME_LIMIT) {
        vector<int> cur_pos = pos;
        vector<Move> cur_path;
        Move last_mv = { -1, '?' };

        int steps = 0;
        while (steps < MAX_STEPS_PER_WALK && time_now() < TIME_LIMIT) {
            legalMoves(cur_pos, legal);
            if (legal.empty()) break;

            // avoid immediate reverse if possible
            vector<int> indices;
            indices.reserve(legal.size());
            for (int i = 0; i < (int)legal.size(); ++i) {
                if (last_mv.id != -1 && legal[i].id == last_mv.id && legal[i].dir == oppositeDir(last_mv.dir)) {
                    continue;
                }
                indices.push_back(i);
            }
            int choose_idx;
            if (!indices.empty()) {
                uniform_int_distribution<int> dist(0, (int)indices.size() - 1);
                choose_idx = indices[dist(rng)];
            } else {
                uniform_int_distribution<int> dist(0, (int)legal.size() - 1);
                choose_idx = dist(rng);
            }

            Move mv = legal[choose_idx];
            applyMove(cur_pos, mv);
            cur_path.push_back(mv);
            last_mv = mv;
            steps++;

            if (steps % EVAL_PERIOD == 0 || steps == MAX_STEPS_PER_WALK) {
                int d = bfs_min_solve_steps(cur_pos);
                if (d > best_difficulty) {
                    best_difficulty = d;
                    best_pos = cur_pos;
                    best_path = cur_path;
                }
            }
        }
        // evaluate at end of walk if not already
        int d = bfs_min_solve_steps(cur_pos);
        if (d > best_difficulty) {
            best_difficulty = d;
            best_pos = cur_pos;
            best_path = cur_path;
        }
    }

    cout << best_difficulty << " " << best_path.size() << "\n";
    for (auto &mv : best_path) {
        cout << mv.id << " " << mv.dir << "\n";
    }

    return 0;
}