#include <iostream>
#include <vector>
#include <queue>
#include <unordered_map>
#include <chrono>
#include <tuple>
#include <algorithm>

using namespace std;

// Vehicle properties
int num_vehicles;
int vehicle_len[12];
bool vehicle_is_horiz[12];
int vehicle_fixed_coord[12];

// For outputting moves
struct Move {
    int id;
    char dir;
};

// State: positions of all vehicles
using State = vector<int>;

// Custom hasher for State (vector<int>)
struct VectorHasher {
    size_t operator()(const vector<int>& v) const {
        size_t seed = v.size();
        for (int i : v) {
            seed ^= i + 0x9e3779b9 + (seed << 6) + (seed >> 2);
        }
        return seed;
    }
};

// Helper to reconstruct board from a state
void build_board(const State& pos, int board[6][6]) {
    for (int r = 0; r < 6; ++r) for (int c = 0; c < 6; ++c) board[r][c] = 0;
    for (int i = 1; i <= num_vehicles; ++i) {
        if (vehicle_is_horiz[i]) {
            int r = vehicle_fixed_coord[i];
            int c = pos[i];
            for (int k = 0; k < vehicle_len[i]; ++k) board[r][c + k] = i;
        } else {
            int r = pos[i];
            int c = vehicle_fixed_coord[i];
            for (int k = 0; k < vehicle_len[i]; ++k) board[r + k][c] = i;
        }
    }
}

// Inner BFS to find min steps to solve
int solve_puzzle(const State& start_pos) {
    int goal_c = 6 - vehicle_len[1];
    queue<pair<State, int>> q;
    unordered_map<State, int, VectorHasher> dist;
    q.push({start_pos, 0});
    dist[start_pos] = 0;
    int board[6][6];

    while (!q.empty()) {
        State current_pos = q.front().first;
        int d = q.front().second;
        q.pop();

        if (current_pos[1] == goal_c) return d;
        if (d > 50) continue; // Optimization: prune deep searches unlikely to be optimal

        build_board(current_pos, board);

        for (int i = 1; i <= num_vehicles; ++i) {
            if (vehicle_is_horiz[i]) {
                int r = vehicle_fixed_coord[i];
                int c = current_pos[i];
                // Right
                if (c + vehicle_len[i] < 6 && board[r][c + vehicle_len[i]] == 0) {
                    State next_pos = current_pos; next_pos[i]++;
                    if (dist.find(next_pos) == dist.end()) {
                        dist[next_pos] = d + 1;
                        q.push({next_pos, d + 1});
                    }
                }
                // Left
                if (c > 0 && board[r][c - 1] == 0) {
                    State next_pos = current_pos; next_pos[i]--;
                    if (dist.find(next_pos) == dist.end()) {
                        dist[next_pos] = d + 1;
                        q.push({next_pos, d + 1});
                    }
                }
            } else { // Vertical
                int r = current_pos[i];
                int c = vehicle_fixed_coord[i];
                // Down
                if (r + vehicle_len[i] < 6 && board[r + vehicle_len[i]][c] == 0) {
                    State next_pos = current_pos; next_pos[i]++;
                    if (dist.find(next_pos) == dist.end()) {
                        dist[next_pos] = d + 1;
                        q.push({next_pos, d + 1});
                    }
                }
                // Up
                if (r > 0 && board[r - 1][c] == 0) {
                    State next_pos = current_pos; next_pos[i]--;
                    if (dist.find(next_pos) == dist.end()) {
                        dist[next_pos] = d + 1;
                        q.push({next_pos, d + 1});
                    }
                }
            }
        }
    }
    return -1; // Unsolvable
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int initial_board[6][6];
    int max_id = 0;
    for (int i = 0; i < 6; ++i) {
        for (int j = 0; j < 6; ++j) {
            cin >> initial_board[i][j];
            max_id = max(max_id, initial_board[i][j]);
        }
    }
    num_vehicles = max_id;

    bool processed[12] = {false};
    State initial_pos(num_vehicles + 1);

    for (int r = 0; r < 6; ++r) {
        for (int c = 0; c < 6; ++c) {
            int id = initial_board[r][c];
            if (id != 0 && !processed[id]) {
                processed[id] = true;
                if (c + 1 < 6 && initial_board[r][c + 1] == id) { // Horizontal
                    vehicle_is_horiz[id] = true;
                    vehicle_fixed_coord[id] = r;
                    initial_pos[id] = c;
                    int len = 0;
                    while (c + len < 6 && initial_board[r][c + len] == id) len++;
                    vehicle_len[id] = len;
                } else { // Vertical
                    vehicle_is_horiz[id] = false;
                    vehicle_fixed_coord[id] = c;
                    initial_pos[id] = r;
                    int len = 0;
                    while (r + len < 6 && initial_board[r + len][c] == id) len++;
                    vehicle_len[id] = len;
                }
            }
        }
    }

    auto start_time = chrono::high_resolution_clock::now();
    const long long time_limit_ms = 1950;

    int max_hardness = solve_puzzle(initial_pos);
    vector<Move> best_path;

    queue<pair<State, vector<Move>>> q;
    unordered_map<State, bool, VectorHasher> visited;

    q.push({initial_pos, {}});
    visited[initial_pos] = true;

    int board[6][6];
    
    while (!q.empty()) {
        auto now = chrono::high_resolution_clock::now();
        if (chrono::duration_cast<chrono::milliseconds>(now - start_time).count() > time_limit_ms) {
            break;
        }

        State current_pos = q.front().first;
        vector<Move> current_path = q.front().second;
        q.pop();

        build_board(current_pos, board);

        for (int i = 1; i <= num_vehicles; ++i) {
            if (vehicle_is_horiz[i]) {
                int r = vehicle_fixed_coord[i];
                int c = current_pos[i];
                State next_pos;
                // R
                if (c + vehicle_len[i] < 6 && board[r][c + vehicle_len[i]] == 0) {
                    next_pos = current_pos; next_pos[i]++;
                    if (visited.find(next_pos) == visited.end()) {
                        visited[next_pos] = true;
                        vector<Move> next_path = current_path; next_path.push_back({i, 'R'});
                        q.push({next_pos, next_path});
                        int hardness = solve_puzzle(next_pos);
                        if (hardness > max_hardness) {
                            max_hardness = hardness;
                            best_path = next_path;
                        }
                    }
                }
                // L
                if (c > 0 && board[r][c - 1] == 0) {
                    next_pos = current_pos; next_pos[i]--;
                    if (visited.find(next_pos) == visited.end()) {
                        visited[next_pos] = true;
                        vector<Move> next_path = current_path; next_path.push_back({i, 'L'});
                        q.push({next_pos, next_path});
                        int hardness = solve_puzzle(next_pos);
                        if (hardness > max_hardness) {
                            max_hardness = hardness;
                            best_path = next_path;
                        }
                    }
                }
            } else { // Vertical
                int r = current_pos[i];
                int c = vehicle_fixed_coord[i];
                State next_pos;
                // D
                if (r + vehicle_len[i] < 6 && board[r + vehicle_len[i]][c] == 0) {
                    next_pos = current_pos; next_pos[i]++;
                    if (visited.find(next_pos) == visited.end()) {
                        visited[next_pos] = true;
                        vector<Move> next_path = current_path; next_path.push_back({i, 'D'});
                        q.push({next_pos, next_path});
                        int hardness = solve_puzzle(next_pos);
                        if (hardness > max_hardness) {
                            max_hardness = hardness;
                            best_path = next_path;
                        }
                    }
                }
                // U
                if (r > 0 && board[r - 1][c] == 0) {
                    next_pos = current_pos; next_pos[i]--;
                    if (visited.find(next_pos) == visited.end()) {
                        visited[next_pos] = true;
                        vector<Move> next_path = current_path; next_path.push_back({i, 'U'});
                        q.push({next_pos, next_path});
                        int hardness = solve_puzzle(next_pos);
                        if (hardness > max_hardness) {
                            max_hardness = hardness;
                            best_path = next_path;
                        }
                    }
                }
            }
        }
    }

    cout << max_hardness << " " << best_path.size() << endl;
    for (const auto& move : best_path) {
        cout << move.id << " " << move.dir << endl;
    }

    return 0;
}