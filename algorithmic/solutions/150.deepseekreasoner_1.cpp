#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <random>
#include <cmath>
#include <unordered_map>
#include <cassert>
#include <numeric>

using namespace std;

const int N = 20;
const int N2 = N * N;
const int ALPH = 8; // A-H
const int DOT = 8; // representation for '.'

struct Placement {
    int sid;
    vector<int> cells;
    vector<int> req;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, M;
    cin >> n >> M; // n is always 20
    assert(n == N);

    vector<string> reads(M);
    for (int i = 0; i < M; i++) {
        cin >> reads[i];
    }

    // Precompute all placements
    vector<Placement> all_placements;
    vector<vector<int>> placements_by_read(M);
    vector<vector<pair<int, int>>> cell_placements(N2);

    for (int r = 0; r < M; r++) {
        const string& s = reads[r];
        int len = s.size();
        for (int i = 0; i < N; i++) {
            for (int j = 0; j < N; j++) {
                // horizontal
                Placement pl_h;
                pl_h.sid = r;
                for (int p = 0; p < len; p++) {
                    int ci = i;
                    int cj = (j + p) % N;
                    int cell = ci * N + cj;
                    int ch = s[p] - 'A';
                    pl_h.cells.push_back(cell);
                    pl_h.req.push_back(ch);
                }
                int pid_h = all_placements.size();
                all_placements.push_back(pl_h);
                placements_by_read[r].push_back(pid_h);
                // vertical
                Placement pl_v;
                pl_v.sid = r;
                for (int p = 0; p < len; p++) {
                    int ci = (i + p) % N;
                    int cj = j;
                    int cell = ci * N + cj;
                    int ch = s[p] - 'A';
                    pl_v.cells.push_back(cell);
                    pl_v.req.push_back(ch);
                }
                int pid_v = all_placements.size();
                all_placements.push_back(pl_v);
                placements_by_read[r].push_back(pid_v);
            }
        }
    }

    // Build cell_placements
    for (size_t pid = 0; pid < all_placements.size(); pid++) {
        const Placement& pl = all_placements[pid];
        for (size_t t = 0; t < pl.cells.size(); t++) {
            int cell = pl.cells[t];
            int req = pl.req[t];
            cell_placements[cell].emplace_back(pid, req);
        }
    }

    // Random number generator
    mt19937 rng(12345); // fixed seed for reproducibility

    // ---------- Phase 1: Greedy placement assignment ----------
    vector<array<int, ALPH>> cell_cnt(N2, {0});
    vector<int> cell_total(N2, 0);
    vector<int> current_placement(M, -1);

    vector<int> order(M);
    iota(order.begin(), order.end(), 0);
    shuffle(order.begin(), order.end(), rng);

    for (int r : order) {
        int best_pid = -1;
        int best_delta = 1e9;
        for (int pid : placements_by_read[r]) {
            const Placement& pl = all_placements[pid];
            int delta = 0;
            for (size_t t = 0; t < pl.cells.size(); t++) {
                int cell = pl.cells[t];
                int ch = pl.req[t];
                int cur_cnt = cell_cnt[cell][ch];
                int cur_max = *max_element(cell_cnt[cell].begin(), cell_cnt[cell].end());
                if (cur_cnt + 1 > cur_max) {
                    delta += cur_max - cur_cnt;
                } else {
                    delta += 1;
                }
            }
            if (delta < best_delta) {
                best_delta = delta;
                best_pid = pid;
            }
        }
        // apply best placement
        current_placement[r] = best_pid;
        const Placement& pl = all_placements[best_pid];
        for (size_t t = 0; t < pl.cells.size(); t++) {
            int cell = pl.cells[t];
            int ch = pl.req[t];
            cell_cnt[cell][ch]++;
            cell_total[cell]++;
        }
    }

    // compute initial cost
    int total_cost = 0;
    for (int cell = 0; cell < N2; cell++) {
        int maxv = *max_element(cell_cnt[cell].begin(), cell_cnt[cell].end());
        total_cost += cell_total[cell] - maxv;
    }

    // ---------- Phase 2: Simulated annealing on placements ----------
    auto compute_delta = [&](int r, int new_pid) {
        int old_pid = current_placement[r];
        if (old_pid == new_pid) return 0;
        const Placement& old_pl = all_placements[old_pid];
        const Placement& new_pl = all_placements[new_pid];
        unordered_map<int, array<int, ALPH>> changes;
        for (size_t t = 0; t < old_pl.cells.size(); t++) {
            int cell = old_pl.cells[t];
            int ch = old_pl.req[t];
            changes[cell][ch]--;
        }
        for (size_t t = 0; t < new_pl.cells.size(); t++) {
            int cell = new_pl.cells[t];
            int ch = new_pl.req[t];
            changes[cell][ch]++;
        }
        int delta = 0;
        for (const auto& p : changes) {
            int cell = p.first;
            const auto& del = p.second;
            array<int, ALPH> cur_cnt = cell_cnt[cell];
            int cur_total = cell_total[cell];
            int cur_max = *max_element(cur_cnt.begin(), cur_cnt.end());
            // apply del
            for (int c = 0; c < ALPH; c++) cur_cnt[c] += del[c];
            int new_total = cur_total;
            for (int c = 0; c < ALPH; c++) new_total += del[c];
            int new_max = *max_element(cur_cnt.begin(), cur_cnt.end());
            delta += (new_total - new_max) - (cur_total - cur_max);
        }
        return delta;
    };

    auto apply_move = [&](int r, int new_pid) {
        int old_pid = current_placement[r];
        if (old_pid == new_pid) return;
        const Placement& old_pl = all_placements[old_pid];
        const Placement& new_pl = all_placements[new_pid];
        unordered_map<int, array<int, ALPH>> changes;
        for (size_t t = 0; t < old_pl.cells.size(); t++) {
            int cell = old_pl.cells[t];
            int ch = old_pl.req[t];
            changes[cell][ch]--;
        }
        for (size_t t = 0; t < new_pl.cells.size(); t++) {
            int cell = new_pl.cells[t];
            int ch = new_pl.req[t];
            changes[cell][ch]++;
        }
        for (const auto& p : changes) {
            int cell = p.first;
            const auto& del = p.second;
            for (int c = 0; c < ALPH; c++) {
                cell_cnt[cell][c] += del[c];
            }
            int sum_del = 0;
            for (int c = 0; c < ALPH; c++) sum_del += del[c];
            cell_total[cell] += sum_del;
        }
        current_placement[r] = new_pid;
    };

    double T = 10.0;
    const int ITER_PLACEMENTS = 200000;
    double decay = pow(1e-6 / T, 1.0 / ITER_PLACEMENTS);
    uniform_real_distribution<> urd(0.0, 1.0);

    int best_cost = total_cost;
    vector<int> best_placement = current_placement;

    for (int iter = 0; iter < ITER_PLACEMENTS; iter++) {
        if (total_cost == 0) break;
        int r = rng() % M;
        const auto& cand = placements_by_read[r];
        if (cand.empty()) continue;
        int new_pid = cand[rng() % cand.size()];
        int delta = compute_delta(r, new_pid);
        if (delta <= 0 || exp(-delta / T) > urd(rng)) {
            apply_move(r, new_pid);
            total_cost += delta;
            if (total_cost < best_cost) {
                best_cost = total_cost;
                best_placement = current_placement;
            }
        }
        T *= decay;
    }

    // Use best placement found
    current_placement = best_placement;
    // Recompute cell_cnt from best_placement
    cell_cnt.assign(N2, {0});
    cell_total.assign(N2, 0);
    for (int r = 0; r < M; r++) {
        int pid = current_placement[r];
        const Placement& pl = all_placements[pid];
        for (size_t t = 0; t < pl.cells.size(); t++) {
            int cell = pl.cells[t];
            int ch = pl.req[t];
            cell_cnt[cell][ch]++;
            cell_total[cell]++;
        }
    }

    // ---------- Build matrix from placement consensus ----------
    vector<int> matrix(N2, 0);
    for (int cell = 0; cell < N2; cell++) {
        int best_char = 0;
        int best_cnt = cell_cnt[cell][0];
        for (int c = 1; c < ALPH; c++) {
            if (cell_cnt[cell][c] > best_cnt) {
                best_cnt = cell_cnt[cell][c];
                best_char = c;
            }
        }
        if (cell_total[cell] == 0) best_char = rng() % ALPH;
        matrix[cell] = best_char;
    }

    // ---------- Check satisfaction ----------
    int satisfied = 0;
    for (int r = 0; r < M; r++) {
        bool ok = false;
        for (int pid : placements_by_read[r]) {
            const Placement& pl = all_placements[pid];
            bool match = true;
            for (size_t t = 0; t < pl.cells.size(); t++) {
                if (matrix[pl.cells[t]] != pl.req[t]) {
                    match = false;
                    break;
                }
            }
            if (match) {
                ok = true;
                break;
            }
        }
        if (ok) satisfied++;
    }

    // ---------- If all satisfied, try dot removal ----------
    if (satisfied == M) {
        // Initialize mismatch counts and match counts
        int P = all_placements.size();
        vector<int> mism_cnt(P, 0);
        vector<int> match_count(M, 0);
        for (int pid = 0; pid < P; pid++) {
            const Placement& pl = all_placements[pid];
            int cnt = 0;
            for (size_t t = 0; t < pl.cells.size(); t++) {
                if (matrix[pl.cells[t]] != pl.req[t]) cnt++;
            }
            mism_cnt[pid] = cnt;
            if (cnt == 0) {
                match_count[pl.sid]++;
            }
        }

        // Greedy dot removal
        vector<int> cell_order(N2);
        iota(cell_order.begin(), cell_order.end(), 0);
        shuffle(cell_order.begin(), cell_order.end(), rng);
        for (int cell : cell_order) {
            int old_char = matrix[cell];
            if (old_char == DOT) continue;
            bool ok = true;
            vector<pair<int, int>> affected; // (pid, old mism_cnt)
            for (auto [pid, req] : cell_placements[cell]) {
                if (req == old_char) {
                    int old_mism = mism_cnt[pid];
                    mism_cnt[pid]++;
                    affected.emplace_back(pid, old_mism);
                    if (old_mism == 0) {
                        int sid = all_placements[pid].sid;
                        match_count[sid]--;
                        if (match_count[sid] == 0) {
                            ok = false;
                            break;
                        }
                    }
                }
            }
            if (ok) {
                matrix[cell] = DOT;
                // keep changes
            } else {
                // revert
                for (auto [pid, old_mism] : affected) {
                    mism_cnt[pid] = old_mism;
                    if (old_mism == 0) {
                        int sid = all_placements[pid].sid;
                        match_count[sid]++;
                    }
                }
            }
        }
    }

    // ---------- Output ----------
    for (int i = 0; i < N; i++) {
        string line(N, '.');
        for (int j = 0; j < N; j++) {
            int v = matrix[i * N + j];
            if (v < DOT) line[j] = 'A' + v;
        }
        cout << line << endl;
    }

    return 0;
}