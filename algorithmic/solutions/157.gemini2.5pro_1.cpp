#include <iostream>
#include <vector>
#include <string>
#include <map>
#include <chrono>
#include <random>
#include <algorithm>
#include <cmath>
#include <queue>
#include <numeric>

using namespace std;

// --- Timer ---
auto start_time = chrono::high_resolution_clock::now();
double time_limit = 2.95; // seconds

bool is_time_up() {
    auto current_time = chrono::high_resolution_clock::now();
    chrono::duration<double> elapsed = current_time - start_time;
    return elapsed.count() > time_limit;
}

// --- Random Number Generator ---
mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());

// --- Globals ---
int N, T;
const int dr[] = {-1, 1, 0, 0};
const int dc[] = {0, 0, -1, 1};
const char move_chars[] = {'U', 'D', 'L', 'R'};
const int opposite_move[] = {1, 0, 3, 2}; // U->D, D->U, L->R, R->L

// --- Data Structures ---
struct State {
    vector<vector<int>> board;
    int empty_r, empty_c;

    State(int n) : board(n, vector<int>(n)), empty_r(-1), empty_c(-1) {}
};

// --- DSU for tree evaluation ---
struct DSU {
    vector<int> parent;
    DSU(int n) {
        parent.resize(n);
        iota(parent.begin(), parent.end(), 0);
    }
    int find(int i) {
        if (parent[i] == i) return i;
        return parent[i] = find(parent[i]);
    }
    void unite(int i, int j) {
        int root_i = find(i);
        int root_j = find(j);
        if (root_i != root_j) {
            parent[root_i] = root_j;
        }
    }
};

// --- Evaluation for SA ---
long long evaluate(const vector<vector<int>>& board) {
    DSU dsu(N * N);
    int edges = 0;
    int cycles = 0;
    vector<bool> has_tile(N * N, false);
    int tile_count = 0;

    for (int r = 0; r < N; ++r) {
        for (int c = 0; c < N; ++c) {
            if (board[r][c] > 0) {
                has_tile[r * N + c] = true;
                tile_count++;
            }
        }
    }

    for (int r = 0; r < N; ++r) {
        for (int c = 0; c < N; ++c) {
            if (board[r][c] == 0) continue;

            // Down connection
            if (r + 1 < N && board[r + 1][c] != 0 && (board[r][c] & 8) && (board[r + 1][c] & 2)) {
                int u = r * N + c;
                int v = (r + 1) * N + c;
                if (dsu.find(u) == dsu.find(v)) {
                    cycles++;
                } else {
                    dsu.unite(u, v);
                    edges++;
                }
            }
            // Right connection
            if (c + 1 < N && board[r][c + 1] != 0 && (board[r][c] & 4) && (board[r][c + 1] & 1)) {
                int u = r * N + c;
                int v = r * N + c + 1;
                if (dsu.find(u) == dsu.find(v)) {
                    cycles++;
                } else {
                    dsu.unite(u, v);
                    edges++;
                }
            }
        }
    }

    map<int, int> component_sizes;
    int max_comp_size = 0;
    for (int i = 0; i < N * N; ++i) {
        if (has_tile[i]) {
            component_sizes[dsu.find(i)]++;
        }
    }
    for (auto const& [root, size] : component_sizes) {
        max_comp_size = max(max_comp_size, size);
    }
    
    if (cycles > 0) {
        return -1e12 + cycles * -1000 + max_comp_size;
    }
    
    if (max_comp_size == N*N - 1) return 1e12;

    return max_comp_size * 10000 - abs(edges - (tile_count - 1));
}


// --- Puzzle Solver ---
string path_bfs(int r_start, int c_start, int r_end, int c_end, const State& current_state, const vector<vector<bool>>& avoid) {
    queue<pair<pair<int, int>, string>> q;
    q.push({{r_start, c_start}, ""});
    vector<vector<bool>> visited(N, vector<bool>(N, false));
    visited[r_start][c_start] = true;

    while (!q.empty()) {
        auto curr = q.front();
        q.pop();
        int r = curr.first.first;
        int c = curr.first.second;
        string path = curr.second;

        if (r == r_end && c == c_end) {
            return path;
        }

        for (int i = 0; i < 4; ++i) {
            int nr = r + dr[i];
            int nc = c + dc[i];
            if (nr >= 0 && nr < N && nc >= 0 && nc < N && !visited[nr][nc] && !avoid[nr][nc]) {
                visited[nr][nc] = true;
                q.push({{nr, nc}, path + move_chars[i]});
            }
        }
    }
    return ""; // Should not happen
}

string moves_str;

void move_tile(State& state, pair<int, int> from, pair<int, int> to, const vector<vector<bool>>& solved_mask,
               vector<vector<pair<int, int>>>& current_pos_of_initial) {

    auto update_pos = [&](int r, int c, int nr, int nc){
        pair<int, int> p1_initial = { -1, -1 }, p2_initial = { -1, -1 };
        for(int i=0; i<N; ++i) for(int j=0; j<N; ++j) {
            if (current_pos_of_initial[i][j] == make_pair(r, c)) p1_initial = {i, j};
            if (current_pos_of_initial[i][j] == make_pair(nr, nc)) p2_initial = {i, j};
        }
        if (p1_initial.first != -1) current_pos_of_initial[p1_initial.first][p1_initial.second] = {nr, nc};
        if (p2_initial.first != -1) current_pos_of_initial[p2_initial.first][p2_initial.second] = {r, c};
    };
    
    auto apply_move_and_update = [&](State& s, char move_char) {
        int move_idx = -1;
        if (move_char == 'U') move_idx = 0;
        if (move_char == 'D') move_idx = 1;
        if (move_char == 'L') move_idx = 2;
        if (move_char == 'R') move_idx = 3;

        int tile_r = s.empty_r - dr[move_idx];
        int tile_c = s.empty_c - dc[move_idx];

        update_pos(s.empty_r, s.empty_c, tile_r, tile_c);
        swap(s.board[s.empty_r][s.empty_c], s.board[tile_r][tile_c]);
        s.empty_r = tile_r;
        s.empty_c = tile_c;
        moves_str += move_char;
    };
    
    auto move_empty_and_update = [&](State& s, int r_end, int c_end, const vector<vector<bool>>& avoid_mask) {
        string path = path_bfs(s.empty_r, s.empty_c, r_end, c_end, s, avoid_mask);
        for (char move_char : path) {
            apply_move_and_update(s, move_char);
        }
    };
    
    vector<vector<bool>> tile_path_avoid = solved_mask;
    string tile_path_str = path_bfs(from.first, from.second, to.first, to.second, state, tile_path_avoid);

    pair<int, int> current_tile_pos = from;

    for (char move : tile_path_str) {
        int move_idx = -1;
        if (move == 'U') move_idx = 0;
        if (move == 'D') move_idx = 1;
        if (move == 'L') move_idx = 2;
        if (move == 'R') move_idx = 3;

        pair<int, int> next_tile_pos = {current_tile_pos.first + dr[move_idx], current_tile_pos.second + dc[move_idx]};
        
        vector<vector<bool>> empty_avoid = solved_mask;
        empty_avoid[current_tile_pos.first][current_tile_pos.second] = true;
        move_empty_and_update(state, next_tile_pos.first, next_tile_pos.second, empty_avoid);
        
        apply_move_and_update(state, move_chars[opposite_move[move_idx]]);
        current_tile_pos = next_tile_pos;
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    cin >> N >> T;
    time_limit = (N < 8) ? 1.95 : 2.95;

    State initial_state(N);
    vector<int> tile_counts(16, 0);
    vector<vector<int>> initial_tiles(N, vector<int>(N));

    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            char c;
            cin >> c;
            int val;
            if (c >= '0' && c <= '9') val = c - '0';
            else val = c - 'a' + 10;
            initial_state.board[i][j] = val;
            initial_tiles[i][j] = val;
            if (val == 0) {
                initial_state.empty_r = i;
                initial_state.empty_c = j;
            } else {
                tile_counts[val]++;
            }
        }
    }
    
    // --- Part 1: Find Target Configuration using Simulated Annealing ---
    vector<int> tiles;
    for (int i = 1; i < 16; ++i) {
        for (int j = 0; j < tile_counts[i]; ++j) {
            tiles.push_back(i);
        }
    }

    vector<vector<int>> best_target_board(N, vector<int>(N));
    long long best_score = -2e18;

    vector<vector<int>> current_board(N, vector<int>(N));
    shuffle(tiles.begin(), tiles.end(), rng);
    int k = 0;
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            if (i == N - 1 && j == N - 1) {
                current_board[i][j] = 0;
            } else {
                current_board[i][j] = tiles[k++];
            }
        }
    }

    long long current_score = evaluate(current_board);

    double start_temp = 1000, end_temp = 0.1;
    int iter_count = 0;

    while (!is_time_up()) {
        iter_count++;
        double temp = start_temp * pow(end_temp / start_temp, (double)(chrono::high_resolution_clock::now() - start_time).count() / (time_limit * 1e9));

        int r1 = rng() % N, c1 = rng() % N;
        int r2 = rng() % N, c2 = rng() % N;
        if (current_board[r1][c1] == 0 || current_board[r2][c2] == 0 || (r1 == r2 && c1 == c2)) {
            continue;
        }

        swap(current_board[r1][c1], current_board[r2][c2]);
        long long new_score = evaluate(current_board);

        if (new_score > current_score || (exp((new_score - current_score) / temp) > uniform_real_distribution<double>(0.0, 1.0)(rng))) {
            current_score = new_score;
            if (current_score > best_score) {
                best_score = current_score;
                best_target_board = current_board;
            }
        } else {
            swap(current_board[r1][c1], current_board[r2][c2]);
        }
        if (best_score >= 1e12 && iter_count > 1000) break;
    }

    // --- Part 2: Solve Puzzle ---
    vector<vector<bool>> solved_mask(N, vector<bool>(N, false));
    vector<vector<pair<int, int>>> target_pos_of_initial(N, vector<pair<int, int>>(N, {-1, -1}));
    vector<vector<pair<int, int>>> current_pos_of_initial(N, vector<pair<int, int>>(N));
    for(int i=0; i<N; ++i) for(int j=0; j<N; ++j) current_pos_of_initial[i][j] = {i, j};

    // Bipartite matching (greedy)
    map<int, vector<pair<int, int>>> initial_pos, target_pos;
    for(int i=0; i<N; ++i) for(int j=0; j<N; ++j) {
        if(initial_tiles[i][j] != 0) initial_pos[initial_tiles[i][j]].push_back({i, j});
        if(best_target_board[i][j] != 0) target_pos[best_target_board[i][j]].push_back({i, j});
    }

    for(auto const& [type, t_pos] : target_pos) {
        vector<pair<int, int>> i_pos = initial_pos[type];
        vector<bool> used(i_pos.size(), false);
        for(const auto& tp : t_pos) {
            int best_idx = -1;
            int min_dist = 1e9;
            for(int i=0; i<i_pos.size(); ++i) {
                if(!used[i]) {
                    int dist = abs(tp.first - i_pos[i].first) + abs(tp.second - i_pos[i].second);
                    if(dist < min_dist) {
                        min_dist = dist;
                        best_idx = i;
                    }
                }
            }
            used[best_idx] = true;
            target_pos_of_initial[i_pos[best_idx].first][i_pos[best_idx].second] = tp;
        }
    }
    
    State current_state = initial_state;
    for (int d = 0; d < N / 2; ++d) {
        // Top row
        for (int j = d; j < N - 1 - d; ++j) {
            pair<int, int> target_cell = {d, j};
            pair<int, int> initial_tile_pos = {-1, -1};
            for(int r=0; r<N; ++r) for(int c=0; c<N; ++c) if(target_pos_of_initial[r][c] == target_cell) initial_tile_pos = {r, c};
            
            pair<int, int> current_tile_pos = current_pos_of_initial[initial_tile_pos.first][initial_tile_pos.second];
            if (current_tile_pos != target_cell) {
                move_tile(current_state, current_tile_pos, target_cell, solved_mask, current_pos_of_initial);
            }
            solved_mask[d][j] = true;
        }

        // Right column
        for (int i = d; i < N - 1 - d; ++i) {
            pair<int, int> target_cell = {i, N - 1 - d};
            pair<int, int> initial_tile_pos = {-1, -1};
            for(int r=0; r<N; ++r) for(int c=0; c<N; ++c) if(target_pos_of_initial[r][c] == target_cell) initial_tile_pos = {r, c};
            
            pair<int, int> current_tile_pos = current_pos_of_initial[initial_tile_pos.first][initial_tile_pos.second];
             if (current_tile_pos != target_cell) {
                move_tile(current_state, current_tile_pos, target_cell, solved_mask, current_pos_of_initial);
            }
            solved_mask[i][N - 1 - d] = true;
        }
        
        // Bottom row
        for (int j = N - 1 - d; j > d; --j) {
            pair<int, int> target_cell = {N - 1 - d, j};
            pair<int, int> initial_tile_pos = {-1, -1};
            for(int r=0; r<N; ++r) for(int c=0; c<N; ++c) if(target_pos_of_initial[r][c] == target_cell) initial_tile_pos = {r, c};
            
            pair<int, int> current_tile_pos = current_pos_of_initial[initial_tile_pos.first][initial_tile_pos.second];
             if (current_tile_pos != target_cell) {
                move_tile(current_state, current_tile_pos, target_cell, solved_mask, current_pos_of_initial);
            }
            solved_mask[N - 1 - d][j] = true;
        }

        // Left column
        for (int i = N - 1 - d; i > d; --i) {
            pair<int, int> target_cell = {i, d};
            pair<int, int> initial_tile_pos = {-1, -1};
            for(int r=0; r<N; ++r) for(int c=0; c<N; ++c) if(target_pos_of_initial[r][c] == target_cell) initial_tile_pos = {r, c};
            
            pair<int, int> current_tile_pos = current_pos_of_initial[initial_tile_pos.first][initial_tile_pos.second];
             if (current_tile_pos != target_cell) {
                move_tile(current_state, current_tile_pos, target_cell, solved_mask, current_pos_of_initial);
            }
            solved_mask[i][d] = true;
        }
    }

    cout << moves_str << endl;

    return 0;
}