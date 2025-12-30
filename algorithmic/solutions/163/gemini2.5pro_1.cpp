#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <set>
#include <chrono>
#include <random>
#include <cmath>
#include <queue>

using namespace std;

const int N_fixed = 50;
const int M_fixed = 100;

int n, m;
vector<vector<int>> initial_grid;
vector<set<int>> adj;
bool is_adj[M_fixed + 1][M_fixed + 1];

struct Point {
    int r, c;
};

int manhattan_dist(Point p1, Point p2) {
    return abs(p1.r - p2.r) + abs(p1.c - p2.c);
}

int dist_to_boundary(Point p) {
    return min({p.r, p.c, n - 1 - p.r, n - 1 - p.c});
}

mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());

void read_input() {
    cin >> n >> m;
    initial_grid.assign(n, vector<int>(n));
    adj.assign(m + 1, set<int>());
    for (int i = 0; i < m + 1; ++i) {
        for (int j = 0; j < m + 1; ++j) {
            is_adj[i][j] = false;
        }
    }

    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < n; ++j) {
            cin >> initial_grid[i][j];
        }
    }

    int dr[] = {-1, 1, 0, 0};
    int dc[] = {0, 0, -1, 1};

    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < n; ++j) {
            int c1 = initial_grid[i][j];
            if (i == 0 || i == n - 1 || j == 0 || j == n - 1) {
                adj[c1].insert(0);
                adj[0].insert(c1);
            }
            for (int k = 0; k < 4; ++k) {
                int ni = i + dr[k];
                int nj = j + dc[k];
                if (ni >= 0 && ni < n && nj >= 0 && nj < n) {
                    int c2 = initial_grid[ni][nj];
                    if (c1 != c2) {
                        adj[c1].insert(c2);
                        adj[c2].insert(c1);
                    }
                }
            }
        }
    }

    for (int i = 0; i <= m; ++i) {
        for (int neighbor : adj[i]) {
            is_adj[i][neighbor] = true;
        }
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    auto start_time = chrono::steady_clock::now();

    read_input();

    vector<Point> positions;
    int grid_dim = 0;
    while(grid_dim * grid_dim < m) grid_dim++;
    
    int stride = n / grid_dim;
    int offset = (n - (grid_dim-1)*stride)/2;

    for (int i = 0; i < grid_dim; ++i) {
        for (int j = 0; j < grid_dim; ++j) {
            if (positions.size() < m) {
                positions.push_back({offset + i * stride, offset + j * stride});
            }
        }
    }
    
    vector<int> ward_at_pos(m);
    iota(ward_at_pos.begin(), ward_at_pos.end(), 1);
    shuffle(ward_at_pos.begin(), ward_at_pos.end(), rng);

    vector<int> pos_of_ward(m + 1);
    for(int i=0; i<m; ++i) pos_of_ward[ward_at_pos[i]] = i;
    
    vector<Point> ward_pos(m + 1);
    for (int i = 1; i <= m; ++i) {
        ward_pos[i] = positions[pos_of_ward[i]];
    }

    auto calculate_energy = [&](const vector<Point>& current_ward_pos) {
        long long current_energy = 0;
        for (int i = 1; i <= m; ++i) {
            for (int neighbor : adj[i]) {
                if (neighbor > i) {
                    current_energy += manhattan_dist(current_ward_pos[i], current_ward_pos[neighbor]);
                } else if (neighbor == 0) {
                    current_energy += dist_to_boundary(current_ward_pos[i]);
                }
            }
        }
        return current_energy;
    };

    long long current_energy = calculate_energy(ward_pos);
    
    double start_temp = 50.0;
    double end_temp = 0.1;
    double time_limit = 1.8;

    while (true) {
        auto now = chrono::steady_clock::now();
        double elapsed_seconds = chrono::duration_cast<chrono::duration<double>>(now - start_time).count();
        if (elapsed_seconds > time_limit) {
            break;
        }

        double temp = start_temp * pow(end_temp / start_temp, elapsed_seconds / time_limit);

        int pos_idx1 = uniform_int_distribution<int>(0, m - 1)(rng);
        int pos_idx2 = uniform_int_distribution<int>(0, m - 1)(rng);
        if (pos_idx1 == pos_idx2) continue;

        int c1 = ward_at_pos[pos_idx1];
        int c2 = ward_at_pos[pos_idx2];
        
        long long delta = 0;

        for (int neighbor : adj[c1]) {
            if (neighbor == 0) delta += dist_to_boundary(positions[pos_idx2]) - dist_to_boundary(positions[pos_idx1]);
            else if (neighbor != c2) delta += manhattan_dist(positions[pos_idx2], ward_pos[neighbor]) - manhattan_dist(positions[pos_idx1], ward_pos[neighbor]);
        }
        for (int neighbor : adj[c2]) {
            if (neighbor == 0) delta += dist_to_boundary(positions[pos_idx1]) - dist_to_boundary(positions[pos_idx2]);
            else if (neighbor != c1) delta += manhattan_dist(positions[pos_idx1], ward_pos[neighbor]) - manhattan_dist(positions[pos_idx2], ward_pos[neighbor]);
        }
        
        if (delta < 0 || uniform_real_distribution<double>(0.0, 1.0)(rng) < exp(-delta / temp)) {
            current_energy += delta;
            swap(ward_at_pos[pos_idx1], ward_at_pos[pos_idx2]);
            pos_of_ward[c1] = pos_idx2;
            pos_of_ward[c2] = pos_idx1;
            ward_pos[c1] = positions[pos_idx2];
            ward_pos[c2] = positions[pos_idx1];
        }
    }

    vector<vector<int>> out_grid(n, vector<int>(n, 0));
    vector<vector<bool>> is_core(n, vector<bool>(n, false));

    for (int i = 1; i <= m; ++i) {
        out_grid[ward_pos[i].r][ward_pos[i].c] = i;
        is_core[ward_pos[i].r][ward_pos[i].c] = true;
    }

    int dr[] = {-1, 1, 0, 0};
    int dc[] = {0, 0, -1, 1};

    for (int c1 = 1; c1 <= m; ++c1) {
        for (int c2 : adj[c1]) {
            if (c2 == 0 || c1 > c2) continue;

            Point start = ward_pos[c1];
            Point end = ward_pos[c2];

            queue<Point> q;
            q.push(start);
            vector<vector<Point>> parent(n, vector<Point>(n, {-1, -1}));
            vector<vector<bool>> visited(n, vector<bool>(n, false));
            visited[start.r][start.c] = true;

            bool found = false;
            while (!q.empty()) {
                Point u = q.front();
                q.pop();

                if (u.r == end.r && u.c == end.c) {
                    found = true;
                    break;
                }

                for (int i = 0; i < 4; ++i) {
                    int nr = u.r + dr[i];
                    int nc = u.c + dc[i];
                    if (nr >= 0 && nr < n && nc >= 0 && nc < n && !visited[nr][nc] && (!is_core[nr][nc] || (nr == end.r && nc == end.c))) {
                        visited[nr][nc] = true;
                        parent[nr][nc] = u;
                        q.push({nr, nc});
                    }
                }
            }

            if (found) {
                vector<Point> path;
                Point curr = end;
                while (curr.r != -1) {
                    path.push_back(curr);
                    curr = parent[curr.r][curr.c];
                }
                reverse(path.begin(), path.end());

                for (size_t i = 0; i < path.size() / 2; ++i) {
                    if (!is_core[path[i].r][path[i].c])
                        out_grid[path[i].r][path[i].c] = c1;
                }
                for (size_t i = path.size() / 2; i < path.size(); ++i) {
                    if (!is_core[path[i].r][path[i].c])
                        out_grid[path[i].r][path[i].c] = c2;
                }
            }
        }
    }
    
    vector<vector<int>> dist_from_boundary(n, vector<int>(n, -1));
    queue<Point> q_bound;
    for(int i = 0; i < n; ++i) {
        for (int j = 0; j < n; ++j) {
            if (i == 0 || i == n - 1 || j == 0 || j == n - 1) {
                if (!is_core[i][j]) {
                    q_bound.push({i,j});
                    dist_from_boundary[i][j] = 0;
                }
            }
        }
    }
    
    int head = 0;
    vector<Point> q_vec(n*n);
    while(!q_bound.empty()){
        q_vec[head++] = q_bound.front();
        q_bound.pop();
    }
    int q_ptr = 0;
    while(q_ptr < head){
        Point u = q_vec[q_ptr++];
        for(int i=0; i<4; ++i){
            int nr = u.r + dr[i];
            int nc = u.c + dc[i];
            if(nr >= 0 && nr < n && nc >= 0 && nc < n && dist_from_boundary[nr][nc] == -1 && !is_core[nr][nc]){
                dist_from_boundary[nr][nc] = dist_from_boundary[u.r][u.c] + 1;
                q_vec[head++] = {nr, nc};
            }
        }
    }

    for (int c : adj[0]) {
        if (c > 0) {
            Point curr = ward_pos[c];
            while (dist_from_boundary[curr.r][curr.c] != 0 && dist_from_boundary[curr.r][curr.c] != -1) {
                if (!is_core[curr.r][curr.c]) out_grid[curr.r][curr.c] = c;
                Point next_p = {-1,-1};
                int min_dist = dist_from_boundary[curr.r][curr.c];
                 for(int i=0; i<4; ++i){
                    int nr = curr.r + dr[i];
                    int nc = curr.c + dc[i];
                    if(nr >= 0 && nr < n && nc >= 0 && nc < n && dist_from_boundary[nr][nc] != -1 && dist_from_boundary[nr][nc] < min_dist){
                        min_dist = dist_from_boundary[nr][nc];
                        next_p = {nr, nc};
                    }
                }
                if(next_p.r == -1) break;
                curr = next_p;
            }
            if (!is_core[curr.r][curr.c]) out_grid[curr.r][curr.c] = c;
        }
    }
    
    vector<vector<bool>> visited_zero(n, vector<bool>(n, false));
    queue<Point> q_zero;

    for (int i = 0; i < n; ++i) {
        if (out_grid[i][0] == 0 && !visited_zero[i][0]) { q_zero.push({i, 0}); visited_zero[i][0] = true; }
        if (out_grid[i][n-1] == 0 && !visited_zero[i][n-1]) { q_zero.push({i, n-1}); visited_zero[i][n-1] = true; }
    }
    for (int j = 1; j < n-1; ++j) {
        if (out_grid[0][j] == 0 && !visited_zero[0][j]) { q_zero.push({0, j}); visited_zero[0][j] = true; }
        if (out_grid[n-1][j] == 0 && !visited_zero[n-1][j]) { q_zero.push({n-1, j}); visited_zero[n-1][j] = true; }
    }

    while(!q_zero.empty()){
        Point u = q_zero.front();
        q_zero.pop();
        for(int i=0; i<4; ++i){
            int nr = u.r + dr[i];
            int nc = u.c + dc[i];
            if(nr >= 0 && nr < n && nc >= 0 && nc < n && out_grid[nr][nc] == 0 && !visited_zero[nr][nc]){
                visited_zero[nr][nc] = true;
                q_zero.push({nr,nc});
            }
        }
    }

    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < n; ++j) {
            if (out_grid[i][j] == 0 && !visited_zero[i][j]) {
                vector<Point> component;
                vector<int> neighbor_colors;
                queue<Point> q_fill;
                
                q_fill.push({i, j});
                visited_zero[i][j] = true;
                
                while(!q_fill.empty()) {
                    Point u = q_fill.front(); q_fill.pop();
                    component.push_back(u);

                    for (int k = 0; k < 4; ++k) {
                        int nr = u.r + dr[k]; int nc = u.c + dc[k];
                        if (nr >= 0 && nr < n && nc >= 0 && nc < n) {
                            if (out_grid[nr][nc] == 0 && !visited_zero[nr][nc]) {
                                visited_zero[nr][nc] = true;
                                q_fill.push({nr, nc});
                            } else if (out_grid[nr][nc] != 0) {
                                neighbor_colors.push_back(out_grid[nr][nc]);
                            }
                        }
                    }
                }

                if (!neighbor_colors.empty()) {
                    sort(neighbor_colors.begin(), neighbor_colors.end());
                    int best_color = neighbor_colors[0], max_count = 0;
                    int current_count = 0; int current_color = -1;
                    for(int color : neighbor_colors) {
                        if (color != current_color) {
                            if (current_count > max_count) { max_count = current_count; best_color = current_color; }
                            current_color = color; current_count = 1;
                        } else current_count++;
                    }
                    if (current_count > max_count) best_color = current_color;
                    for (const auto& p_fill : component) out_grid[p_fill.r][p_fill.c] = best_color;
                }
            }
        }
    }
    
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < n; ++j) {
            cout << out_grid[i][j] << (j == n - 1 ? "" : " ");
        }
        cout << "\n";
    }

    return 0;
}