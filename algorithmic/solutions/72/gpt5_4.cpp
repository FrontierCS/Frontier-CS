#include <bits/stdc++.h>
using namespace std;

struct Step {
    int vid; // 0-based
    int delta; // -1 or +1
    char dir; // 'L','R','U','D'
};

struct VecHash {
    size_t operator()(const vector<int>& v) const noexcept {
        uint64_t h = 1469598103934665603ULL;
        for (int x : v) {
            h ^= (uint64_t)(x + 1);
            h *= 1099511628211ULL;
        }
        return (size_t)h;
    }
};

static const int NROWS = 6;
static const int NCOLS = 6;

int n; // number of vehicles
vector<int> vlen; // length of vehicles
vector<char> vorient; // 'H' or 'V'
vector<int> vfix; // fixed row if H, fixed col if V
vector<int> vmaxpos; // maximum anchor position
int redRow; // row of red car (id=1, index 0)
mt19937 rng((uint32_t)chrono::high_resolution_clock::now().time_since_epoch().count());

inline uint64_t encode_key(const vector<int>& pos) {
    // Use 3 bits per vehicle (0..7), enough since pos in 0..5
    uint64_t key = 0;
    for (int i = 0; i < (int)pos.size(); ++i) {
        key |= (uint64_t)(pos[i] & 7) << (3 * i);
    }
    return key;
}
inline void decode_key(uint64_t key, vector<int>& pos) {
    for (int i = 0; i < (int)pos.size(); ++i) {
        pos[i] = (int)((key >> (3 * i)) & 7ULL);
    }
}

inline void fill_board(const vector<int>& pos, int grid[6][6]) {
    for (int r = 0; r < 6; ++r) for (int c = 0; c < 6; ++c) grid[r][c] = 0;
    for (int i = 0; i < n; ++i) {
        if (vorient[i] == 'H') {
            int r = vfix[i];
            int c0 = pos[i];
            for (int a = 0; a < vlen[i]; ++a) grid[r][c0 + a] = i + 1;
        } else {
            int c = vfix[i];
            int r0 = pos[i];
            for (int a = 0; a < vlen[i]; ++a) grid[r0 + a][c] = i + 1;
        }
    }
}

inline void list_moves(const vector<int>& pos, vector<Step>& moves) {
    moves.clear();
    static int grid[6][6];
    fill_board(pos, grid);
    for (int i = 0; i < n; ++i) {
        if (vorient[i] == 'H') {
            int r = vfix[i];
            int c0 = pos[i];
            // move left
            if (c0 - 1 >= 0 && grid[r][c0 - 1] == 0) {
                moves.push_back({i, -1, 'L'});
            }
            // move right
            if (c0 + vlen[i] <= 5 && grid[r][c0 + vlen[i]] == 0) {
                moves.push_back({i, +1, 'R'});
            }
        } else { // 'V'
            int c = vfix[i];
            int r0 = pos[i];
            // move up
            if (r0 - 1 >= 0 && grid[r0 - 1][c] == 0) {
                moves.push_back({i, -1, 'U'});
            }
            // move down
            if (r0 + vlen[i] <= 5 && grid[r0 + vlen[i]][c] == 0) {
                moves.push_back({i, +1, 'D'});
            }
        }
    }
}

struct EvalInfo {
    int lb; // lower bound
    int blockers;
    int red_left;
};

inline EvalInfo evaluate_lb(const vector<int>& pos) {
    static int grid[6][6];
    fill_board(pos, grid);
    int red_left = pos[0];
    int red_right = red_left + vlen[0] - 1; // len=2 for red
    int blockers = 0;
    bool seen[11] = {false};
    for (int c = red_right + 1; c < 6; ++c) {
        int id = grid[redRow][c];
        if (id != 0 && id != 1 && !seen[id]) {
            seen[id] = true;
            blockers++;
        }
    }
    int lb = (6 - red_left) + blockers;
    return {lb, blockers, red_left};
}

inline bool corridor_clear(const vector<int>& pos) {
    static int grid[6][6];
    fill_board(pos, grid);
    int red_left = pos[0];
    int red_right = red_left + vlen[0] - 1;
    for (int c = red_right + 1; c < 6; ++c) {
        if (grid[redRow][c] != 0) return false;
    }
    return true;
}

int solve_min_steps_from_state(const vector<int>& start_pos, double time_limit_ms = 1e9) {
    // BFS in state space; for any state with corridor clear, candidate answer = d + (6 - red_left)
    auto ts = chrono::high_resolution_clock::now();
    uint64_t start_key = encode_key(start_pos);

    unordered_map<uint64_t, uint16_t> dist;
    dist.reserve(100000);
    queue<uint64_t> q;
    q.push(start_key);
    dist[start_key] = 0;

    int best = INT_MAX;

    vector<int> cur(n), nxt(n);
    vector<Step> moves;
    moves.reserve(64);

    while (!q.empty()) {
        // Time check
        if (dist.size() % 8192 == 0) {
            auto now = chrono::high_resolution_clock::now();
            double ms = chrono::duration<double, std::milli>(now - ts).count();
            if (ms > time_limit_ms) break;
        }

        uint64_t key = q.front(); q.pop();
        decode_key(key, cur);
        int d = dist[key];

        // early pruning
        if (best != INT_MAX) {
            // minimal extra is 2 (when red reaches rightmost inside board)
            if (d >= best - 2) {
                continue;
            }
        }

        // check corridor clear
        static int grid[6][6];
        fill_board(cur, grid);
        int red_left = cur[0];
        int red_right = red_left + vlen[0] - 1;
        bool clear = true;
        for (int c = red_right + 1; c < 6; ++c) {
            if (grid[redRow][c] != 0) { clear = false; break; }
        }
        if (clear) {
            int extra = 6 - red_left;
            int cand = d + extra;
            if (cand < best) best = cand;
            if (d >= best - 2) continue;
        }

        // expand neighbors
        list_moves(cur, moves);
        for (const auto& st : moves) {
            nxt = cur;
            nxt[st.vid] += st.delta;
            // boundary check just in case
            if (nxt[st.vid] < 0 || nxt[st.vid] > vmaxpos[st.vid]) continue;
            uint64_t nk = encode_key(nxt);
            if (dist.find(nk) == dist.end()) {
                dist[nk] = (uint16_t)(d + 1);
                q.push(nk);
            }
        }
    }
    if (best == INT_MAX) {
        // Should not happen for solvable instances; return a large number
        return 1000000000;
    }
    return best;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int board[6][6];
    int max_id = 0;
    for (int r = 0; r < 6; ++r) {
        for (int c = 0; c < 6; ++c) {
            int x;
            if (!(cin >> x)) x = 0;
            board[r][c] = x;
            max_id = max(max_id, x);
        }
    }
    n = max_id;
    if (n <= 0) {
        // no vehicles; trivial
        cout << 0 << " " << 0 << "\n";
        return 0;
    }

    vector<vector<pair<int,int>>> cells(n + 1);
    for (int r = 0; r < 6; ++r) {
        for (int c = 0; c < 6; ++c) {
            int id = board[r][c];
            if (id > 0) cells[id].push_back({r, c});
        }
    }

    vlen.assign(n, 0);
    vorient.assign(n, 'H');
    vfix.assign(n, 0);
    vmaxpos.assign(n, 0);
    vector<int> pos0(n, 0);

    for (int id = 1; id <= n; ++id) {
        auto &vec = cells[id];
        if (vec.empty()) continue;
        int len = (int)vec.size();
        vlen[id - 1] = len;
        // determine orientation
        bool same_row = true, same_col = true;
        int r0 = vec[0].first, c0 = vec[0].second;
        for (auto &p : vec) {
            if (p.first != r0) same_row = false;
            if (p.second != c0) same_col = false;
        }
        if (same_row) {
            vorient[id - 1] = 'H';
            int row = r0;
            int minc = 100;
            for (auto &p : vec) minc = min(minc, p.second);
            vfix[id - 1] = row;
            pos0[id - 1] = minc;
            vmaxpos[id - 1] = 6 - len;
        } else if (same_col) {
            vorient[id - 1] = 'V';
            int col = c0;
            int minr = 100;
            for (auto &p : vec) minr = min(minr, p.first);
            vfix[id - 1] = col;
            pos0[id - 1] = minr;
            vmaxpos[id - 1] = 6 - len;
        } else {
            // Invalid, but proceed
            vorient[id - 1] = 'H';
            vfix[id - 1] = r0;
            pos0[id - 1] = c0;
            vmaxpos[id - 1] = 6 - len;
        }
    }
    redRow = vfix[0]; // red car row

    // Random walk to find candidate states
    auto t_start = chrono::high_resolution_clock::now();
    double total_ms = 1950.0;
    double phase1_ms = 1100.0; // exploration
    double phase2_ms = total_ms - phase1_ms - 50.0; // reserve for final BFS and output

    vector<int> cur = pos0;
    vector<Step> move_seq; move_seq.reserve(100000);
    vector<int> score_seq; score_seq.reserve(100000);

    struct Cand {
        uint64_t key;
        int idx; // index into move_seq
        int lb;
        int score;
    };
    auto cmp_cand = [](const Cand& a, const Cand& b){
        if (a.lb != b.lb) return a.lb < b.lb;
        return a.score < b.score;
    };
    const int MAXC = 40;
    multiset<Cand, decltype(cmp_cand)> topCands(cmp_cand);
    unordered_set<uint64_t> cand_set;
    cand_set.reserve(1024);

    auto add_candidate = [&](uint64_t key, int idx, int lb, int score){
        if (cand_set.find(key) != cand_set.end()) return;
        Cand cd{key, idx, lb, score};
        topCands.insert(cd);
        cand_set.insert(key);
        if ((int)topCands.size() > MAXC) {
            auto it = topCands.begin();
            cand_set.erase(it->key);
            topCands.erase(it);
        }
    };

    // Include initial state as candidate
    {
        auto ev = evaluate_lb(cur);
        int score = ev.lb + 2 * ev.blockers;
        add_candidate(encode_key(cur), 0, ev.lb, score);
    }

    Step lastMove{-1, 0, '?'};
    vector<Step> moves;
    moves.reserve(64);

    // exploration
    while (true) {
        auto now = chrono::high_resolution_clock::now();
        double ms = chrono::duration<double, std::milli>(now - t_start).count();
        if (ms > phase1_ms) break;

        list_moves(cur, moves);
        if (moves.empty()) break;
        // choose a move: avoid immediate reverse
        vector<int> cand_idx;
        cand_idx.reserve(moves.size());
        for (int i = 0; i < (int)moves.size(); ++i) {
            const Step& st = moves[i];
            if (lastMove.vid == st.vid && lastMove.delta + st.delta == 0) continue;
            cand_idx.push_back(i);
        }
        int pickIndex = -1;
        if (!cand_idx.empty()) {
            uniform_int_distribution<int> dist(0, (int)cand_idx.size() - 1);
            pickIndex = cand_idx[dist(rng)];
        } else {
            uniform_int_distribution<int> dist(0, (int)moves.size() - 1);
            pickIndex = dist(rng);
        }
        Step st = moves[pickIndex];
        // apply
        cur[st.vid] += st.delta;
        move_seq.push_back(st);
        lastMove = st;

        // Evaluate and maybe store as candidate
        auto ev = evaluate_lb(cur);
        int score = ev.lb + 2 * ev.blockers;
        score_seq.push_back(score);
        add_candidate(encode_key(cur), (int)move_seq.size(), ev.lb, score);
    }

    // Build an ordered list of candidates (best first)
    vector<Cand> cands(topCands.begin(), topCands.end());
    sort(cands.begin(), cands.end(), [](const Cand& a, const Cand& b){
        if (a.lb != b.lb) return a.lb > b.lb;
        return a.score > b.score;
    });

    // Append current state as candidate too (in case it wasn't)
    {
        auto ev = evaluate_lb(cur);
        int score = ev.lb + 2 * ev.blockers;
        uint64_t key = encode_key(cur);
        if (cand_set.find(key) == cand_set.end()) {
            cands.push_back({key, (int)move_seq.size(), ev.lb, score});
        }
    }

    // Always include initial state
    uint64_t init_key = encode_key(pos0);
    bool has_init = false;
    for (auto &cd : cands) if (cd.key == init_key) { has_init = true; break; }
    if (!has_init) {
        auto ev = evaluate_lb(pos0);
        int sc = ev.lb + 2 * ev.blockers;
        cands.push_back({init_key, 0, ev.lb, sc});
    }

    // Phase 2: compute exact minimal steps for best candidates within time
    int best_exact = -1;
    int best_idx = 0;
    uint64_t best_key = init_key;

    // Ensure initial state's exact is computed first as fallback
    {
        int exact = solve_min_steps_from_state(pos0, phase2_ms);
        best_exact = exact;
        best_idx = 0;
        best_key = init_key;
    }

    auto t_mid = chrono::high_resolution_clock::now();
    double elapsed_ms = chrono::duration<double, std::milli>(t_mid - t_start).count();
    double remaining_ms = total_ms - elapsed_ms - 25.0; // reserve 25ms for output
    if (remaining_ms < 0) remaining_ms = 0;

    // Evaluate candidates
    for (auto &cd : cands) {
        if (remaining_ms <= 5.0) break;
        if (cd.key == init_key && cd.idx == 0) continue; // already computed

        vector<int> sp(n);
        decode_key(cd.key, sp);
        auto t0 = chrono::high_resolution_clock::now();
        int exact = solve_min_steps_from_state(sp, remaining_ms * 0.9);
        auto t1 = chrono::high_resolution_clock::now();
        double used = chrono::duration<double, std::milli>(t1 - t0).count();
        remaining_ms -= used;
        if (exact > best_exact) {
            best_exact = exact;
            best_idx = cd.idx;
            best_key = cd.key;
        }
        if (remaining_ms <= 5.0) break;
    }

    // Output
    cout << best_exact << " " << best_idx << "\n";
    for (int i = 0; i < best_idx; ++i) {
        const Step& st = move_seq[i];
        cout << (st.vid + 1) << " " << st.dir << "\n";
    }
    return 0;
}