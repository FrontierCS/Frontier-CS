#include <iostream>
#include <vector>
#include <string>
#include <sstream>
#include <algorithm>
#include <map>
#include <cmath>
#include <chrono>
#include <random>
#include <queue>
#include <iomanip>

using namespace std;

// --- Timer ---
auto start_time = chrono::high_resolution_clock::now();
double time_limit = 1.95;

bool is_time_up() {
    auto current_time = chrono::high_resolution_clock::now();
    double elapsed_time = chrono::duration<double>(current_time - start_time).count();
    return elapsed_time > time_limit;
}

// --- Random Number Generator ---
mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());

// --- Utilities ---
int N, T;
int dr[] = {-1, 1, 0, 0}; // U, D, L, R
int dc[] = {0, 0, -1, 1};
char move_chars[] = {'U', 'D', 'L', 'R'};
map<char, int> move_map = {{'U', 0}, {'D', 1}, {'L', 2}, {'R', 3}};

int hex_to_int(char c) {
    if (c >= '0' && c <= '9') return c - '0';
    return c - 'a' + 10;
}

struct DSU {
    vector<int> parent;
    DSU(int n) {
        parent.resize(n);
        for (int i = 0; i < n; ++i) parent[i] = i;
    }
    int find(int i) {
        if (parent[i] == i) return i;
        return parent[i] = find(parent[i]);
    }
    void unite(int i, int j) {
        int root_i = find(i);
        int root_j = find(j);
        if (root_i != root_j) parent[root_i] = root_j;
    }
};

struct Board {
    vector<vector<int>> tiles;
    int empty_r, empty_c;

    Board() : tiles(N, vector<int>(N)) {}

    void find_empty() {
        for (int i = 0; i < N; ++i) {
            for (int j = 0; j < N; ++j) {
                if (tiles[i][j] == 0) {
                    empty_r = i;
                    empty_c = j;
                    return;
                }
            }
        }
    }

    bool is_valid(int r, int c) const {
        return r >= 0 && r < N && c >= 0 && c < N;
    }

    void apply_move(char move_char) {
        int d = move_map[move_char];
        int nr = empty_r + dr[d];
        int nc = empty_c + dc[d];
        if (is_valid(nr, nc)) {
            swap(tiles[empty_r][empty_c], tiles[nr][nc]);
            empty_r = nr;
            empty_c = nc;
        }
    }
};

// --- Target Finding (Simulated Annealing) ---
struct SA_State {
    vector<vector<int>> grid_types;
    double score;
    int empty_r = N - 1, empty_c = N - 1;

    SA_State(const map<int, int>& tile_counts) {
        grid_types.assign(N, vector<int>(N, 0));
        vector<int> tiles_to_place;
        for (auto const& [type, count] : tile_counts) {
            for (int i = 0; i < count; ++i) tiles_to_place.push_back(type);
        }
        shuffle(tiles_to_place.begin(), tiles_to_place.end(), rng);
        int k = 0;
        for (int i = 0; i < N; ++i) {
            for (int j = 0; j < N; ++j) {
                if (i == empty_r && j == empty_c) continue;
                grid_types[i][j] = tiles_to_place[k++];
            }
        }
        calc_score();
    }

    void calc_score() {
        int edges = 0, cycles = 0;
        DSU dsu(N * N);
        for (int i = 0; i < N; ++i) {
            for (int j = 0; j < N; ++j) {
                if (i == empty_r && j == empty_c) continue;
                // Down
                if (i + 1 < N && !(i + 1 == empty_r && j == empty_c)) {
                    if ((grid_types[i][j] & 8) && (grid_types[i+1][j] & 2)) {
                        edges++;
                        int u = i * N + j, v = (i + 1) * N + j;
                        if (dsu.find(u) == dsu.find(v)) cycles++; else dsu.unite(u, v);
                    }
                }
                // Right
                if (j + 1 < N && !(i == empty_r && j + 1 == empty_c)) {
                    if ((grid_types[i][j] & 4) && (grid_types[i][j+1] & 1)) {
                        edges++;
                        int u = i * N + j, v = i * N + j + 1;
                        if (dsu.find(u) == dsu.find(v)) cycles++; else dsu.unite(u, v);
                    }
                }
            }
        }
        int components = 0;
        for (int i = 0; i < N * N; ++i) {
            if (i == empty_r * N + empty_c) continue;
            if (dsu.parent[i] == i) components++;
        }
        score = -1000 * (components - 1) - 1000 * cycles + edges;
    }

    void step() {
        int r1, c1, r2, c2;
        do { r1 = rng() % N; c1 = rng() % N; } while (r1 == empty_r && c1 == empty_c);
        do { r2 = rng() % N; c2 = rng() % N; } while ((r2 == empty_r && c2 == empty_c) || (r1 == r2 && c1 == c2));
        swap(grid_types[r1][c1], grid_types[r2][c2]);
    }
};

// --- Puzzle Solving ---
string bfs_path_empty(int sr, int sc, int tr, int tc, const vector<pair<int, int>>& obstacles) {
    if (sr == tr && sc == tc) return "";
    queue<pair<pair<int, int>, string>> q;
    q.push({{sr, sc}, ""});
    vector<vector<bool>> visited(N, vector<bool>(N, false));
    for (auto p : obstacles) visited[p.first][p.second] = true;
    if(visited[sr][sc]) return "IMPOSSIBLE";
    visited[sr][sc] = true;

    while (!q.empty()) {
        auto curr = q.front(); q.pop();
        int r = curr.first.first, c = curr.first.second;
        string path = curr.second;
        for (int i = 0; i < 4; ++i) {
            int nr = r + dr[i], nc = c + dc[i];
            if (nr >= 0 && nr < N && nc >= 0 && nc < N && !visited[nr][nc]) {
                if (nr == tr && nc == tc) return path + move_chars[i];
                visited[nr][nc] = true;
                q.push({{nr, nc}, path + move_chars[i]});
            }
        }
    }
    return "IMPOSSIBLE";
}

string move_tile_greedily(Board& board, pair<int, int> tile_pos, pair<int, int> target_pos, const vector<pair<int, int>>& obstacles) {
    string path = "";
    int tr = tile_pos.first, tc = tile_pos.second;
    int target_r = target_pos.first, target_c = target_pos.second;

    auto move_empty_to = [&](int r, int c, const vector<pair<int, int>>& current_obstacles) {
        string empty_moves = bfs_path_empty(board.empty_r, board.empty_c, r, c, current_obstacles);
        for(char m : empty_moves) board.apply_move(m);
        path += empty_moves;
    };

    while (tc > target_c) {
        vector<pair<int, int>> current_obstacles = obstacles; current_obstacles.push_back({tr, tc});
        move_empty_to(tr, tc - 1, current_obstacles);
        board.apply_move('L'); path += 'L'; tc--;
    }
    while (tc < target_c) {
        vector<pair<int, int>> current_obstacles = obstacles; current_obstacles.push_back({tr, tc});
        move_empty_to(tr, tc + 1, current_obstacles);
        board.apply_move('R'); path += 'R'; tc++;
    }
    while (tr > target_r) {
        vector<pair<int, int>> current_obstacles = obstacles; current_obstacles.push_back({tr, tc});
        move_empty_to(tr - 1, tc, current_obstacles);
        board.apply_move('U'); path += 'U'; tr--;
    }
    while (tr < target_r) {
        vector<pair<int, int>> current_obstacles = obstacles; current_obstacles.push_back({tr, tc});
        move_empty_to(tr + 1, tc, current_obstacles);
        board.apply_move('D'); path += 'D'; tr++;
    }
    return path;
}


int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    cin >> N >> T;
    Board current_board;
    map<int, int> tile_counts;
    for (int i = 0; i < N; ++i) {
        string row; cin >> row;
        for (int j = 0; j < N; ++j) {
            current_board.tiles[i][j] = hex_to_int(row[j]);
            if (current_board.tiles[i][j] != 0) tile_counts[current_board.tiles[i][j]]++;
        }
    }
    current_board.find_empty();

    // 1. Find Target Configuration with SA
    SA_State best_state(tile_counts);
    double start_temp = 10, end_temp = 0.01;
    long long iter_count = 0;
    while (!is_time_up()) {
        SA_State current_state = best_state;
        current_state.step();
        current_state.calc_score();
        double temp = start_temp * pow(end_temp / start_temp, chrono::duration<double>(chrono::high_resolution_clock::now() - start_time).count() / time_limit);
        if (current_state.score > best_state.score || exp((current_state.score - best_state.score) / temp) > (double)rng() / mt19937::max()) {
            best_state = current_state;
        }
        iter_count++;
        if (best_state.score >= N*N-2) break;
    }
    vector<vector<int>> target_grid = best_state.grid_types;

    // 2. Solve puzzle
    string solution = "";
    vector<pair<int, int>> finalized_cells;

    int rows_to_solve = (N <= 4) ? N : N - 2;
    for (int r = 0; r < rows_to_solve; ++r) {
        for (int c = 0; c < N; ++c) {
            int target_type = target_grid[r][c];
            pair<int, int> current_pos = {-1, -1};
            if (current_board.tiles[r][c] == target_type) {
                bool found_other = false;
                for(int fr=0; fr<N; ++fr) for(int fc=0; fc<N; ++fc) {
                    bool is_final = false;
                    for(auto p : finalized_cells) if(p.first==fr && p.second==fc) is_final=true;
                    if(!is_final && current_board.tiles[fr][fc] == target_type && (fr != r || fc != c)) {
                        found_other = true; break;
                    }
                }
                if(!found_other) {
                    finalized_cells.push_back({r,c});
                    continue;
                }
            }

            for (int i = 0; i < N; ++i) {
                for (int j = 0; j < N; ++j) {
                    bool is_finalized = false;
                    for (auto p : finalized_cells) if (p.first == i && p.second == j) is_finalized = true;
                    if (!is_finalized && current_board.tiles[i][j] == target_type) {
                        current_pos = {i, j}; break;
                    }
                }
                if (current_pos.first != -1) break;
            }
            if(current_pos.first == -1) { // Should not happen if tile counts match
                 for(int i=0; i<N; ++i) for(int j=0; j<N; ++j) if(current_board.tiles[i][j]==target_type) current_pos = {i,j};
            }

            string moves = move_tile_greedily(current_board, current_pos, {r, c}, finalized_cells);
            solution += moves;
            finalized_cells.push_back({r, c});
        }
    }

    if (N > 4) {
        for (int c = 0; c < N - 2; ++c) {
            for (int r = N - 2; r < N; ++r) {
                 int target_type = target_grid[r][c];
                if (current_board.tiles[r][c] == target_type) {
                    finalized_cells.push_back({r,c});
                    continue;
                }
                 // If the tile for (N-1,c) is blocking (N-2,c)'s spot
                if(r == N-2 && current_board.tiles[r][c] == target_grid[r+1][c]){
                    string moves = move_tile_greedily(current_board, {r,c}, {r,c+1}, finalized_cells);
                    solution += moves;
                }

                pair<int, int> current_pos = {-1, -1};
                for (int i = N - 2; i < N; ++i) for (int j = c; j < N; ++j) {
                    bool is_finalized = false;
                    for(auto p:finalized_cells) if(p.first==i && p.second==j) is_finalized = true;
                    if(!is_finalized && current_board.tiles[i][j] == target_type){
                        current_pos = {i,j}; break;
                    }
                }
                if(current_pos.first == -1) {
                     for(int i=0; i<N; ++i) for(int j=0; j<N; ++j) {
                         bool is_finalized = false;
                         for(auto p:finalized_cells) if(p.first==i && p.second==j) is_finalized = true;
                         if(!is_finalized && current_board.tiles[i][j] == target_type) { current_pos = {i,j}; break; }
                     }
                }

                string moves = move_tile_greedily(current_board, current_pos, {r,c}, finalized_cells);
                solution += moves;
                finalized_cells.push_back({r,c});
            }
        }

        // Final 2x2 box, use greedy again
        vector<pair<int,int>> final_pos;
        for(int r=N-2; r<N; ++r) for(int c=N-2; c<N; ++c) final_pos.push_back({r,c});
        for(auto p : final_pos) {
            if(current_board.tiles[p.first][p.second] == target_grid[p.first][p.second]) {
                finalized_cells.push_back(p);
                continue;
            }
            int target_type = target_grid[p.first][p.second];
            pair<int, int> current_pos = {-1, -1};
            for(auto p2 : final_pos) {
                bool is_finalized = false;
                for(auto f : finalized_cells) if(f==p2) is_finalized=true;
                if(!is_finalized && current_board.tiles[p2.first][p2.second] == target_type) {
                    current_pos = p2;
                    break;
                }
            }
            string moves = move_tile_greedily(current_board, current_pos, p, finalized_cells);
            solution += moves;
            finalized_cells.push_back(p);
        }
    }
    cout << solution << endl;
    return 0;
}