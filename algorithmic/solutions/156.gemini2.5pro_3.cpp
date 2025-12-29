#include <iostream>
#include <vector>
#include <string>
#include <array>
#include <numeric>
#include <algorithm>
#include <chrono>
#include <random>
#include <cmath>
#include <tuple>
#include <map>

using namespace std;

constexpr int N = 30;
constexpr double TIME_LIMIT = 2.8;

const int di[] = {0, -1, 0, 1};
const int dj[] = {-1, 0, 1, 0};
const int to[8][4] = {
    {1, 0, -1, -1},
    {3, -1, -1, 0},
    {-1, -1, 3, 2},
    {-1, 2, 1, -1},
    {1, 0, 3, 2},
    {3, 2, 1, 0},
    {2, -1, 0, -1},
    {-1, 3, -1, 1},
};
int rotate_tile[8][4];

array<array<int, N>, N> initial_tiles;
array<array<int, N>, N> current_rotations;
array<array<int, N>, N> best_rotations;

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

    int next_int(int l, int r) {
        return l + next() % (r - l + 1);
    }

    double next_double() {
        return next() / (double)UINT32_MAX;
    }
};

XorShift rnd;

long long calculate_score(const array<array<int, N>, N>& tiles) {
    vector<int> lengths;
    array<array<array<int, 4>, N>, N> visited{};
    int component_id = 1;

    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            for (int d_start = 0; d_start < 4; ++d_start) {
                if (visited[i][j][d_start]) continue;

                int ci = i, cj = j, cd = d_start;
                map<tuple<int, int, int>, int> path_indices;
                int path_len = 0;
                
                while (true) {
                    if (ci < 0 || ci >= N || cj < 0 || cj >= N) break;
                    
                    if (visited[ci][cj][cd]) {
                        if (visited[ci][cj][cd] == component_id) { // Cycle
                            auto it = path_indices.find({ci, cj, cd});
                            if (it != path_indices.end()) {
                                int len = path_len - it->second;
                                lengths.push_back(len);
                            }
                        }
                        break;
                    }
                    
                    visited[ci][cj][cd] = component_id;
                    path_indices[{ci, cj, cd}] = path_len;
                    
                    int type = tiles[ci][cj];
                    int exit_d = to[type][cd];
                    if (exit_d == -1) break;
                    
                    path_len++;
                    ci += di[exit_d];
                    cj += dj[exit_d];
                    cd = (exit_d + 2) % 4;
                }
                component_id++;
            }
        }
    }
    sort(lengths.rbegin(), lengths.rend());
    long long L1 = lengths.size() > 0 ? lengths[0] : 0;
    long long L2 = lengths.size() > 1 ? lengths[1] : 0;
    return L1 * L2;
}

void solve() {
    auto start_time = chrono::high_resolution_clock::now();

    for (int i = 0; i < N; ++i) {
        string row;
        cin >> row;
        for (int j = 0; j < N; ++j) {
            initial_tiles[i][j] = row[j] - '0';
        }
    }

    for (int i = 0; i < 4; ++i) for (int j = 0; j < 4; ++j) rotate_tile[i][j] = (i + j) % 4;
    for (int i = 4; i < 6; ++i) for (int j = 0; j < 4; ++j) rotate_tile[i][j] = 4 + ((i - 4 + j) % 2);
    for (int i = 6; i < 8; ++i) for (int j = 0; j < 4; ++j) rotate_tile[i][j] = 6 + ((i - 6 + j) % 2);

    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            current_rotations[i][j] = rnd.next_int(0, 3);
        }
    }
    best_rotations = current_rotations;

    array<array<int, N>, N> current_tiles;
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            current_tiles[i][j] = rotate_tile[initial_tiles[i][j]][current_rotations[i][j]];
        }
    }

    long long current_score = calculate_score(current_tiles);
    long long best_score = current_score;

    double start_temp = 50000;
    double end_temp = 10;

    while (true) {
        auto current_time = chrono::high_resolution_clock::now();
        double elapsed_time = chrono::duration<double>(current_time - start_time).count();
        if (elapsed_time > TIME_LIMIT) {
            break;
        }

        double temp = start_temp + (end_temp - start_temp) * elapsed_time / TIME_LIMIT;

        int r = rnd.next_int(0, N - 1);
        int c = rnd.next_int(0, N - 1);
        int old_rot = current_rotations[r][c];
        int new_rot = (old_rot + rnd.next_int(1, 3)) % 4;

        int old_tile_type = current_tiles[r][c];
        current_rotations[r][c] = new_rot;
        current_tiles[r][c] = rotate_tile[initial_tiles[r][c]][new_rot];

        long long new_score = calculate_score(current_tiles);

        double delta = (double)new_score - current_score;
        if (delta > 0 || exp(delta / temp) > rnd.next_double()) {
            current_score = new_score;
            if (current_score > best_score) {
                best_score = current_score;
                best_rotations = current_rotations;
            }
        } else {
            current_rotations[r][c] = old_rot;
            current_tiles[r][c] = old_tile_type;
        }
    }

    string result_str = "";
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            result_str += to_string(best_rotations[i][j]);
        }
    }
    cout << result_str << endl;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    solve();
    return 0;
}