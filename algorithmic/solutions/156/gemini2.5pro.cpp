#include <iostream>
#include <vector>
#include <string>
#include <chrono>
#include <random>
#include <algorithm>
#include <cmath>
#include <numeric>
#include <tuple>

// Constants
const int N = 30;
const int DI[] = {0, -1, 0, 1}; // L, U, R, D
const int DJ[] = {-1, 0, 1, 0};
const int TO[8][4] = {
    {1, 0, -1, -1}, {3, -1, -1, 0}, {-1, -1, 3, 2}, {-1, 2, 1, -1},
    {1, 0, 3, 2},   {3, 2, 1, 0},   {2, -1, 0, -1}, {-1, 3, -1, 1}
};

// State
int initial_tiles[N][N];
int rotations[N][N];
int current_tiles[N][N];
int best_rotations[N][N];

// For score calculation
bool path_visited[N][N][4];
std::vector<std::tuple<int, int, int>> path_nodes_buffer;

// Random number generator
std::mt19937 rng;

// Timer
std::chrono::high_resolution_clock::time_point start_time;
const double TIME_LIMIT = 1.95; 

int rotate_type(int type, int count) {
    if (count == 0) return type;
    if (type <= 3) {
        return (type + count) % 4;
    } else if (type <= 5) {
        return count % 2 == 0 ? type : 9 - type;
    } else {
        return count % 2 == 0 ? type : 13 - type;
    }
}

long long calculate_score() {
    bool visited[N][N][4] = {};
    std::vector<int> loops;

    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            for (int d_entry = 0; d_entry < 4; ++d_entry) {
                if (visited[i][j][d_entry] || TO[current_tiles[i][j]][d_entry] == -1) continue;
                
                path_nodes_buffer.clear();

                int si = i, sj = j, sd_entry = d_entry;
                int ci = i, cj = j, cd_entry = d_entry;
                int length = 0;
                bool is_loop = true;

                while (true) {
                    if (path_visited[ci][cj][cd_entry] || visited[ci][cj][cd_entry]) { is_loop = false; break; }
                    
                    path_visited[ci][cj][cd_entry] = true;
                    path_nodes_buffer.emplace_back(ci, cj, cd_entry);

                    int type = current_tiles[ci][cj];
                    int d_exit = TO[type][cd_entry];
                    
                    if (d_exit == -1) { is_loop = false; break; }

                    int ni = ci + DI[d_exit];
                    int nj = cj + DJ[d_exit];

                    if (ni < 0 || ni >= N || nj < 0 || nj >= N) { is_loop = false; break; }

                    int nd_entry = (d_exit + 2) % 4;
                    length++;
                    ci = ni; cj = nj; cd_entry = nd_entry;

                    if (ci == si && cj == sj && cd_entry == sd_entry) break;
                }
                
                if (is_loop && length > 0) {
                    loops.push_back(length);
                    for (const auto& node : path_nodes_buffer) {
                        visited[std::get<0>(node)][std::get<1>(node)][std::get<2>(node)] = true;
                    }
                }
                for (const auto& node : path_nodes_buffer) {
                    path_visited[std::get<0>(node)][std::get<1>(node)][std::get<2>(node)] = false;
                }
            }
        }
    }

    if (loops.size() < 2) return 0;

    std::sort(loops.rbegin(), loops.rend());
    return (long long)loops[0] * loops[1];
}

void solve() {
    std::uniform_int_distribution<> rot_dist(0, 3);
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            rotations[i][j] = rot_dist(rng);
            current_tiles[i][j] = rotate_type(initial_tiles[i][j], rotations[i][j]);
        }
    }

    long long current_score = calculate_score();
    long long best_score = current_score;
    for(int i=0; i<N; ++i) for(int j=0; j<N; ++j) best_rotations[i][j] = rotations[i][j];
    
    double T_start = 3000.0;
    double T_end = 10.0;
    
    std::uniform_int_distribution<> pos_dist(0, N - 1);
    std::uniform_int_distribution<> add_rot_dist(1, 3);

    while (true) {
        auto current_time = std::chrono::high_resolution_clock::now();
        double elapsed_time = std::chrono::duration_cast<std::chrono::duration<double>>(current_time - start_time).count();
        if (elapsed_time > TIME_LIMIT) break;

        int r = pos_dist(rng);
        int c = pos_dist(rng);
        
        int old_rot = rotations[r][c];
        int new_rot = (old_rot + add_rot_dist(rng)) % 4;
        
        rotations[r][c] = new_rot;
        int old_tile_type = current_tiles[r][c];
        current_tiles[r][c] = rotate_type(initial_tiles[r][c], new_rot);
        
        long long new_score = calculate_score();
        
        double temp = T_start + (T_end - T_start) * elapsed_time / TIME_LIMIT;
        
        if (new_score > current_score || std::uniform_real_distribution<>(0.0, 1.0)(rng) < exp((double)(new_score - current_score) / temp)) {
            current_score = new_score;
            if (current_score > best_score) {
                best_score = current_score;
                for(int i=0; i<N; ++i) for(int j=0; j<N; ++j) best_rotations[i][j] = rotations[i][j];
            }
        } else {
            rotations[r][c] = old_rot;
            current_tiles[r][c] = old_tile_type;
        }
    }
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    start_time = std::chrono::high_resolution_clock::now();
    std::random_device rd;
    rng.seed(rd());
    path_nodes_buffer.reserve(N * N * 2);

    for (int i = 0; i < N; ++i) {
        std::string row;
        std::cin >> row;
        for (int j = 0; j < N; ++j) {
            initial_tiles[i][j] = row[j] - '0';
        }
    }
    
    solve();

    std::string result = "";
    result.reserve(N * N);
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            result += std::to_string(best_rotations[i][j]);
        }
    }
    std::cout << result << std::endl;

    return 0;
}