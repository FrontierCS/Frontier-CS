#include <iostream>
#include <vector>
#include <string>
#include <chrono>
#include <random>
#include <cmath>
#include <algorithm>
#include <numeric>

// --- Timer ---
auto start_time = std::chrono::steady_clock::now();
double get_time() {
    auto now = std::chrono::steady_clock::now();
    return std::chrono::duration_cast<std::chrono::duration<double>>(now - start_time).count();
}

// --- Random Number Generator ---
std::mt19937 rng(std::chrono::steady_clock::now().time_since_epoch().count());

// --- Constants ---
constexpr int N = 20;
constexpr int CHAR_KIND = 8;
const double TIME_LIMIT = 2.95;

// --- Problem Data ---
int M;
std::vector<std::string> S;
std::vector<int> S_len;
int char_to_int[128];

// --- SA State ---
struct Placement {
    int r, c, dir; // dir 0:H, 1:V. r=-1: unplaced
};

std::vector<Placement> placements;
int char_counts[N][N][CHAR_KIND];
int total_counts[N][N];
long long current_conflicts = 0;
int current_unplaced_count = 0;

std::vector<Placement> best_placements;
long long best_energy = -1;

// --- SA Parameters ---
const long long W_UNPLACED = 800;
const long long W_CONFLICT = 1;

// --- Helper Functions ---
long long calculate_cell_conflict_value(int r, int c) {
    if (total_counts[r][c] <= 1) return 0;
    int max_f = 0;
    for (int i = 0; i < CHAR_KIND; ++i) {
        max_f = std::max(max_f, char_counts[r][c][i]);
    }
    return total_counts[r][c] - max_f;
}

void apply_placement(int s_idx, const Placement& p, int sign) {
    if (p.r == -1) {
        current_unplaced_count += sign;
        return;
    }

    if (sign == 1) current_unplaced_count--;
    else current_unplaced_count++;

    const auto& s = S[s_idx];
    int len = S_len[s_idx];
    
    for (int i = 0; i < len; ++i) {
        int r, c;
        if (p.dir == 0) { // Horizontal
            r = p.r;
            c = (p.c + i) % N;
        } else { // Vertical
            r = (p.r + i) % N;
            c = p.c;
        }
        current_conflicts -= calculate_cell_conflict_value(r, c);
        total_counts[r][c] += sign;
        char_counts[r][c][char_to_int[s[i]]] += sign;
        current_conflicts += calculate_cell_conflict_value(r, c);
    }
}


void init() {
    int n_dummy;
    std::cin >> n_dummy >> M;
    S.resize(M);
    S_len.resize(M);
    for (int i = 0; i < M; ++i) {
        std::cin >> S[i];
        S_len[i] = S[i].length();
    }

    for (int i = 0; i < CHAR_KIND; ++i) {
        char_to_int['A' + i] = i;
    }

    placements.assign(M, {-1, -1, -1});
    current_unplaced_count = M;

    std::vector<int> p_indices(M);
    std::iota(p_indices.begin(), p_indices.end(), 0);
    std::sort(p_indices.begin(), p_indices.end(), [&](int a, int b){
        return S_len[a] > S_len[b];
    });

    std::vector<std::vector<char>> initial_grid(N, std::vector<char>(N, '.'));
    std::uniform_int_distribution<> rand_n(0, N - 1);
    std::uniform_int_distribution<> rand_dir(0, 1);

    for(int s_idx : p_indices) {
        int best_r = -1, best_c = -1, best_dir = -1;
        int max_overlap = -1;

        // Limited random search for a good initial placement
        for(int k=0; k < 2000/M + 1; ++k) {
            int r = rand_n(rng);
            int c = rand_n(rng);
            int dir = rand_dir(rng);
            
            bool possible = true;
            int current_overlap = 0;
            for (int i = 0; i < S_len[s_idx]; ++i) {
                int cur_r, cur_c;
                if(dir == 0) { cur_r = r; cur_c = (c+i)%N; }
                else { cur_r = (r+i)%N; cur_c = c; }

                char grid_char = initial_grid[cur_r][cur_c];
                if (grid_char != '.' && grid_char != S[s_idx][i]) {
                    possible = false;
                    break;
                }
                if (grid_char == S[s_idx][i]) {
                    current_overlap++;
                }
            }
            if (possible && current_overlap > max_overlap) {
                max_overlap = current_overlap;
                best_r = r; best_c = c; best_dir = dir;
            }
        }
        
        if (max_overlap == -1) { // try one full search if random fails
             for (int dir = 0; dir < 2; ++dir) for (int r = 0; r < N; ++r) for (int c = 0; c < N; ++c) {
                bool possible = true; int current_overlap = 0;
                for (int i = 0; i < S_len[s_idx]; ++i) {
                    int cur_r, cur_c;
                    if(dir == 0) { cur_r = r; cur_c = (c+i)%N; } else { cur_r = (r+i)%N; cur_c = c; }
                    char grid_char = initial_grid[cur_r][cur_c];
                    if (grid_char != '.' && grid_char != S[s_idx][i]) { possible = false; break; }
                    if (grid_char == S[s_idx][i]) current_overlap++;
                }
                if (possible && current_overlap > max_overlap) {
                    max_overlap = current_overlap; best_r = r; best_c = c; best_dir = dir;
                }
             }
        }

        if (best_r != -1) {
            placements[s_idx] = {best_r, best_c, best_dir};
            apply_placement(s_idx, placements[s_idx], 1);
            for (int i = 0; i < S_len[s_idx]; ++i) {
                if (best_dir == 0) initial_grid[best_r][(best_c + i) % N] = S[s_idx][i];
                else initial_grid[(best_r + i) % N][best_c] = S[s_idx][i];
            }
        }
    }
}

void solve() {
    std::uniform_int_distribution<> rand_m(0, M - 1);
    std::uniform_int_distribution<> rand_n(0, N - 1);
    std::uniform_int_distribution<> rand_dir(0, 1);
    std::uniform_int_distribution<> rand_100(0, 99);
    std::uniform_real_distribution<> rand_double(0.0, 1.0);

    double start_temp = 10;
    double end_temp = 0.1;
    
    best_placements = placements;
    best_energy = W_UNPLACED * current_unplaced_count + W_CONFLICT * current_conflicts;

    while (get_time() < TIME_LIMIT) {
        double progress = get_time() / TIME_LIMIT;
        double temp = start_temp * pow(end_temp / start_temp, progress);

        int s_idx = rand_m(rng);
        Placement old_p = placements[s_idx];
        Placement new_p;

        int move_type = rand_100(rng);
        if (current_unplaced_count > 0 && move_type < 10) {
            s_idx = -1;
            for(int i=0; i<M; ++i) { if(placements[i].r == -1) {s_idx = i; break;} }
            old_p = placements[s_idx];
            new_p = {rand_n(rng), rand_n(rng), rand_dir(rng)};
        } else if (move_type < 80) { // Random new placement
            new_p = {rand_n(rng), rand_n(rng), rand_dir(rng)};
        } else if (move_type < 95) { // Unplace
            new_p = {-1, -1, -1};
        } else { // Local move
            if (old_p.r != -1) {
                int dr = rng() % 3 - 1;
                int dc = rng() % 3 - 1;
                new_p = {(old_p.r + dr + N) % N, (old_p.c + dc + N) % N, old_p.dir};
                if(rng()%2==0) new_p.dir = 1-new_p.dir;
            } else { // was unplaced, try random
                new_p = {rand_n(rng), rand_n(rng), rand_dir(rng)};
            }
        }
        
        if (old_p.r == new_p.r && old_p.c == new_p.c && old_p.dir == new_p.dir) continue;
        
        long long current_energy = W_UNPLACED * current_unplaced_count + W_CONFLICT * current_conflicts;

        apply_placement(s_idx, old_p, -1);
        apply_placement(s_idx, new_p, 1);

        long long new_energy = W_UNPLACED * current_unplaced_count + W_CONFLICT * current_conflicts;
        long long delta_energy = new_energy - current_energy;

        if (delta_energy < 0 || rand_double(rng) < exp(-delta_energy / temp)) {
            placements[s_idx] = new_p;
            if (new_energy < best_energy) {
                best_energy = new_energy;
                best_placements = placements;
            }
        } else {
            apply_placement(s_idx, new_p, -1);
            apply_placement(s_idx, old_p, 1);
        }
    }
}

void output() {
    std::vector<std::vector<char>> grid(N, std::vector<char>(N, '.'));
    
    std::vector<std::vector<std::vector<int>>> final_char_counts(N, std::vector<std::vector<int>>(N, std::vector<int>(CHAR_KIND, 0)));
    std::vector<std::vector<int>> final_total_counts(N, std::vector<int>(N, 0));
    
    int final_unplaced = 0;
    long long final_conflicts = 0;

    for (int i = 0; i < M; ++i) {
        if (best_placements[i].r == -1) {
            final_unplaced++;
            continue;
        }
        const auto& p = best_placements[i];
        const auto& s = S[i];
        int len = S_len[i];
        for (int j = 0; j < len; ++j) {
            int r, c;
            if (p.dir == 0) { r = p.r; c = (p.c + j) % N; } 
            else { r = (p.r + j) % N; c = p.c; }
            final_char_counts[r][c][char_to_int[s[j]]]++;
            final_total_counts[r][c]++;
        }
    }
    
    for (int r = 0; r < N; ++r) {
        for (int c = 0; c < N; ++c) {
            if (final_total_counts[r][c] > 0) {
                int max_f = 0, max_char_idx = 0;
                for (int i = 0; i < CHAR_KIND; ++i) {
                    if (final_char_counts[r][c][i] > max_f) {
                        max_f = final_char_counts[r][c][i];
                        max_char_idx = i;
                    }
                }
                grid[r][c] = 'A' + max_char_idx;
                final_conflicts += final_total_counts[r][c] - max_f;
            }
        }
    }

    if (final_unplaced == 0 && final_conflicts == 0) {
        std::vector<int> char_freq(CHAR_KIND, 0);
        for(const auto& s : S) {
            for(char ch : s) char_freq[char_to_int[ch]]++;
        }
        std::vector<char> weighted_chars;
        for(int i=0; i<CHAR_KIND; ++i) {
            for(int j=0; j<char_freq[i]; ++j) weighted_chars.push_back('A'+i);
        }
        if(!weighted_chars.empty()){
            std::uniform_int_distribution<> rand_char(0, weighted_chars.size()-1);
            for (int r = 0; r < N; ++r) {
                for (int c = 0; c < N; ++c) {
                    if (grid[r][c] == '.') {
                        grid[r][c] = weighted_chars[rand_char(rng)];
                    }
                }
            }
        }
    }

    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            std::cout << grid[i][j];
        }
        std::cout << '\n';
    }
}


int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    init();
    solve();
    output();
    return 0;
}