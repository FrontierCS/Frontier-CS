#include <iostream>
#include <vector>
#include <string>
#include <chrono>
#include <random>
#include <cmath>
#include <numeric>
#include <algorithm>

// Constants
constexpr int N_FIXED = 20;

// PRNG
std::mt19937 rng(std::chrono::steady_clock::now().time_since_epoch().count());

// Timer
std::chrono::steady_clock::time_point start_time;
const int TIME_LIMIT_MS = 1950;

struct Placement {
    int r, c, dir; // dir=0: horizontal, 1: vertical
};

// Global variables
int N, M;
std::vector<std::string> S;
std::vector<Placement> P;
std::vector<Placement> best_P;

// Grid state for fast energy calculation
int counts[N_FIXED][N_FIXED][8];
int num_char_types[N_FIXED][N_FIXED];
int total_coverage[N_FIXED][N_FIXED];
long long conflicts;
int filled_cells;
long long best_conflicts;
int best_filled_cells;

// Energy parameters
const long long W = 10000;

inline void get_coords(int r_start, int c_start, int dir, int k, int& r, int& c) {
    if (dir == 0) { // horizontal
        r = r_start;
        c = (c_start + k) % N;
    } else { // vertical
        r = (r_start + k) % N;
        c = c_start;
    }
}

void update_cell(int r, int c, int char_idx, int sign) {
    bool was_conflicting = num_char_types[r][c] > 1;

    if (sign == 1) { // add
        if (total_coverage[r][c] == 0) filled_cells++;
        total_coverage[r][c]++;
        if (counts[r][c][char_idx] == 0) num_char_types[r][c]++;
        counts[r][c][char_idx]++;
    } else { // remove
        total_coverage[r][c]--;
        if (total_coverage[r][c] == 0) filled_cells--;
        counts[r][c][char_idx]--;
        if (counts[r][c][char_idx] == 0) num_char_types[r][c]--;
    }

    bool is_conflicting = num_char_types[r][c] > 1;
    if (!was_conflicting && is_conflicting) conflicts++;
    if (was_conflicting && !is_conflicting) conflicts--;
}

void update_placement(int str_idx, const Placement& p, int sign) {
    const auto& s = S[str_idx];
    for (size_t k = 0; k < s.length(); ++k) {
        int r, c;
        get_coords(p.r, p.c, p.dir, k, r, c);
        update_cell(r, c, s[k] - 'A', sign);
    }
}

void solve() {
    start_time = std::chrono::steady_clock::now();
    std::uniform_int_distribution<int> rand_N_dist(0, N - 1);
    std::uniform_int_distribution<int> rand_dir_dist(0, 1);
    std::uniform_int_distribution<int> rand_M_dist(0, M - 1);
    std::uniform_real_distribution<double> rand_double_dist(0.0, 1.0);

    // Initial random placements
    P.resize(M);
    for (int i = 0; i < M; ++i) {
        P[i] = {rand_N_dist(rng), rand_N_dist(rng), rand_dir_dist(rng)};
        update_placement(i, P[i], 1);
    }
    
    best_P = P;
    best_conflicts = conflicts;
    best_filled_cells = filled_cells;

    double T_start = 2000.0, T_end = 0.1;
    
    int iter = 0;
    while (true) {
        iter++;
        if (iter % 1024 == 0) {
            auto current_time = std::chrono::steady_clock::now();
            auto elapsed_ms = std::chrono::duration_cast<std::chrono::milliseconds>(current_time - start_time).count();
            if (elapsed_ms > TIME_LIMIT_MS) break;
        }

        double progress = (double)std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now() - start_time).count() / TIME_LIMIT_MS;
        if(progress >= 1.0) break;
        double T = T_start * pow(T_end / T_start, progress);

        int str_idx = rand_M_dist(rng);
        Placement p_old = P[str_idx];
        Placement p_new = {rand_N_dist(rng), rand_N_dist(rng), rand_dir_dist(rng)};
        if(p_old.r == p_new.r && p_old.c == p_new.c && p_old.dir == p_new.dir) continue;


        long long old_energy = W * conflicts + filled_cells;
        
        update_placement(str_idx, p_old, -1);
        update_placement(str_idx, p_new, 1);
        
        long long new_energy = W * conflicts + filled_cells;
        long long best_energy = W * best_conflicts + best_filled_cells;
        
        if (new_energy < best_energy) {
            best_conflicts = conflicts;
            best_filled_cells = filled_cells;
            best_P = P;
            best_P[str_idx] = p_new;
        }

        if (new_energy < old_energy || rand_double_dist(rng) < exp((double)(old_energy - new_energy) / T)) {
            P[str_idx] = p_new;
        } else {
            update_placement(str_idx, p_new, -1);
            update_placement(str_idx, p_old, 1);
        }
    }

    std::vector<std::string> grid(N, std::string(N, '.'));
    
    if (best_conflicts > 0) {
        int final_counts[N_FIXED][N_FIXED][8] = {};
        int final_num_char_types[N_FIXED][N_FIXED] = {};

        for(int i = 0; i < M; ++i) {
            const auto& s = S[i];
            const auto& p = best_P[i];
            for (size_t k = 0; k < s.length(); ++k) {
                int r, c;
                get_coords(p.r, p.c, p.dir, k, r, c);
                if (final_counts[r][c][s[k] - 'A'] == 0) {
                    final_num_char_types[r][c]++;
                }
                final_counts[r][c][s[k] - 'A']++;
            }
        }

        std::vector<bool> is_ok(M, true);
        for (int i = 0; i < M; ++i) {
            const auto& s = S[i];
            const auto& p = best_P[i];
            for (size_t k = 0; k < s.length(); ++k) {
                int r, c;
                get_coords(p.r, p.c, p.dir, k, r, c);
                if (final_num_char_types[r][c] > 1) {
                    is_ok[i] = false;
                    break;
                }
            }
        }
        for (int i = 0; i < M; ++i) {
            if (is_ok[i]) {
                const auto& s = S[i];
                const auto& p = best_P[i];
                for (size_t k = 0; k < s.length(); ++k) {
                    int r, c;
                    get_coords(p.r, p.c, p.dir, k, r, c);
                    grid[r][c] = s[k];
                }
            }
        }
    } else {
         for (int i = 0; i < M; ++i) {
            const auto& s = S[i];
            const auto& p = best_P[i];
            for (size_t k = 0; k < s.length(); ++k) {
                int r, c;
                get_coords(p.r, p.c, p.dir, k, r, c);
                grid[r][c] = s[k];
            }
        }
    }

    for (int i = 0; i < N; ++i) {
        std::cout << grid[i] << std::endl;
    }
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    std::cin >> N >> M;
    S.resize(M);
    for (int i = 0; i < M; ++i) {
        std::cin >> S[i];
    }
    solve();
    return 0;
}