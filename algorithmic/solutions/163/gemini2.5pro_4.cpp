#include <iostream>
#include <vector>
#include <numeric>
#include <set>
#include <queue>
#include <algorithm>
#include <cmath>
#include <chrono>
#include <random>
#include <map>

using namespace std;

const int N = 50;
const int M = 100;

int n_fixed, m_fixed;
vector<vector<int>> initial_grid(N, vector<int>(N));
vector<vector<bool>> req_adj(M + 1, vector<bool>(M + 1, false));
vector<vector<int>> grid(N, vector<int>(N));
vector<vector<int>> best_grid;
int best_score = -1;

int dx[] = {0, 1, 0, -1};
int dy[] = {1, 0, -1, 0};

bool is_valid(int r, int c) {
    return r >= 0 && r < N && c >= 0 && c < N;
}

void read_input() {
    cin >> n_fixed >> m_fixed;
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            cin >> initial_grid[i][j];
        }
    }
}

void build_adj() {
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            if (i == 0 || i == N - 1 || j == 0 || j == N - 1) {
                if (initial_grid[i][j] != 0) {
                    req_adj[initial_grid[i][j]][0] = req_adj[0][initial_grid[i][j]] = true;
                }
            }
            for (int k = 0; k < 2; ++k) {
                int ni = i + dx[k];
                int nj = j + dy[k];
                if (is_valid(ni, nj) && initial_grid[i][j] != initial_grid[ni][nj]) {
                    int u = initial_grid[i][j];
                    int v = initial_grid[ni][nj];
                    if (u != 0 && v != 0) {
                        req_adj[u][v] = req_adj[v][u] = true;
                    }
                }
            }
        }
    }
}

struct State {
    int cost, r, c;
    bool operator>(const State& other) const {
        return cost > other.cost;
    }
};

bool is_path_cell_valid(int r, int c, int path_color, int other_color) {
    for (int i = 0; i < 4; ++i) {
        int nr = r + dx[i];
        int nc = c + dy[i];
        if (is_valid(nr, nc)) {
            int neighbor_color = grid[nr][nc];
            if (neighbor_color != 0 && neighbor_color != path_color && neighbor_color != other_color && !req_adj[path_color][neighbor_color]) {
                return false;
            }
        }
    }
    return true;
}

vector<pair<int, int>> dijkstra(int start_c, int end_c, int path_color, int other_color) {
    priority_queue<State, vector<State>, greater<State>> pq;
    vector<vector<int>> dist(N, vector<int>(N, -1));
    vector<vector<pair<int, int>>> parent(N, vector<pair<int, int>>(N, {-1, -1}));

    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            if (grid[i][j] == 0) {
                bool is_source = false;
                if (start_c != 0) {
                    for (int k = 0; k < 4; ++k) {
                        int ni = i + dx[k], nj = j + dy[k];
                        if (is_valid(ni, nj) && grid[ni][nj] == start_c) {
                            is_source = true;
                            break;
                        }
                    }
                } else {
                    if (i == 0 || i == N - 1 || j == 0 || j == N - 1) is_source = true;
                }
                if (is_source && is_path_cell_valid(i, j, path_color, other_color)) {
                    dist[i][j] = 1;
                    pq.push({1, i, j});
                }
            }
        }
    }

    while (!pq.empty()) {
        State current = pq.top();
        pq.pop();
        int r = current.r, c = current.c, cost = current.cost;

        if (dist[r][c] != -1 && cost > dist[r][c]) continue;

        bool is_target = false;
        if (end_c != 0) {
            for (int k = 0; k < 4; ++k) {
                int nr = r + dx[k], nc = c + dy[k];
                if (is_valid(nr, nc) && grid[nr][nc] == end_c) {
                    is_target = true;
                    break;
                }
            }
        } else {
            if (r == 0 || r == N - 1 || c == 0 || c == N - 1) is_target = true;
        }

        if (is_target) {
            vector<pair<int, int>> path;
            pair<int, int> curr = {r, c};
            while (curr.first != -1) {
                path.push_back(curr);
                curr = parent[curr.first][curr.second];
            }
            reverse(path.begin(), path.end());
            return path;
        }

        for (int k = 0; k < 4; ++k) {
            int nr = r + dx[k], nc = c + dy[k];
            if (is_valid(nr, nc) && grid[nr][nc] == 0 && (dist[nr][nc] == -1 || dist[nr][nc] > cost + 1)) {
                if (is_path_cell_valid(nr, nc, path_color, other_color)) {
                    dist[nr][nc] = cost + 1;
                    parent[nr][nc] = {r, c};
                    pq.push({dist[nr][nc], nr, nc});
                }
            }
        }
    }
    return {};
}

void solve(std::mt19937& rng) {
    grid.assign(N, vector<int>(N, 0));
    for (int i = 0; i < 10; ++i) {
        for (int j = 0; j < 10; ++j) {
            grid[i * 5 + 2][j * 5 + 2] = i * 10 + j + 1;
        }
    }

    vector<pair<int, int>> adj_pairs;
    for (int i = 0; i <= M; ++i) {
        for (int j = i + 1; j <= M; ++j) {
            if (req_adj[i][j]) {
                adj_pairs.push_back({i, j});
            }
        }
    }
    shuffle(adj_pairs.begin(), adj_pairs.end(), rng);
    
    sort(adj_pairs.begin(), adj_pairs.end(), [](const pair<int, int>& a, const pair<int, int>& b){
        bool a_is_0 = a.first == 0 || a.second == 0;
        bool b_is_0 = b.first == 0 || b.second == 0;
        if(a_is_0 && !b_is_0) return true;
        if(!a_is_0 && b_is_0) return false;
        return false;
    });

    for (const auto& p : adj_pairs) {
        int c1 = p.first, c2 = p.second;
        
        bool is_adj = false;
        if (c1 != 0 && c2 != 0) {
            for (int r = 0; r < N && !is_adj; ++r) for (int c = 0; c < N && !is_adj; ++c) if (grid[r][c] == c1)
                for (int k = 0; k < 4; ++k) { int nr = r + dx[k], nc = c + dy[k]; if (is_valid(nr, nc) && grid[nr][nc] == c2) { is_adj = true; break; } }
        } else {
            int non_zero_c = (c1 == 0) ? c2 : c1;
            for(int i=0; i<N && !is_adj; ++i) {
                if(grid[i][0] == non_zero_c || grid[i][N-1] == non_zero_c || grid[0][i] == non_zero_c || grid[N-1][i] == non_zero_c) is_adj = true;
            }
        }
        if (is_adj) continue;

        vector<pair<int, int>> path1 = dijkstra(c1, c2, c1, c2);
        vector<pair<int, int>> path2 = dijkstra(c2, c1, c2, c1);
        
        vector<pair<int, int>> path;
        int path_color;

        bool p1_empty = path1.empty(), p2_empty = path2.empty();

        if (p1_empty && p2_empty) continue;
        if (p1_empty) { path = path2; path_color = c2; }
        else if (p2_empty) { path = path1; path_color = c1; }
        else if (path1.size() <= path2.size()) { path = path1; path_color = c1; }
        else { path = path2; path_color = c2; }

        for (auto& cell : path) {
            grid[cell.first][cell.second] = path_color;
        }
    }

    vector<vector<int>> contacts(M + 1, vector<int>(M + 1, 0));
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            for (int k = 0; k < 2; ++k) {
                int ni = i + dx[k], nj = j + dy[k];
                if (is_valid(ni, nj)) {
                    int u = grid[i][j], v = grid[ni][nj];
                    if (u != v) { contacts[u][v]++; contacts[v][u]++; }
                }
            }
            if (grid[i][j] != 0 && (i==0 || i==N-1 || j==0 || j==N-1)) {
                contacts[grid[i][j]][0] += (i==0) + (i==N-1) + (j==0) + (j==N-1);
                contacts[0][grid[i][j]] += (i==0) + (i==N-1) + (j==0) + (j==N-1);
            }
        }
    }

    for (int iter = 0; iter < 5; ++iter) {
        vector<pair<int, int>> cells;
        for (int i = 0; i < N; ++i) for (int j = 0; j < N; ++j) if (grid[i][j] != 0) cells.push_back({i, j});
        shuffle(cells.begin(), cells.end(), rng);

        for (auto& p : cells) {
            int r = p.first, c = p.second;
            int color = grid[r][c];
            if (color == 0) continue;

            map<int, int> adj_counts;
            for (int k = 0; k < 4; ++k) {
                int nr = r + dx[k], nc = c + dy[k];
                adj_counts[is_valid(nr, nc) ? grid[nr][nc] : 0]++;
            }
            
            bool can_remove = true;
            for(auto const& [adj_c, count] : adj_counts) {
                if (adj_c != color && req_adj[color][adj_c] && contacts[color][adj_c] <= count) {
                    can_remove = false; break;
                }
            }
            if(!can_remove) continue;
            
            grid[r][c] = 0; // Tentatively remove
            
            int total_same_color_cells = 0;
            pair<int,int> start_node = {-1,-1};
            for(int i=0; i<N; ++i) for(int j=0; j<N; ++j) if(grid[i][j] == color) {
                total_same_color_cells++;
                if(start_node.first == -1) start_node = {i,j};
            }

            if(total_same_color_cells > 0) {
                queue<pair<int,int>> q;
                q.push(start_node);
                vector<vector<bool>> visited(N, vector<bool>(N, false));
                visited[start_node.first][start_node.second] = true;
                int count = 0;
                while(!q.empty()){
                    pair<int,int> curr = q.front(); q.pop();
                    count++;
                    for(int k=0; k<4; ++k){
                        int nr = curr.first + dx[k], nc = curr.second + dy[k];
                        if(is_valid(nr, nc) && grid[nr][nc] == color && !visited[nr][nc]){
                            visited[nr][nc] = true;
                            q.push({nr, nc});
                        }
                    }
                }
                if(count < total_same_color_cells) can_remove = false;
            }

            if (can_remove) {
                for(auto const& [adj_c, count] : adj_counts) if (adj_c != color) {
                    contacts[color][adj_c] -= count;
                    contacts[adj_c][color] -= count;
                }
            } else {
                grid[r][c] = color; // Revert
            }
        }
    }
    
    int score = 0;
    for(int i=0; i<N; ++i) for(int j=0; j<N; ++j) if(grid[i][j] == 0) score++;
    
    if (score > best_score) {
        best_score = score;
        best_grid = grid;
    }
}

void print_output() {
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            cout << best_grid[i][j] << (j == N - 1 ? "" : " ");
        }
        cout << endl;
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    auto start_time = std::chrono::high_resolution_clock::now();
    
    std::random_device rd;
    std::mt19937 rng(rd()); 

    read_input();
    build_adj();
    
    solve(rng); // Initial run to get a baseline

    while(true){
        auto current_time = std::chrono::high_resolution_clock::now();
        auto elapsed = std::chrono::duration_cast<std::chrono::milliseconds>(current_time - start_time);
        if(elapsed.count() > 2800) break;
        solve(rng);
    }
    
    print_output();

    return 0;
}