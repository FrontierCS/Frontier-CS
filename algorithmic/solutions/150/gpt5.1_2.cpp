#include <bits/stdc++.h>
using namespace std;

struct Placement {
    uint16_t sid;  // string id
    uint8_t len;   // length of string
    uint8_t dir;   // 0: horizontal, 1: vertical
    uint8_t i, j;  // start position
};

struct AdjEntry {
    int pid;       // placement id
    uint8_t idx;   // index in string
};

struct PlChange {
    int pid;
    uint8_t old_unsat;
};

static uint64_t rng_state = 88172645463325252ull;
inline uint64_t rng() {
    rng_state ^= rng_state << 7;
    rng_state ^= rng_state >> 9;
    return rng_state;
}
inline double rand01() {
    return (rng() >> 11) * (1.0 / (1ULL << 53));
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, M;
    if (!(cin >> N >> M)) return 0;
    vector<string> S(M);
    for (int i = 0; i < M; i++) cin >> S[i];

    const int NN = N * N;

    // Build placements and adjacency
    vector<Placement> placements;
    placements.reserve(M * 2 * N * N);
    vector<vector<AdjEntry>> adj(NN);

    for (int sid = 0; sid < M; sid++) {
        int len = (int)S[sid].size();
        uint8_t len8 = (uint8_t)len;
        for (int dir = 0; dir < 2; dir++) {
            for (int i = 0; i < N; i++) {
                for (int j = 0; j < N; j++) {
                    Placement pl;
                    pl.sid = (uint16_t)sid;
                    pl.len = len8;
                    pl.dir = (uint8_t)dir;
                    pl.i = (uint8_t)i;
                    pl.j = (uint8_t)j;
                    int pid = (int)placements.size();
                    placements.push_back(pl);
                    for (int idx = 0; idx < len; idx++) {
                        int r, c;
                        if (dir == 0) { // horizontal
                            r = i;
                            c = (j + idx) % N;
                        } else {        // vertical
                            r = (i + idx) % N;
                            c = j;
                        }
                        int pos = r * N + c;
                        adj[pos].push_back(AdjEntry{pid, (uint8_t)idx});
                    }
                }
            }
        }
    }

    int P = (int)placements.size();

    // Initialize grid randomly (letters A-H)
    string grid(NN, 'A');
    for (int pos = 0; pos < NN; pos++) {
        grid[pos] = char('A' + (rng() % 8));
    }

    // Initialize unsatisfied counts and satisfied placement counts per string
    vector<uint8_t> unsat(P);
    vector<int> satisfied_placements_per_str(M, 0);

    for (int pid = 0; pid < P; pid++) {
        const Placement &pl = placements[pid];
        uint8_t ct = 0;
        int base_i = pl.i;
        int base_j = pl.j;
        int dir = pl.dir;
        const string &str = S[pl.sid];
        for (int idx = 0; idx < pl.len; idx++) {
            int r = (dir == 0) ? base_i : (base_i + idx) % N;
            int c = (dir == 0) ? (base_j + idx) % N : base_j;
            char ch = grid[r * N + c];
            char need = str[idx];
            if (ch != need) ct++;
        }
        unsat[pid] = ct;
        if (ct == 0) satisfied_placements_per_str[pl.sid]++;
    }

    int currentC = 0;
    for (int sid = 0; sid < M; sid++) {
        if (satisfied_placements_per_str[sid] > 0) currentC++;
    }

    // Simulated annealing
    const double TIME_LIMIT = 1.9;
    const double T0 = 3.0;
    const double T_end = 0.1;
    const double invTL = 1.0 / TIME_LIMIT;

    auto time_start = chrono::steady_clock::now();

    vector<int> touched_sids;
    touched_sids.reserve(1024);
    vector<int> delta_satisfied(M);
    vector<char> sid_marked(M, 0);
    vector<PlChange> pl_changes;
    pl_changes.reserve(4096);

    while (true) {
        auto now = chrono::steady_clock::now();
        double elapsed = chrono::duration<double>(now - time_start).count();
        if (elapsed > TIME_LIMIT) break;
        double progress = elapsed * invTL;
        double temp = T0 + (T_end - T0) * progress;

        int pos = (int)(rng() % NN);
        char old_char = grid[pos];
        char new_char = char('A' + (rng() % 8));
        if (new_char == old_char) continue;

        auto &adj_list = adj[pos];
        if (adj_list.empty()) {
            grid[pos] = new_char;
            continue;
        }

        touched_sids.clear();
        pl_changes.clear();

        for (const AdjEntry &e : adj_list) {
            int pid = e.pid;
            int sid = placements[pid].sid;
            uint8_t idx = e.idx;
            char need = S[sid][idx];

            bool was_mis = (old_char != need);
            bool new_mis = (new_char != need);
            if (was_mis == new_mis) continue;  // no change in this placement

            if (!sid_marked[sid]) {
                sid_marked[sid] = 1;
                touched_sids.push_back(sid);
                delta_satisfied[sid] = 0;
            }

            uint8_t old_u = unsat[pid];
            uint8_t new_u;
            if (was_mis && !new_mis) {
                new_u = uint8_t(old_u - 1);
                if (new_u == 0) {
                    delta_satisfied[sid]++;
                }
            } else { // !was_mis && new_mis
                if (old_u == 0) {
                    delta_satisfied[sid]--;
                }
                new_u = uint8_t(old_u + 1);
            }

            pl_changes.push_back(PlChange{pid, old_u});
            unsat[pid] = new_u;
        }

        if (pl_changes.empty()) {
            // No placement satisfaction changed; commit char change
            grid[pos] = new_char;
            continue;
        }

        int newC = currentC;
        for (int sid : touched_sids) {
            int old_cnt = satisfied_placements_per_str[sid];
            int new_cnt = old_cnt + delta_satisfied[sid];
            if (old_cnt > 0 && new_cnt == 0) newC--;
            else if (old_cnt == 0 && new_cnt > 0) newC++;
        }
        int deltaC = newC - currentC;

        bool accept = false;
        if (deltaC >= 0) {
            accept = true;
        } else {
            double prob = exp((double)deltaC / temp);
            if (rand01() < prob) accept = true;
        }

        if (accept) {
            grid[pos] = new_char;
            currentC = newC;
            for (int sid : touched_sids) {
                satisfied_placements_per_str[sid] += delta_satisfied[sid];
            }
        } else {
            // revert unsat counts
            for (const PlChange &pc : pl_changes) {
                unsat[pc.pid] = pc.old_unsat;
            }
        }

        for (int sid : touched_sids) {
            sid_marked[sid] = 0;
        }
    }

    // Output final grid
    for (int i = 0; i < N; i++) {
        for (int j = 0; j < N; j++) {
            cout << grid[i * N + j];
        }
        cout << '\n';
    }

    return 0;
}