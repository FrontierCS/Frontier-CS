#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <random>
#include <chrono>
#include <cassert>

using namespace std;

const int N = 20;
const int NN = N * N;
const string ALPH = "ABCDEFGH";
const int A = ALPH.size();

struct Placement {
    int sid;            // string index
    int len;            // length of the string
    vector<int> cells;  // cell indices (size = len)
    vector<char> req;   // required letters (size = len)
};

int M;
vector<string> strings;
vector<Placement> placements;
vector<vector<pair<int, char>>> cell_placements; // for each cell: list of (placement id, required letter)

// ----------------------------------------------------------------------
// Initialize data structures
// ----------------------------------------------------------------------
void build_placements() {
    placements.clear();
    for (int sid = 0; sid < M; ++sid) {
        const string& s = strings[sid];
        int L = s.size();
        for (int i = 0; i < N; ++i) {
            for (int j = 0; j < N; ++j) {
                // horizontal
                Placement ph;
                ph.sid = sid;
                ph.len = L;
                ph.cells.resize(L);
                ph.req.resize(L);
                for (int p = 0; p < L; ++p) {
                    int ci = i;
                    int cj = (j + p) % N;
                    ph.cells[p] = ci * N + cj;
                    ph.req[p] = s[p];
                }
                placements.push_back(ph);

                // vertical
                Placement pv;
                pv.sid = sid;
                pv.len = L;
                pv.cells.resize(L);
                pv.req.resize(L);
                for (int p = 0; p < L; ++p) {
                    int ci = (i + p) % N;
                    int cj = j;
                    pv.cells[p] = ci * N + cj;
                    pv.req[p] = s[p];
                }
                placements.push_back(pv);
            }
        }
    }

    cell_placements.assign(NN, vector<pair<int,char>>());
    for (size_t pid = 0; pid < placements.size(); ++pid) {
        const Placement& pl = placements[pid];
        for (int p = 0; p < pl.len; ++p) {
            int cell = pl.cells[p];
            cell_placements[cell].emplace_back(pid, pl.req[p]);
        }
    }
}

// ----------------------------------------------------------------------
// Compute initial state for a given grid
// ----------------------------------------------------------------------
void compute_initial_state(const vector<char>& grid,
                           vector<int>& mismatches,
                           vector<int>& match_count,
                           int& total_covered) {
    int P = placements.size();
    mismatches.assign(P, 0);
    for (int pid = 0; pid < P; ++pid) {
        const Placement& pl = placements[pid];
        int miss = 0;
        for (int p = 0; p < pl.len; ++p) {
            if (grid[pl.cells[p]] != pl.req[p]) ++miss;
        }
        mismatches[pid] = miss;
    }

    match_count.assign(M, 0);
    for (int pid = 0; pid < P; ++pid) {
        if (mismatches[pid] == 0) {
            match_count[placements[pid].sid]++;
        }
    }

    total_covered = 0;
    for (int sid = 0; sid < M; ++sid) {
        if (match_count[sid] > 0) total_covered++;
    }
}

// ----------------------------------------------------------------------
// ICM (Iterated Conditional Modes) sweeps
// ----------------------------------------------------------------------
void icm(vector<char>& grid,
         vector<int>& mismatches,
         vector<int>& match_count,
         int& total_covered,
         mt19937& rng) {
    vector<int> order(NN);
    iota(order.begin(), order.end(), 0);

    for (int sweep = 0; sweep < 5; ++sweep) {
        shuffle(order.begin(), order.end(), rng);
        bool changed = false;

        for (int idx : order) {
            char old_letter = grid[idx];
            int best_delta = 0;
            char best_letter = old_letter;

            // try each possible new letter
            for (char new_letter : ALPH) {
                if (new_letter == old_letter) continue;

                vector<int> delta_match(M, 0);
                for (const auto& p : cell_placements[idx]) {
                    int pid = p.first;
                    char req_letter = p.second;
                    int old_m = mismatches[pid];
                    bool old_match = (old_letter == req_letter);
                    bool new_match = (new_letter == req_letter);
                    int d = 0;
                    if (old_match && !new_match) d = 1;
                    if (!old_match && new_match) d = -1;
                    int new_m = old_m + d;
                    bool was_match = (old_m == 0);
                    bool will_match = (new_m == 0);
                    int sid = placements[pid].sid;
                    if (was_match && !will_match) {
                        delta_match[sid]--;
                    } else if (!was_match && will_match) {
                        delta_match[sid]++;
                    }
                }

                int delta_c = 0;
                for (int sid = 0; sid < M; ++sid) {
                    if (delta_match[sid] == 0) continue;
                    int new_match_count = match_count[sid] + delta_match[sid];
                    if (match_count[sid] == 0 && new_match_count > 0) delta_c++;
                    else if (match_count[sid] > 0 && new_match_count == 0) delta_c--;
                }

                if (delta_c > best_delta) {
                    best_delta = delta_c;
                    best_letter = new_letter;
                }
            }

            if (best_delta > 0) {
                // apply the change
                char new_letter = best_letter;
                for (const auto& p : cell_placements[idx]) {
                    int pid = p.first;
                    char req_letter = p.second;
                    int old_m = mismatches[pid];
                    bool old_match = (grid[idx] == req_letter);
                    bool new_match = (new_letter == req_letter);
                    int d = 0;
                    if (old_match && !new_match) d = 1;
                    if (!old_match && new_match) d = -1;
                    int new_m = old_m + d;
                    mismatches[pid] = new_m;

                    bool was_match = (old_m == 0);
                    bool will_match = (new_m == 0);
                    int sid = placements[pid].sid;
                    if (was_match && !will_match) {
                        match_count[sid]--;
                        if (match_count[sid] == 0) total_covered--;
                    } else if (!was_match && will_match) {
                        match_count[sid]++;
                        if (match_count[sid] == 1) total_covered++;
                    }
                }
                grid[idx] = new_letter;
                changed = true;
            }
        }

        if (!changed) break;
    }
}

// ----------------------------------------------------------------------
// Generate consensus grid (most frequent letter per cell)
// ----------------------------------------------------------------------
vector<char> consensus_grid() {
    vector<char> grid(NN);
    for (int cell = 0; cell < NN; ++cell) {
        int cnt[8] = {0};
        for (const auto& p : cell_placements[cell]) {
            char req = p.second;
            cnt[req - 'A']++;
        }
        int best = 0;
        for (int i = 1; i < 8; ++i) {
            if (cnt[i] > cnt[best]) best = i;
        }
        grid[cell] = ALPH[best];
    }
    return grid;
}

// ----------------------------------------------------------------------
// Generate random grid
// ----------------------------------------------------------------------
vector<char> random_grid(mt19937& rng) {
    vector<char> grid(NN);
    uniform_int_distribution<int> dist(0, A-1);
    for (int i = 0; i < NN; ++i) {
        grid[i] = ALPH[dist(rng)];
    }
    return grid;
}

// ----------------------------------------------------------------------
// Main
// ----------------------------------------------------------------------
int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    cin >> N >> M;
    strings.resize(M);
    for (int i = 0; i < M; ++i) {
        cin >> strings[i];
    }

    build_placements();

    mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());

    // best solution found
    vector<char> best_grid(NN);
    int best_covered = -1;

    // try consensus start
    {
        vector<char> grid = consensus_grid();
        vector<int> mismatches;
        vector<int> match_count;
        int covered;
        compute_initial_state(grid, mismatches, match_count, covered);
        icm(grid, mismatches, match_count, covered, rng);
        if (covered > best_covered) {
            best_covered = covered;
            best_grid = grid;
        }
    }

    // try a few random starts
    const int NUM_TRIALS = 2;
    for (int trial = 0; trial < NUM_TRIALS; ++trial) {
        vector<char> grid = random_grid(rng);
        vector<int> mismatches;
        vector<int> match_count;
        int covered;
        compute_initial_state(grid, mismatches, match_count, covered);
        icm(grid, mismatches, match_count, covered, rng);
        if (covered > best_covered) {
            best_covered = covered;
            best_grid = grid;
        }
        if (best_covered == M) break;
    }

    // output the grid
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            cout << best_grid[i * N + j];
        }
        cout << '\n';
    }

    return 0;
}