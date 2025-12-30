#include <iostream>
#include <vector>
#include <string>
#include <numeric>
#include <algorithm>
#include <map>
#include <random>
#include <chrono>
#include <queue>
#include <tuple>

using namespace std;

constexpr int DR[] = {-1, 1, 0, 0};
constexpr int DC[] = {0, 0, -1, 1};
const string MOVE_CHARS = "UDLR";
const int OPPOSITE[] = {1, 0, 3, 2};

int N, T;

struct DSU {
    vector<int> parent;
    DSU(int n) {
        parent.resize(n);
        iota(parent.begin(), parent.end(), 0);
    }
    int find(int i) {
        if (parent[i] == i)
            return i;
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

int get_tile_type(const vector<pair<int, int>>& adj, int r, int c) {
    int type = 0;
    for (auto& edge : adj) {
        int r2 = edge.first;
        int c2 = edge.second;
        if (r2 == r + 1 && c2 == c) type |= 8; // Down
        if (r2 == r - 1 && c2 == c) type |= 2; // Up
        if (r2 == r && c2 == c + 1) type |= 4; // Right
        if (r2 == r && c2 == c - 1) type |= 1; // Left
    }
    return type;
}

int hex_to_int(char c) {
    if (c >= '0' && c <= '9') return c - '0';
    return c - 'a' + 10;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    auto start_time = chrono::high_resolution_clock::now();

    cin >> N >> T;
    vector<vector<int>> initial_board(N, vector<int>(N));
    map<int, int> initial_counts;
    int initial_er, initial_ec;

    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            char c;
            cin >> c;
            initial_board[i][j] = hex_to_int(c);
            if (initial_board[i][j] == 0) {
                initial_er = i;
                initial_ec = j;
            } else {
                initial_counts[initial_board[i][j]]++;
            }
        }
    }

    mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());
    vector<vector<int>> target_board(N, vector<int>(N));
    int target_er = N - 1, target_ec = N - 1;

    while (true) {
        auto current_time = chrono::high_resolution_clock::now();
        if (chrono::duration_cast<chrono::milliseconds>(current_time - start_time).count() > 300) {
            cout << "" << endl;
            return 0;
        }

        vector<tuple<int, int, int>> edges;
        for (int i = 0; i < N; ++i) {
            for (int j = 0; j < N; ++j) {
                if (i == target_er && j == target_ec) continue;
                if (i + 1 < N && !(i + 1 == target_er && j == target_ec)) {
                    edges.emplace_back(uniform_int_distribution<int>()(rng), i * N + j, (i + 1) * N + j);
                }
                if (j + 1 < N && !(i == target_er && j + 1 == target_ec)) {
                    edges.emplace_back(uniform_int_distribution<int>()(rng), i * N + j, i * N + j + 1);
                }
            }
        }
        shuffle(edges.begin(), edges.end(), rng);

        DSU dsu(N * N);
        vector<vector<pair<int, int>>> adj(N * N);
        int edge_count = 0;
        for (const auto& edge : edges) {
            int u, v;
            tie(ignore, u, v) = edge;
            if (dsu.find(u) != dsu.find(v)) {
                dsu.unite(u, v);
                adj[u].push_back({v / N, v % N});
                adj[v].push_back({u / N, u % N});
                edge_count++;
            }
        }
        
        if (edge_count != N * N - 2) continue;

        map<int, int> target_counts;
        bool possible = true;
        for (int i = 0; i < N; ++i) {
            for (int j = 0; j < N; ++j) {
                if (i == target_er && j == target_ec) {
                    target_board[i][j] = 0;
                    continue;
                }
                target_board[i][j] = get_tile_type(adj[i * N + j], i, j);
                if (target_board[i][j] == 0) {
                    possible = false;
                    break;
                }
                target_counts[target_board[i][j]]++;
            }
            if(!possible) break;
        }
        
        if (possible && initial_counts == target_counts) {
            break;
        }
    }
    
    map<int, vector<pair<int, int>>> initial_pos_map, target_pos_map;
    for(int i = 0; i < N; ++i) {
        for(int j = 0; j < N; ++j) {
            if(initial_board[i][j] != 0) initial_pos_map[initial_board[i][j]].push_back({i, j});
            if(target_board[i][j] != 0) target_pos_map[target_board[i][j]].push_back({i, j});
        }
    }

    vector<vector<pair<int, int>>> tile_dest(N, vector<pair<int, int>>(N));
    for(auto const& [type, t_pos] : target_pos_map) {
        vector<pair<int, int>> i_pos = initial_pos_map[type];
        vector<bool> used(i_pos.size(), false);
        for(const auto& p_target : t_pos) {
            int best_idx = -1;
            int min_dist = 1e9;
            for(size_t i = 0; i < i_pos.size(); ++i) {
                if(!used[i]) {
                    int dist = abs(p_target.first - i_pos[i].first) + abs(p_target.second - i_pos[i].second);
                    if(dist < min_dist) {
                        min_dist = dist;
                        best_idx = i;
                    }
                }
            }
            tile_dest[i_pos[best_idx].first][i_pos[best_idx].second] = p_target;
            used[best_idx] = true;
        }
    }
    
    vector<vector<pair<int, int>>> current_pos(N, vector<pair<int,int>>(N));
    for(int i=0; i<N; ++i) for(int j=0; j<N; ++j) current_pos[i][j] = {i, j};

    string final_ans = "";
    int er = initial_er, ec = initial_ec;
    vector<vector<bool>> placed(N, vector<bool>(N, false));

    auto move_empty = [&](int r, int c, int ar, int ac) {
        queue<pair<pair<int,int>, string>> q;
        q.push({{er, ec}, ""});
        map<pair<int,int>, bool> visited;
        visited[{er,ec}] = true;

        string path = "";
        while(!q.empty()){
            auto curr = q.front(); q.pop();
            if(curr.first.first == r && curr.first.second == c){
                path = curr.second;
                break;
            }
            for(int i=0; i<4; ++i){
                int ner = curr.first.first + DR[i];
                int nec = curr.first.second + DC[i];
                if(ner>=0 && ner<N && nec>=0 && nec<N && !visited[{ner,nec}] && !(ner==ar && nec==ac) && !placed[ner][nec]){
                    visited[{ner,nec}] = true;
                    q.push({{ner,nec}, curr.second + MOVE_CHARS[i]});
                }
            }
        }
        for(char m : path){
            final_ans += m;
            if(m == 'U'){ er--; } else if(m == 'D'){ er++; } else if(m == 'L'){ ec--; } else { ec++; }
        }
    };
    
    auto move_tile = [&](pair<int,int> from, pair<int,int> to){
        queue<pair<pair<int,int>, pair<int,int>>> q;
        q.push({from, {-1,-1}});
        map<pair<int,int>, pair<int,int>> parent;
        parent[from] = {-1,-1};
        
        bool found = false;
        while(!q.empty()){
            auto curr = q.front(); q.pop();
            if(curr.first == to) {
                found = true;
                break;
            }
            for(int i=0; i<4; ++i){
                int nr = curr.first.first + DR[i];
                int nc = curr.first.second + DC[i];
                if(nr>=0 && nr<N && nc>=0 && nc<N && parent.find({nr,nc}) == parent.end() && !placed[nr][nc]){
                    parent[{nr,nc}] = curr.first;
                    q.push({{nr,nc}, curr.first});
                }
            }
        }

        if(!found) return;

        vector<pair<int,int>> tile_path;
        pair<int,int> curr = to;
        while(curr.first != -1){
            tile_path.push_back(curr);
            curr = parent[curr];
        }
        reverse(tile_path.begin(), tile_path.end());

        pair<int,int> tile_pos = from;
        for(size_t i=1; i<tile_path.size(); ++i){
            pair<int,int> next_pos = tile_path[i];
            move_empty(next_pos.first, next_pos.second, tile_pos.first, tile_pos.second);
            
            int move_dir = -1;
            for(int j=0; j<4; ++j) {
                if (tile_pos.first + DR[j] == er && tile_pos.second + DC[j] == ec) {
                    move_dir = j; break;
                }
            }
            final_ans += MOVE_CHARS[OPPOSITE[move_dir]];
            swap(current_pos[er][ec], current_pos[tile_pos.first][tile_pos.second]);
            er = tile_pos.first; ec = tile_pos.second;
            tile_pos = next_pos;
        }
    };

    auto place_routine = [&](int r_end, int c_end, bool row_major) {
      if(row_major){
        for(int i=0; i<=r_end; ++i) {
            for(int j=0; j<N; ++j) {
                if(i==r_end && j>=c_end) continue;
                pair<int,int> target_tile_orig = {-1,-1};
                for(int ro=0; ro<N; ++ro) for(int co=0; co<N; ++co) if(initial_board[ro][co]!=0 && tile_dest[ro][co]==make_pair(i,j)) target_tile_orig = {ro,co};
                pair<int,int> tile_curr_pos = {-1,-1};
                for(int rc=0; rc<N; ++rc) for(int cc=0; cc<N; ++cc) if(current_pos[rc][cc]==target_tile_orig) tile_curr_pos = {rc,cc};
                if(tile_curr_pos != make_pair(i,j)) move_tile(tile_curr_pos, {i,j});
                placed[i][j] = true;
            }
        }
      } else { // col major
         for(int j=0; j<=c_end; ++j) {
            for(int i=0; i<N; ++i) {
                if(i>=r_end && j==c_end) continue;
                pair<int,int> target_tile_orig = {-1,-1};
                for(int ro=0; ro<N; ++ro) for(int co=0; co<N; ++co) if(initial_board[ro][co]!=0 && tile_dest[ro][co]==make_pair(i,j)) target_tile_orig = {ro,co};
                pair<int,int> tile_curr_pos = {-1,-1};
                for(int rc=0; rc<N; ++rc) for(int cc=0; cc<N; ++cc) if(current_pos[rc][cc]==target_tile_orig) tile_curr_pos = {rc,cc};
                if(tile_curr_pos != make_pair(i,j)) move_tile(tile_curr_pos, {i,j});
                placed[i][j] = true;
            }
        }
      }
    };

    if (N > 2) {
      place_routine(N - 3, N - 1, true);
      place_routine(N - 1, N - 3, false);
    }
    
    vector<pair<int, int>> unplaced_orig, unplaced_target;
    for(int i=N-2; i<N; ++i) for(int j=N-2; j<N; ++j){
        if (i == target_er && j == target_ec) continue;
        unplaced_target.push_back({i,j});
        pair<int,int> target_tile_orig = {-1,-1};
        for(int ro=0; ro<N; ++ro) for(int co=0; co<N; ++co) if(initial_board[ro][co]!=0 && tile_dest[ro][co]==make_pair(i,j)) target_tile_orig = {ro,co};
        unplaced_orig.push_back(target_tile_orig);
    }

    vector<int> board_1d;
    map<pair<int,int>, int> orig_to_val;
    for(size_t i=0; i<unplaced_orig.size(); ++i) orig_to_val[unplaced_orig[i]] = i+1;
    
    for(int r=N-2; r<N; ++r) for(int c=N-2; c<N; ++c){
        if(r==er && c==ec) board_1d.push_back(0);
        else board_1d.push_back(orig_to_val[current_pos[r][c]]);
    }

    queue<pair<vector<int>, string>> q_bfs;
    q_bfs.push({board_1d, ""});
    map<vector<int>, bool> visited_bfs;
    visited_bfs[board_1d] = true;
    string sub_path = "";

    while(!q_bfs.empty()){
        auto state = q_bfs.front(); q_bfs.pop();
        
        bool done = true;
        for(size_t i=0; i<unplaced_target.size(); ++i) {
            int r = unplaced_target[i].first, c = unplaced_target[i].second;
            int idx = (r-(N-2))*2 + (c-(N-2));
            if(state.first[idx] != i+1) done = false;
        }
        if(done){
            sub_path = state.second;
            break;
        }

        int sub_er, sub_ec;
        for(int i=0; i<4; ++i) if(state.first[i]==0){sub_er=i/2; sub_ec=i%2; break;}

        for(int i=0; i<4; ++i){
            int ner = sub_er + DR[i], nec = sub_ec + DC[i];
            if(ner>=0 && ner<2 && nec>=0 && nec<2){
                vector<int> next_board = state.first;
                swap(next_board[sub_er*2+sub_ec], next_board[ner*2+nec]);
                if(!visited_bfs[next_board]){
                    visited_bfs[next_board] = true;
                    q_bfs.push({next_board, state.second+MOVE_CHARS[i]});
                }
            }
        }
    }
    
    final_ans += sub_path;

    cout << final_ans << endl;

    return 0;
}