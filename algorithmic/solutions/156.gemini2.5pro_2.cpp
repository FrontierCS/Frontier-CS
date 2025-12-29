#include <iostream>
#include <vector>
#include <string>
#include <chrono>
#include <random>
#include <algorithm>
#include <cmath>
#include <tuple>
#include <array>
#include <numeric>

// --- Utilities ---
struct Timer {
    std::chrono::high_resolution_clock::time_point start_time;
    Timer() {
        start_time = std::chrono::high_resolution_clock::now();
    }
    double get_elapsed() {
        auto end_time = std::chrono::high_resolution_clock::now();
        std::chrono::duration<double> elapsed = end_time - start_time;
        return elapsed.count();
    }
};

struct XorShift {
    unsigned int x, y, z, w;
    XorShift() {
        x = 123456789;
        y = 362436069;
        z = 521288629;
        w = 88675123;
    }
    unsigned int next() {
        unsigned int t = x ^ (x << 11);
        x = y; y = z; z = w;
        return w = (w ^ (w >> 19)) ^ (t ^ (t >> 8));
    }
    int next_int(int n) {
        return next() % n;
    }
    double next_double() {
        return next() / 4294967295.0;
    }
};

// --- Problem Specifics ---
constexpr int N = 30;
const int di[] = {0, -1, 0, 1}; // 0:L, 1:U, 2:R, 3:D
const int dj[] = {-1, 0, 1, 0};
const int to[8][4] = {
    {1, 0, -1, -1},
    {3, -1, -1, 0},
    {-1, -1, 3, 2},
    {-1, 2, 1, -1},
    {1, 0, 3, 2},
    {3, 2, 1, 0},
    {2, -1, 0, -1},
    {-1, 3, -1, 1}
};

std::array<std::array<int, N>, N> initial_tiles;
std::array<std::array<int, 4>, 8> rotated_type;

int rotate_once(int t) {
    if (t <= 3) return (t + 1) % 4;
    if (t == 4) return 5;
    if (t == 5) return 4;
    if (t == 6) return 7;
    if (t == 7) return 6;
    return -1;
}

void precompute_rotations() {
    for (int t = 0; t < 8; ++t) {
        rotated_type[t][0] = t;
        int current_t = t;
        for (int r = 1; r < 4; ++r) {
            current_t = rotate_once(current_t);
            rotated_type[t][r] = current_t;
        }
    }
}

long long calculate_score(const std::array<std::array<int, N>, N>& current_tiles, bool use_heuristic_score) {
    std::array<std::array<std::array<bool, 4>, N>, N> visited{};
    std::vector<int> loop_lengths;

    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            for (int start_d = 0; start_d < 4; ++start_d) {
                if (visited[i][j][start_d]) continue;
                
                if (to[current_tiles[i][j]][start_d] == -1) continue;

                std::vector<std::tuple<int, int, int>> path;
                int ci = i, cj = j;
                int d_entry = start_d;
                int len = 0;
                
                while (true) {
                    if (visited[ci][cj][d_entry]) {
                        len = 0;
                        break;
                    }
                    path.emplace_back(ci, cj, d_entry);
                    
                    int current_d_exit = to[current_tiles[ci][cj]][d_entry];
                    if (current_d_exit == -1) {
                        len = 0;
                        break;
                    }

                    len++;
                    int ni = ci + di[current_d_exit];
                    int nj = cj + dj[current_d_exit];

                    if (ni < 0 || ni >= N || nj < 0 || nj >= N) {
                        len = 0;
                        break;
                    }

                    int next_d_entry = (current_d_exit + 2) % 4;

                    if (ni == i && nj == j && next_d_entry == start_d) {
                        loop_lengths.push_back(len);
                        for (const auto& p : path) {
                            visited[std::get<0>(p)][std::get<1>(p)][std::get<2>(p)] = true;
                        }
                        break;
                    }

                    ci = ni;
                    cj = nj;
                    d_entry = next_d_entry;
                }
            }
        }
    }
    
    if (loop_lengths.size() < 2) {
        if (use_heuristic_score) {
            return loop_lengths.empty() ? 0 : loop_lengths[0];
        }
        return 0;
    }

    std::sort(loop_lengths.rbegin(), loop_lengths.rend());
    return (long long)loop_lengths[0] * loop_lengths[1];
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    Timer timer;
    XorShift rnd;

    for (int i = 0; i < N; ++i) {
        std::string row;
        std::cin >> row;
        for (int j = 0; j < N; ++j) {
            initial_tiles[i][j] = row[j] - '0';
        }
    }
    
    precompute_rotations();

    std::array<std::array<int, N>, N> current_rotations{};
    std::array<std::array<int, N>, N> best_rotations{};

    for (int i=0; i<N; ++i) {
        for (int j=0; j<N; ++j) {
            current_rotations[i][j] = rnd.next_int(4);
        }
    }

    std::array<std::array<int, N>, N> current_tiles;
    auto get_current_tiles = [&](const auto& rotations, auto& tiles) {
        for (int i = 0; i < N; ++i) {
            for (int j = 0; j < N; ++j) {
                tiles[i][j] = rotated_type[initial_tiles[i][j]][rotations[i][j]];
            }
        }
    };
    
    get_current_tiles(current_rotations, current_tiles);
    
    long long current_score = calculate_score(current_tiles, true);
    long long best_score = calculate_score(current_tiles, false);
    best_rotations = current_rotations;

    double time_limit = 2.95;
    double T_start = 5000;
    double T_end = 0.1;

    while(timer.get_elapsed() < time_limit) {
        double progress = timer.get_elapsed() / time_limit;
        double T = T_start * pow(T_end / T_start, progress);

        int r = rnd.next_int(N);
        int c = rnd.next_int(N);
        int old_rot = current_rotations[r][c];
        int new_rot = (old_rot + rnd.next_int(3) + 1) % 4;

        int old_tile_type = current_tiles[r][c];
        current_tiles[r][c] = rotated_type[initial_tiles[r][c]][new_rot];

        long long neighbor_score = calculate_score(current_tiles, true);
        
        double delta = (double)neighbor_score - current_score;

        if (delta > 0 || exp(delta / T) > rnd.next_double()) {
            current_rotations[r][c] = new_rot;
            current_score = neighbor_score;
            long long real_neighbor_score = calculate_score(current_tiles, false);
            if (real_neighbor_score > best_score) {
                best_score = real_neighbor_score;
                best_rotations = current_rotations;
            }
        } else {
            current_tiles[r][c] = old_tile_type;
        }
    }

    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            std::cout << best_rotations[i][j];
        }
    }
    std::cout << std::endl;

    return 0;
}