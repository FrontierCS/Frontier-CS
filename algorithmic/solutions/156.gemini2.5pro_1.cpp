#include <iostream>
#include <vector>
#include <string>
#include <chrono>
#include <random>
#include <algorithm>
#include <cmath>
#include <numeric>
#include <tuple>

// --- Timer ---
auto start_time = std::chrono::high_resolution_clock::now();
double get_time() {
    auto now = std::chrono::high_resolution_clock::now();
    return std::chrono::duration_cast<std::chrono::duration<double>>(now - start_time).count();
}

// --- Random Number Generator ---
std::mt19937 rng(std::chrono::steady_clock::now().time_since_epoch().count());
int rand_int(int min, int max) {
    std::uniform_int_distribution<int> dist(min, max);
    return dist(rng);
}
double rand_double() {
    std::uniform_real_distribution<double> dist(0.0, 1.0);
    return dist(rng);
}

// --- Problem Constants ---
constexpr int N = 30;
const int TO[8][4] = {
    {1, 0, -1, -1}, {3, -1, -1, 0}, {-1, -1, 3, 2}, {-1, 2, 1, -1},
    {1, 0, 3, 2}, {3, 2, 1, 0}, {2, -1, 0, -1}, {-1, 3, -1, 1},
};
const int DI[] = {0, -1, 0, 1}; // 0:L, 1:U, 2:R, 3:D
const int DJ[] = {-1, 0, 1, 0};

int initial_tiles[N][N];
int rotate_map[8][4];
int current_rotations[N][N];
int best_rotations[N][N];

void precompute_rotations() {
    int r_map[8] = {1, 2, 3, 0, 5, 4, 7, 6};
    for (int t = 0; t < 8; ++t) {
        rotate_map[t][0] = t;
        int current_t = t;
        for (int r = 1; r < 4; ++r) {
            current_t = r_map[current_t];
            rotate_map[t][r] = current_t;
        }
    }
}

long long calculate_score() {
    int tiles[N][N];
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            tiles[i][j] = rotate_map[initial_tiles[i][j]][current_rotations[i][j]];
        }
    }

    bool visited[N][N][4] = {};
    std::vector<int> loop_lengths;

    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            for (int d_start = 0; d_start < 4; ++d_start) {
                if (visited[i][j][d_start]) continue;

                std::vector<std::tuple<int, int, int>> path;
                int ci = i, cj = j, cd = d_start;
                bool is_loop = false;
                
                while (true) {
                    if (ci < 0 || ci >= N || cj < 0 || cj >= N) break;
                    if (visited[ci][cj][cd]) break;
                    
                    path.emplace_back(ci, cj, cd);
                    
                    int type = tiles[ci][cj];
                    int d_exit = TO[type][cd];
                    if (d_exit == -1) break;

                    int ni = ci + DI[d_exit];
                    int nj = cj + DJ[d_exit];
                    
                    int nd = (d_exit + 2) % 4;
                    ci = ni; cj = nj; cd = nd;

                    if (ci == i && cj == j && cd == d_start) {
                        is_loop = true;
                        break; 
                    }
                }

                if (is_loop) {
                    loop_lengths.push_back(path.size());
                }

                for (const auto& p : path) {
                    visited[std::get<0>(p)][std::get<1>(p)][std::get<2>(p)] = true;
                }
            }
        }
    }

    if (loop_lengths.size() < 2) return 0;

    std::sort(loop_lengths.rbegin(), loop_lengths.rend());
    return (long long)loop_lengths[0] * loop_lengths[1];
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    for (int i = 0; i < N; ++i) {
        std::string row;
        std::cin >> row;
        for (int j = 0; j < N; ++j) {
            initial_tiles[i][j] = row[j] - '0';
        }
    }

    precompute_rotations();

    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            current_rotations[i][j] = rand_int(0, 3);
        }
    }
    
    long long current_score = calculate_score();
    long long best_score = current_score;
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            best_rotations[i][j] = current_rotations[i][j];
        }
    }
    
    const double time_limit = 1.95;
    const double T_start = 20000;
    const double T_end = 0.1;

    while (true) {
        double elapsed_time = get_time();
        if (elapsed_time >= time_limit) break;

        double progress = elapsed_time / time_limit;
        double T = T_start * pow(T_end / T_start, progress);

        int r = rand_int(0, N - 1);
        int c = rand_int(0, N - 1);
        int old_rot = current_rotations[r][c];
        int new_rot = (old_rot + rand_int(1, 3)) % 4;

        current_rotations[r][c] = new_rot;
        long long new_score = calculate_score();

        if (new_score > current_score || rand_double() < exp((double)(new_score - current_score) / T)) {
            current_score = new_score;
            if (current_score > best_score) {
                best_score = current_score;
                for (int i = 0; i < N; ++i) {
                    for (int j = 0; j < N; ++j) {
                        best_rotations[i][j] = current_rotations[i][j];
                    }
                }
            }
        } else {
            current_rotations[r][c] = old_rot;
        }
    }

    std::string out = "";
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            out += std::to_string(best_rotations[i][j]);
        }
    }
    std::cout << out << std::endl;

    return 0;
}