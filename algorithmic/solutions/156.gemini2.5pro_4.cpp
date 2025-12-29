#include <iostream>
#include <vector>
#include <string>
#include <chrono>
#include <random>
#include <algorithm>
#include <cmath>
#include <tuple>

namespace {
// Constants
constexpr int N = 30;
constexpr int di[] = {0, -1, 0, 1}; // 0:L, 1:U, 2:R, 3:D
constexpr int dj[] = {-1, 0, 1, 0};
constexpr int to[8][4] = {
	{1, 0, -1, -1}, // 0
	{3, -1, -1, 0}, // 1
	{-1, -1, 3, 2}, // 2
	{-1, 2, 1, -1}, // 3
	{1, 0, 3, 2},   // 4
	{3, 2, 1, 0},   // 5
	{2, -1, 0, -1}, // 6
	{-1, 3, -1, 1}, // 7
};
constexpr int rot_map_03[] = {1, 2, 3, 0};
const double TIME_LIMIT = 2.95; 

// State variables
int initial_tiles[N][N];
int rotations[N][N];
int best_rotations[N][N];

// RNG
std::mt19937 rng(std::chrono::steady_clock::now().time_since_epoch().count());

// Timer
auto start_time = std::chrono::steady_clock::now();

int get_rotated_tile(int type, int rot) {
    rot &= 3;
    if (rot == 0) return type;
    if (type <= 3) {
        int current_type = type;
        for (int i = 0; i < rot; ++i) {
            current_type = rot_map_03[current_type];
        }
        return current_type;
    }
    // For types 4,5 and 6,7, an odd number of rotations flips them.
    if (rot & 1) return type ^ 1;
    return type;
}

long long calculate_score(const int current_rotations[N][N]) {
    int current_tiles[N][N];
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            current_tiles[i][j] = get_rotated_tile(initial_tiles[i][j], current_rotations[i][j]);
        }
    }

    bool visited[N][N][4] = {};
    std::vector<int> loop_lengths;

    for (int si = 0; si < N; ++si) {
        for (int sj = 0; sj < N; ++sj) {
            for (int sd = 0; sd < 4; ++sd) {
                if (visited[si][sj][sd] || to[current_tiles[si][sj]][sd] == -1) continue;
                
                std::vector<std::tuple<int, int, int>> path;
                int i = si, j = sj, d = sd;
                int length = 0;
                
                while (true) {
                    if (visited[i][j][d]) {
                        length = 0; 
                        break;
                    }
                    path.emplace_back(i, j, d);

                    int tile_type = current_tiles[i][j];
                    int d2 = to[tile_type][d];

                    if (d2 == -1) {
                        length = 0;
                        break;
                    }

                    i += di[d2];
                    j += dj[d2];
                    length++;

                    if (i < 0 || i >= N || j < 0 || j >= N) {
                        length = 0;
                        break;
                    }

                    d = (d2 + 2) & 3;

                    if (i == si && j == sj && d == sd) {
                        break;
                    }
                }

                if (length > 0) {
                    loop_lengths.push_back(length);
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

void solve() {
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            int best_rot = rng() % 4;
            if (j == N/2 - 1 || j == N/2) {
                int min_crossings = 5;
                for (int r = 0; r < 4; ++r) {
                    int type = get_rotated_tile(initial_tiles[i][j], r);
                    int crossings = 0;
                    if (j == N/2 - 1 && to[type][2] != -1) crossings++;
                    if (j == N/2 && to[type][0] != -1) crossings++;
                    
                    if (crossings < min_crossings) {
                        min_crossings = crossings;
                        best_rot = r;
                    } else if (crossings == min_crossings && (rng() & 1)) {
                        best_rot = r;
                    }
                }
            }
            rotations[i][j] = best_rot;
        }
    }
    
    long long current_score = calculate_score(rotations);
    long long best_score = current_score;
    for (int i=0; i<N; ++i) for (int j=0; j<N; ++j) best_rotations[i][j] = rotations[i][j];

    double T_start = 50000;
    double T_end = 1.0;
    
    while (true) {
        auto current_time = std::chrono::steady_clock::now();
        double elapsed_time = std::chrono::duration_cast<std::chrono::duration<double>>(current_time - start_time).count();
        if (elapsed_time > TIME_LIMIT) break;

        double T = T_start * pow(T_end / T_start, elapsed_time / TIME_LIMIT);

        if ((rng() % 10) < 8) {
            int r = rng() % N;
            int c = rng() % N;
            int old_rot = rotations[r][c];
            int new_rot = rng() % 4;
            if (new_rot == old_rot) new_rot = (new_rot + 1) & 3;
            
            rotations[r][c] = new_rot;
            long long new_score = calculate_score(rotations);
            
            double prob = exp((double)(new_score - current_score) / T);
            if (prob > (double)rng() / rng.max()) {
                current_score = new_score;
                if (current_score > best_score) {
                    best_score = current_score;
                    for(int i=0; i<N; ++i) for(int j=0; j<N; ++j) best_rotations[i][j] = rotations[i][j];
                }
            } else {
                rotations[r][c] = old_rot;
            }
        } else {
            int r = rng() % (N - 1);
            int c = rng() % (N - 1);
            int old_rots[2][2];
            old_rots[0][0] = rotations[r][c]; old_rots[0][1] = rotations[r][c+1];
            old_rots[1][0] = rotations[r+1][c]; old_rots[1][1] = rotations[r+1][c+1];
            
            rotations[r][c] = rng() % 4; rotations[r][c+1] = rng() % 4;
            rotations[r+1][c] = rng() % 4; rotations[r+1][c+1] = rng() % 4;

            long long new_score = calculate_score(rotations);

            double prob = exp((double)(new_score - current_score) / T);
            if (prob > (double)rng() / rng.max()) {
                current_score = new_score;
                if (current_score > best_score) {
                    best_score = current_score;
                    for(int i=0; i<N; ++i) for(int j=0; j<N; ++j) best_rotations[i][j] = rotations[i][j];
                }
            } else {
                rotations[r][c] = old_rots[0][0]; rotations[r][c+1] = old_rots[0][1];
                rotations[r+1][c] = old_rots[1][0]; rotations[r+1][c+1] = old_rots[1][1];
            }
        }
    }
}
} // anonymous namespace

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
    
    solve();

    std::string out_str;
    out_str.reserve(N*N);
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            out_str += std::to_string(best_rotations[i][j]);
        }
    }
    std::cout << out_str << std::endl;

    return 0;
}