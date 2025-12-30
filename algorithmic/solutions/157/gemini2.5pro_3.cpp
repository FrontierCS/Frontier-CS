#include <iostream>
#include <vector>
#include <string>
#include <chrono>
#include <numeric>
#include <algorithm>
#include <map>
#include <random>
#include <tuple>

using namespace std;

auto start_time = chrono::steady_clock::now();
double time_limit = 1.95;

bool is_time_up() {
    auto now = chrono::steady_clock::now();
    double elapsed = chrono::duration_cast<chrono::duration<double>>(now - start_time).count();
    return elapsed > time_limit;
}

mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());

const int MAX_N = 10;
int N;
long long T_param;
int DR[] = {-1, 1, 0, 0};
int DC[] = {0, 0, -1, 1};
char MOVE_CHARS[] = {'U', 'D', 'L', 'R'};
map<char, char> REV_MOVE = {{'U', 'D'}, {'D', 'U'}, {'L', 'R'}, {'R', 'L'}};

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

const int INF = 1e9;
struct Edge {
    int to, capacity, cost, rev;
};
vector<vector<Edge>> adj;
vector<int> dist;
vector<int> parent_v, parent_e;

void add_edge(int u, int v, int cap, int cost) {
    adj[u].push_back({v, cap, cost, (int)adj[v].size()});
    adj[v].push_back({u, 0, -cost, (int)adj[u].size() - 1});
}

int min_cost_flow(int s, int t, int f) {
    int res = 0;
    while (f > 0) {
        dist.assign(adj.size(), INF);
        dist[s] = 0;
        vector<int> q;
        q.push_back(s);
        vector<bool> in_queue(adj.size(), false);
        in_queue[s] = true;
        parent_v.assign(adj.size(), -1);
        parent_e.assign(adj.size(), -1);
        int head = 0;
        while(head < q.size()){
            int u = q[head++];
            in_queue[u] = false;
            for(size_t i = 0; i < adj[u].size(); ++i){
                Edge &e = adj[u][i];
                if(e.capacity > 0 && dist[e.to] > dist[u] + e.cost){
                    dist[e.to] = dist[u] + e.cost;
                    parent_v[e.to] = u;
                    parent_e[e.to] = i;
                    if(!in_queue[e.to]){
                        q.push_back(e.to);
                        in_queue[e.to] = true;
                    }
                }
            }
        }
        if (dist[t] == INF) return -1;
        int d = f;
        for (int v = t; v != s; v = parent_v[v]) {
            d = min(d, adj[parent_v[v]][parent_e[v]].capacity);
        }
        f -= d;
        res += d * dist[t];
        for (int v = t; v != s; v = parent_v[v]) {
            Edge &e = adj[parent_v[v]][parent_e[v]];
            e.capacity -= d;
            adj[v][e.rev].capacity += d;
        }
    }
    return res;
}

int hex_to_int(char c) {
    if (c >= '0' && c <= '9') return c - '0';
    return c - 'a' + 10;
}

int manhattan_dist(int r1, int c1, int r2, int c2) {
    return abs(r1 - r2) + abs(c1 - c2);
}

map<pair<int, int>, pair<int, int>> final_target_map;

int calculate_h(const vector<vector<pair<int, int>>>& board) {
    int total_dist = 0;
    for (int r = 0; r < N; ++r) {
        for (int c = 0; c < N; ++c) {
            if (board[r][c].first == -1) continue;
            auto it = final_target_map.find(board[r][c]);
            if (it != final_target_map.end()) {
                 total_dist += manhattan_dist(r, c, it->second.first, it->second.second);
            }
        }
    }
    return total_dist;
}

string ida_star_solution;
int node_limit;

int ida_star_dfs(vector<vector<pair<int, int>>>& board, int er, int ec, int g, int f_limit, char last_move, string& path) {
    int h = calculate_h(board);
    int f = g + h;
    if (f > f_limit) return f;
    if (h == 0) {
        ida_star_solution = path;
        return 0;
    }
    if (is_time_up() || node_limit-- <= 0) return -2;

    int min_f = INF;
    for (int i = 0; i < 4; ++i) {
        if (last_move != ' ' && MOVE_CHARS[i] == REV_MOVE.at(last_move)) continue;

        int ner = er + DR[i];
        int nec = ec + DC[i];

        if (ner < 0 || ner >= N || nec < 0 || nec >= N) continue;

        swap(board[er][ec], board[ner][nec]);
        path += MOVE_CHARS[i];

        int res = ida_star_dfs(board, ner, nec, g + 1, f_limit, MOVE_CHARS[i], path);
        
        path.pop_back();
        swap(board[er][ec], board[ner][nec]);

        if (res == 0) return 0;
        if (res == -2) return -2;
        min_f = min(min_f, res);
    }
    return min_f;
}

string solve_ida_star(const vector<vector<int>>& initial_board, int initial_er, int initial_ec) {
    vector<vector<pair<int, int>>> initial_board_id(N, vector<pair<int, int>>(N));
    for (int r = 0; r < N; ++r) {
        for (int c = 0; c < N; ++c) {
            initial_board_id[r][c] = (initial_board[r][c] == 0) ? make_pair(-1, -1) : make_pair(r, c);
        }
    }
    
    int h0 = calculate_h(initial_board_id);
    int f_limit = h0;
    string path = "";

    while (!is_time_up()) {
        node_limit = 200000 / (N/5);
        int res = ida_star_dfs(initial_board_id, initial_er, initial_ec, 0, f_limit, ' ', path);
        if (res == 0) return ida_star_solution;
        if (res == -2 || res == INF) break;
        f_limit = res;
    }
    return "";
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    cin >> N >> T_param;
    vector<vector<int>> initial_board(N, vector<int>(N));
    vector<int> initial_tile_counts(16, 0);
    vector<vector<pair<int, int>>> initial_pos_by_type(16);
    int initial_er = -1, initial_ec = -1;

    for (int i = 0; i < N; ++i) {
        string row; cin >> row;
        for (int j = 0; j < N; ++j) {
            initial_board[i][j] = hex_to_int(row[j]);
            if (initial_board[i][j] == 0) {
                initial_er = i; initial_ec = j;
            } else {
                initial_pos_by_type[initial_board[i][j]].push_back({i, j});
                initial_tile_counts[initial_board[i][j]]++;
            }
        }
    }

    int best_h = INF;
    vector<vector<int>> best_target_board;

    vector<pair<int, int>> vertices;
    map<pair<int, int>, int> p_to_idx;
    for (int r = 0; r < N; ++r) for (int c = 0; c < N; ++c) {
        if (r == initial_er && c == initial_ec) continue;
        p_to_idx[{r, c}] = vertices.size();
        vertices.push_back({r, c});
    }
    
    vector<tuple<int, int, int>> edges;
    for (size_t i = 0; i < vertices.size(); ++i) {
        auto [r, c] = vertices[i];
        if (r + 1 < N && !(r + 1 == initial_er && c == initial_ec)) {
            edges.emplace_back(i, p_to_idx.at({r + 1, c}), 0);
        }
        if (c + 1 < N && !(r == initial_er && c + 1 == initial_ec)) {
            edges.emplace_back(i, p_to_idx.at({r, c + 1}), 1);
        }
    }
    
    int V = N * N - 1;
    
    while (!is_time_up()) {
        shuffle(edges.begin(), edges.end(), rng);

        DSU dsu(V);
        vector<vector<int>> target_board(N, vector<int>(N, 0));
        int edge_count = 0;
        
        for (const auto& edge : edges) {
            if (dsu.find(get<0>(edge)) != dsu.find(get<1>(edge))) {
                dsu.unite(get<0>(edge), get<1>(edge));
                auto [u_r, u_c] = vertices[get<0>(edge)];
                auto [v_r, v_c] = vertices[get<1>(edge)];
                if (get<2>(edge) == 0) { // vertical
                    target_board[u_r][u_c] |= 8;
                    target_board[v_r][v_c] |= 2;
                } else { // horizontal
                    target_board[u_r][u_c] |= 4;
                    target_board[v_r][v_c] |= 1;
                }
                if (++edge_count == V - 1) break;
            }
        }

        vector<int> target_tile_counts(16, 0);
        for (int r = 0; r < N; ++r) for (int c = 0; c < N; ++c) {
            if (r == initial_er && c == initial_ec) continue;
            target_tile_counts[target_board[r][c]]++;
        }
        if (initial_tile_counts != target_tile_counts) continue;

        vector<vector<pair<int, int>>> target_pos_by_type(16);
        for (int r = 0; r < N; ++r) for (int c = 0; c < N; ++c) {
            if (r == initial_er && c == initial_ec) continue;
            target_pos_by_type[target_board[r][c]].push_back({r,c});
        }
        
        int current_h = 0;
        for (int type = 1; type < 16; ++type) {
            if (initial_pos_by_type[type].empty()) continue;
            int k = initial_pos_by_type[type].size();
            int s = 0, t = 2 * k + 1;
            adj.assign(t + 1, vector<Edge>());
            for(int i=0; i<k; ++i){
                add_edge(s, i+1, 1, 0);
                add_edge(i+1+k, t, 1, 0);
                for(int j=0; j<k; ++j){
                     add_edge(i+1, j+1+k, 1, manhattan_dist(
                        initial_pos_by_type[type][i].first, initial_pos_by_type[type][i].second,
                        target_pos_by_type[type][j].first, target_pos_by_type[type][j].second
                    ));
                }
            }
            current_h += min_cost_flow(s, t, k);
        }

        if (current_h < best_h) {
            best_h = current_h;
            best_target_board = target_board;
        }
    }
    
    if (best_h == INF) {
        cout << "" << endl;
        return 0;
    }
    
    vector<vector<pair<int, int>>> target_pos_by_type(16);
    for(int r=0; r<N; ++r) for(int c=0; c<N; ++c) {
        if(r == initial_er && c == initial_ec) continue;
        target_pos_by_type[best_target_board[r][c]].push_back({r,c});
    }
    
    for (int type = 1; type < 16; ++type) {
        if (initial_pos_by_type[type].empty()) continue;
        int k = initial_pos_by_type[type].size();
        int s = 0, t = 2 * k + 1;
        adj.assign(t + 1, vector<Edge>());
        for(int i=0; i<k; ++i){
            add_edge(s, i+1, 1, 0);
            add_edge(i+1+k, t, 1, 0);
            for(int j=0; j<k; ++j){
                 add_edge(i+1, j+1+k, 1, manhattan_dist(
                    initial_pos_by_type[type][i].first, initial_pos_by_type[type][i].second,
                    target_pos_by_type[type][j].first, target_pos_by_type[type][j].second
                ));
            }
        }
        min_cost_flow(s, t, k);
        for(int i=0; i<k; ++i){
            for(const auto& edge : adj[i+1]){
                if(edge.capacity == 0){
                    final_target_map[initial_pos_by_type[type][i]] = target_pos_by_type[type][edge.to - (k+1)];
                    break;
                }
            }
        }
    }

    string solution = solve_ida_star(initial_board, initial_er, initial_ec);

    if (solution.empty()) {
        string greedy_path = "";
        auto current_board = initial_board;
        int er = initial_er, ec = initial_ec;
        map<pair<int,int>, pair<int,int>> current_pos_map;
        for(auto const& [key, val] : final_target_map) current_pos_map[key] = key;
        
        for (long long k = 0; k < T_param; ++k) {
            int current_h = 0;
            for(auto const& [key, val] : current_pos_map) {
                current_h += manhattan_dist(val.first, val.second, final_target_map[key].first, final_target_map[key].second);
            }
            if (current_h == 0) break;
            
            int best_move = -1;
            int min_h_change = INF;

            for (int i = 0; i < 4; ++i) {
                if (!greedy_path.empty() && MOVE_CHARS[i] == REV_MOVE.at(greedy_path.back())) continue;
                int ner = er + DR[i], nec = ec + DC[i];
                if (ner < 0 || ner >= N || nec < 0 || nec >= N) continue;
                
                pair<int,int> moved_tile_id;
                for(auto const& [key, val] : current_pos_map) if (val.first == ner && val.second == nec) { moved_tile_id = key; break; }
                
                int h_before = manhattan_dist(ner, nec, final_target_map[moved_tile_id].first, final_target_map[moved_tile_id].second);
                int h_after = manhattan_dist(er, ec, final_target_map[moved_tile_id].first, final_target_map[moved_tile_id].second);

                if (h_after - h_before < min_h_change) {
                    min_h_change = h_after - h_before;
                    best_move = i;
                }
            }
            
            if (best_move != -1) {
                greedy_path += MOVE_CHARS[best_move];
                int ner = er + DR[best_move], nec = ec + DC[best_move];
                pair<int,int> moved_tile_id;
                for(auto const& [key, val] : current_pos_map) if (val.first == ner && val.second == nec) { moved_tile_id = key; break; }
                current_pos_map[moved_tile_id] = {er, ec};
                er = ner; ec = nec;
            }
        }
        solution = greedy_path;
    }
    cout << solution << endl;
    return 0;
}