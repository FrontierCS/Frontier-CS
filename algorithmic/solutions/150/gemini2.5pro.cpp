#include <iostream>
#include <vector>
#include <string>
#include <chrono>
#include <random>
#include <cmath>
#include <algorithm>
#include <map>
#include <array>

using namespace std;

const int N_fixed = 20;
const int NUM_CHARS = 8;
int M_val;
vector<string> S_vec;

chrono::steady_clock::time_point start_time;
mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());

inline int mod(int a, int m) {
    return (a % m + m) % m;
}

struct State {
    vector<vector<int>> grid;
    vector<vector<vector<array<int, 2>>>> mismatch_counts;
    vector<int> match_counts;
    int unsatisfied_count;

    State() : grid(N_fixed, vector<int>(N_fixed)),
              mismatch_counts(M_val, vector<vector<array<int, 2>>>(N_fixed, vector<array<int, 2>>(N_fixed))),
              match_counts(M_val),
              unsatisfied_count(0) {}

    void compute_initial_mismatches() {
        unsatisfied_count = 0;
        for (int i = 0; i < M_val; ++i) {
            match_counts[i] = 0;
            for (int r = 0; r < N_fixed; ++r) {
                for (int c = 0; c < N_fixed; ++c) {
                    int mismatches_h = 0;
                    for (size_t p = 0; p < S_vec[i].length(); ++p) {
                        if (grid[r][(c + p) % N_fixed] != S_vec[i][p] - 'A') {
                            mismatches_h++;
                        }
                    }
                    mismatch_counts[i][r][c][0] = mismatches_h;
                    if (mismatches_h == 0) match_counts[i]++;

                    int mismatches_v = 0;
                    for (size_t p = 0; p < S_vec[i].length(); ++p) {
                        if (grid[(r + p) % N_fixed][c] != S_vec[i][p] - 'A') {
                            mismatches_v++;
                        }
                    }
                    mismatch_counts[i][r][c][1] = mismatches_v;
                    if (mismatches_v == 0) match_counts[i]++;
                }
            }
            if (match_counts[i] == 0) {
                unsatisfied_count++;
            }
        }
    }

    void generate_initial_grid() {
        vector<vector<vector<int>>> counts(N_fixed, vector<vector<int>>(N_fixed, vector<int>(NUM_CHARS, 0)));
        for (int i = 0; i < M_val; ++i) {
            for (int r = 0; r < N_fixed; ++r) {
                for (int c = 0; c < N_fixed; ++c) {
                    for (size_t p = 0; p < S_vec[i].length(); ++p) {
                        counts[r][(c + p) % N_fixed][S_vec[i][p] - 'A']++;
                    }
                    for (size_t p = 0; p < S_vec[i].length(); ++p) {
                        counts[(r + p) % N_fixed][c][S_vec[i][p] - 'A']++;
                    }
                }
            }
        }
        for (int r = 0; r < N_fixed; ++r) {
            for (int c = 0; c < N_fixed; ++c) {
                int best_char = 0;
                int max_count = -1;
                for (int char_idx = 0; char_idx < NUM_CHARS; ++char_idx) {
                    if (counts[r][c][char_idx] > max_count) {
                        max_count = counts[r][c][char_idx];
                        best_char = char_idx;
                    }
                }
                grid[r][c] = best_char;
            }
        }
    }
};

void solve() {
    int N_in;
    cin >> N_in >> M_val;
    S_vec.resize(M_val);
    for (int i = 0; i < M_val; ++i) {
        cin >> S_vec[i];
    }

    State current_state;
    current_state.generate_initial_grid();
    current_state.compute_initial_mismatches();

    State best_state = current_state;

    double start_temp = 5;
    double end_temp = 1e-4;
    double time_limit = 2.9;

    uniform_int_distribution<int> dist_pos(0, N_fixed - 1);
    uniform_int_distribution<int> dist_char(0, NUM_CHARS - 1);
    uniform_real_distribution<double> dist_prob(0.0, 1.0);

    while (true) {
        auto current_time = chrono::steady_clock::now();
        double elapsed_seconds = chrono::duration<double>(current_time - start_time).count();
        if (elapsed_seconds > time_limit) break;

        double temp = start_temp * pow(end_temp / start_temp, elapsed_seconds / time_limit);

        int r = dist_pos(rng);
        int c = dist_pos(rng);
        int old_char = current_state.grid[r][c];
        int new_char = dist_char(rng);
        if (old_char == new_char) continue;

        map<int, int> mc_deltas;
        for (int i = 0; i < M_val; ++i) {
            for (size_t p = 0; p < S_vec[i].length(); ++p) {
                int char_needed = S_vec[i][p] - 'A';
                
                // Horizontal placement covering (r,c) starts at (r, c-p)
                int sr_h = r, sc_h = mod(c - (int)p, N_fixed);
                int old_mismatch_h = current_state.mismatch_counts[i][sr_h][sc_h][0];
                int new_mismatch_h = old_mismatch_h;
                if (char_needed == old_char) new_mismatch_h++;
                if (char_needed == new_char) new_mismatch_h--;
                if (old_mismatch_h == 0 && new_mismatch_h > 0) mc_deltas[i]--;
                if (old_mismatch_h > 0 && new_mismatch_h == 0) mc_deltas[i]++;
                
                // Vertical placement covering (r,c) starts at (r-p, c)
                int sr_v = mod(r - (int)p, N_fixed), sc_v = c;
                int old_mismatch_v = current_state.mismatch_counts[i][sr_v][sc_v][1];
                int new_mismatch_v = old_mismatch_v;
                if (char_needed == old_char) new_mismatch_v++;
                if (char_needed == new_char) new_mismatch_v--;
                if (old_mismatch_v == 0 && new_mismatch_v > 0) mc_deltas[i]--;
                if (old_mismatch_v > 0 && new_mismatch_v == 0) mc_deltas[i]++;
            }
        }
        
        int delta_e = 0;
        for(auto const& [i, delta] : mc_deltas) {
            bool was_satisfied = current_state.match_counts[i] > 0;
            bool is_satisfied = (current_state.match_counts[i] + delta) > 0;
            if (was_satisfied && !is_satisfied) delta_e++;
            if (!was_satisfied && is_satisfied) delta_e--;
        }

        if (delta_e <= 0 || dist_prob(rng) < exp(-delta_e / temp)) {
            current_state.grid[r][c] = new_char;
            current_state.unsatisfied_count += delta_e;
            for(auto const& [i, delta] : mc_deltas) {
                current_state.match_counts[i] += delta;
            }
            for (int i = 0; i < M_val; ++i) {
                for (size_t p = 0; p < S_vec[i].length(); ++p) {
                    int char_needed = S_vec[i][p] - 'A';
                    int sr, sc;
                    sr = r; sc = mod(c - (int)p, N_fixed);
                    if (char_needed == old_char) current_state.mismatch_counts[i][sr][sc][0]++;
                    if (char_needed == new_char) current_state.mismatch_counts[i][sr][sc][0]--;
                    sr = mod(r - (int)p, N_fixed); sc = c;
                    if (char_needed == old_char) current_state.mismatch_counts[i][sr][sc][1]++;
                    if (char_needed == new_char) current_state.mismatch_counts[i][sr][sc][1]--;
                }
            }
            if (current_state.unsatisfied_count < best_state.unsatisfied_count) {
                best_state = current_state;
            }
        }
    }

    vector<vector<char>> final_grid(N_fixed, vector<char>(N_fixed));
    for (int r = 0; r < N_fixed; ++r) {
        for (int c = 0; c < N_fixed; ++c) {
            final_grid[r][c] = (char)('A' + best_state.grid[r][c]);
        }
    }

    if (best_state.unsatisfied_count == 0) {
        best_state.compute_initial_mismatches();
        vector<vector<bool>> is_essential(N_fixed, vector<bool>(N_fixed, false));
        for (int i = 0; i < M_val; ++i) {
            if (best_state.match_counts[i] == 1) {
                for (int r = 0; r < N_fixed; ++r) {
                    for (int c = 0; c < N_fixed; ++c) {
                        if (best_state.mismatch_counts[i][r][c][0] == 0) {
                            for (size_t p = 0; p < S_vec[i].length(); ++p) {
                                is_essential[r][(c + p) % N_fixed] = true;
                            }
                        }
                        if (best_state.mismatch_counts[i][r][c][1] == 0) {
                            for (size_t p = 0; p < S_vec[i].length(); ++p) {
                                is_essential[(r + p) % N_fixed][c] = true;
                            }
                        }
                    }
                }
            }
        }

        for (int r = 0; r < N_fixed; ++r) {
            for (int c = 0; c < N_fixed; ++c) {
                if (!is_essential[r][c]) {
                    final_grid[r][c] = '.';
                }
            }
        }
    }

    for (int r = 0; r < N_fixed; ++r) {
        for (int c = 0; c < N_fixed; ++c) {
            cout << final_grid[r][c];
        }
        cout << endl;
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    start_time = chrono::steady_clock::now();
    solve();
    return 0;
}