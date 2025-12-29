#include <iostream>
#include <vector>
#include <string>
#include <map>
#include <random>
#include <algorithm>
#include <chrono>
#include <queue>
#include <tuple>

using namespace std;

// Constants and Typedefs
constexpr int MAX_N = 10;
constexpr int DR[] = {-1, 1, 0, 0};
constexpr int DC[] = {0, 0, -1, 1};

int N, T_max;
vector<vector<int>> initial_board;
pair<int, int> initial_empty;
vector<vector<int>> target_board;
pair<int, int> target_empty = {-1, -1};

string ans_moves = "";
vector<vector<int>> current_board;
pair<int, int> current_empty;
map<pair<int, int>, pair<int, int>> pos_to_initial;

struct DSU {
    vector<int> parent;
    DSU(int n) {
        parent.resize(n);
        for(int i=0; i<n; ++i) parent[i] = i;
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

int hex_to_int(char c) {
    if (c >= '0' && c <= '9') return c - '0';
    return c - 'a' + 10;
}

void apply_move_tracked(char move_char) {
    int er = current_empty.first, ec = current_empty.second;
    int tile_r = er, tile_c = ec;
    if (move_char == 'U') tile_r--; else if (move_char == 'D') tile_r++;
    else if (move_char == 'L') tile_c--; else if (move_char == 'R') tile_c++;
    
    swap(current_board[er][ec], current_board[tile_r][tile_c]);
    swap(pos_to_initial[{er,ec}], pos_to_initial[{tile_r,tile_c}]);
    current_empty = {tile_r, tile_c};
    ans_moves += move_char;
}

void move_empty_to_tracked(pair<int, int> target, const vector<pair<int, int>>& forbidden) {
    queue<pair<int, int>> q; q.push(current_empty);
    map<pair<int, int>, pair<int, int>> parent; parent[current_empty] = {-1, -1};
    vector<vector<bool>> visited(N, vector<bool>(N, false));
    if (current_empty.first >= 0) visited[current_empty.first][current_empty.second] = true;
    for (const auto& f : forbidden) visited[f.first][f.second] = true;
    
    pair<int, int> final_pos = {-1, -1};
    while (!q.empty()) {
        pair<int, int> curr = q.front(); q.pop();
        if (curr == target) { final_pos = curr; break; }
        for (int i = 0; i < 4; ++i) {
            int nr = curr.first + DR[i], nc = curr.second + DC[i];
            if (nr >= 0 && nr < N && nc >= 0 && nc < N && !visited[nr][nc]) {
                visited[nr][nc] = true; q.push({nr, nc}); parent[{nr, nc}] = curr;
            }
        }
    }
    if (final_pos.first == -1) return;
    vector<pair<int, int>> path; pair<int, int> p = final_pos;
    while (p.first != -1) { path.push_back(p); p = parent[p]; }
    reverse(path.begin(), path.end());
    for (size_t i = 1; i < path.size(); ++i) {
        int dr = path[i].first - path[i-1].first, dc = path[i].second - path[i-1].second;
        char mc;
        if (dr == -1) mc = 'U'; else if (dr == 1) mc = 'D'; else if (dc == -1) mc = 'L'; else mc = 'R';
        apply_move_tracked(mc);
    }
}


int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    auto start_time = chrono::high_resolution_clock::now();

    cin >> N >> T_max;
    initial_board.assign(N, vector<int>(N));
    map<int, int> initial_counts;
    for (int i = 0; i < N; ++i) {
        string row;
        cin >> row;
        for (int j = 0; j < N; ++j) {
            initial_board[i][j] = hex_to_int(row[j]);
            if (initial_board[i][j] == 0) {
                initial_empty = {i, j};
            } else {
                initial_counts[initial_board[i][j]]++;
            }
        }
    }
    
    current_board = initial_board;
    current_empty = initial_empty;

    mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());
    target_empty = {N - 1, N - 1};

    while (target_board.empty()) {
        auto now = chrono::high_resolution_clock::now();
        if (chrono::duration_cast<chrono::milliseconds>(now - start_time).count() > 1900) {
            break;
        }
        
        vector<tuple<int, int>> edges;
        for (int i = 0; i < N; ++i) {
            for (int j = 0; j < N; ++j) {
                 if (i + 1 < N) edges.emplace_back(i * N + j, (i + 1) * N + j);
                 if (j + 1 < N) edges.emplace_back(i * N + j, i * N + j + 1);
            }
        }
        shuffle(edges.begin(), edges.end(), rng);

        DSU dsu(N * N);
        vector<vector<int>> adj(N * N);
        int edge_count = 0;
        for (const auto& edge : edges) {
            int u, v;
            tie(u, v) = edge;
            if (make_pair(u/N, u%N) == target_empty || make_pair(v/N, v%N) == target_empty) continue;
            if (dsu.find(u) != dsu.find(v)) {
                dsu.unite(u, v);
                adj[u].push_back(v);
                adj[v].push_back(u);
                edge_count++;
            }
        }
        if (edge_count != N * N - 2) continue;

        vector<vector<int>> current_target_board(N, vector<int>(N, 0));
        map<int, int> target_counts;
        for (int i = 0; i < N; ++i) {
            for (int j = 0; j < N; ++j) {
                if (make_pair(i, j) == target_empty) continue;
                int u = i * N + j;
                int mask = 0;
                for (int v : adj[u]) {
                    int vr = v / N, vc = v % N;
                    if (vr == i - 1) mask |= 2; // Up
                    if (vr == i + 1) mask |= 8; // Down
                    if (vc == j - 1) mask |= 1; // Left
                    if (vc == j + 1) mask |= 4; // Right
                }
                current_target_board[i][j] = mask;
                target_counts[mask]++;
            }
        }

        if (initial_counts.size() != target_counts.size()) continue;
        bool match = true;
        for (auto const& [key, val] : initial_counts) {
            if (target_counts.find(key) == target_counts.end() || target_counts[key] != val) {
                match = false;
                break;
            }
        }

        if (match) {
            target_board = current_target_board;
        }
    }
    
    if (target_board.empty()) { // Fallback, shouldn't be needed with problem guarantee
         cout << "" << endl; return 0;
    }

    map<int, vector<pair<int, int>>> initial_pos_by_type, target_pos_by_type;
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            if (initial_board[i][j] != 0) initial_pos_by_type[initial_board[i][j]].push_back({i, j});
            if (target_board[i][j] != 0) target_pos_by_type[target_board[i][j]].push_back({i, j});
        }
    }
    
    map<pair<int, int>, pair<int, int>> dest_of;
    for (auto const& [type, t_locs_const] : target_pos_by_type) {
        vector<pair<int,int>> i_locs = initial_pos_by_type[type];
        vector<pair<int,int>> t_locs = t_locs_const;
        vector<bool> used(i_locs.size(), false);
        for(const auto& t_loc : t_locs){
            int best_idx = -1;
            int min_dist = 1e9;
            for(size_t i=0; i<i_locs.size(); ++i){
                if(!used[i]){
                    int dist = abs(t_loc.first - i_locs[i].first) + abs(t_loc.second - i_locs[i].second);
                    if(dist < min_dist){
                        min_dist = dist;
                        best_idx = i;
                    }
                }
            }
            dest_of[i_locs[best_idx]] = t_loc;
            used[best_idx] = true;
        }
    }
    
    for(int r=0; r<N; ++r) for(int c=0; c<N; ++c) pos_to_initial[{r,c}] = {r,c};
    pos_to_initial[initial_empty] = {-1,-1};

    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            if (make_pair(i, j) == target_empty) continue;
            
            pair<int, int> initial_of_tile_at_target_pos = pos_to_initial.at({i,j});
            if (initial_of_tile_at_target_pos != make_pair(-1,-1) && dest_of.at(initial_of_tile_at_target_pos) == make_pair(i,j)) continue;

            pair<int, int> target_initial_pos = {-1,-1};
            for(auto const& [init_p, dest_p] : dest_of){
                if(dest_p == make_pair(i,j)){
                    target_initial_pos = init_p;
                    break;
                }
            }
            
            pair<int, int> current_pos_of_target;
            for(auto const& [cur_p, init_p] : pos_to_initial){
                if(init_p == target_initial_pos){
                    current_pos_of_target = cur_p;
                    break;
                }
            }
            
            pair<int, int> tile_pos = current_pos_of_target;
            while(tile_pos != make_pair(i,j)) {
                 int dr = (i > tile_pos.first) - (i < tile_pos.first);
                 int dc = (j > tile_pos.second) - (j < tile_pos.second);
                 pair<int,int> next_tile_pos = tile_pos;
                 if (dr != 0) next_tile_pos.first += dr;
                 else if (dc != 0) next_tile_pos.second += dc;

                 move_empty_to_tracked(next_tile_pos, {tile_pos});
                 
                 char move_char;
                 int er=current_empty.first, ec=current_empty.second;
                 int tr=tile_pos.first, tc=tile_pos.second;
                 if(er == tr-1) move_char = 'D';
                 else if(er == tr+1) move_char = 'U';
                 else if(ec == tc-1) move_char = 'R';
                 else move_char = 'L';
                 apply_move_tracked(move_char);
                 tile_pos = next_tile_pos;
            }
        }
    }
        
    move_empty_to_tracked(target_empty, {});
    cout << ans_moves << endl;

    return 0;
}