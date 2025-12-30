#include <iostream>
#include <vector>
#include <string>
#include <queue>
#include <map>
#include <set>
#include <algorithm>
#include <cmath>
#include <functional>

using namespace std;

const long long INF = 1e18;

int N, si, sj;
vector<string> C;

struct Point {
    int r, c;

    bool operator==(const Point& other) const {
        return r == other.r && c == other.c;
    }

    bool operator!=(const Point& other) const {
        return !(*this == other);
    }

    bool operator<(const Point& other) const {
        if (r != other.r) return r < other.r;
        return c < other.c;
    }
};

int dr[] = {-1, 1, 0, 0};
int dc[] = {0, 0, -1, 1};
char move_char[] = {'U', 'D', 'L', 'R'};

bool is_valid(int r, int c) {
    return r >= 0 && r < N && c >= 0 && c < N && C[r][c] != '#';
}

void dijkstra(const Point& start, vector<vector<long long>>& dist_grid, vector<vector<Point>>& parent_grid) {
    dist_grid.assign(N, vector<long long>(N, INF));
    parent_grid.assign(N, vector<Point>(N, {-1, -1}));

    dist_grid[start.r][start.c] = 0;
    priority_queue<pair<long long, Point>, vector<pair<long long, Point>>, greater<pair<long long, Point>>> pq;
    pq.push({0, start});

    while (!pq.empty()) {
        auto [d, p] = pq.top();
        pq.pop();

        if (d > dist_grid[p.r][p.c]) {
            continue;
        }

        for (int i = 0; i < 4; ++i) {
            int nr = p.r + dr[i];
            int nc = p.c + dc[i];
            if (is_valid(nr, nc)) {
                long long new_dist = d + (C[nr][nc] - '0');
                if (new_dist < dist_grid[nr][nc]) {
                    dist_grid[nr][nc] = new_dist;
                    parent_grid[nr][nc] = p;
                    pq.push({new_dist, {nr, nc}});
                }
            }
        }
    }
}

string reconstruct_path(const Point& start, const Point& end, const vector<vector<Point>>& parent_grid) {
    if (start == end) return "";
    string path = "";
    Point curr = end;
    while (curr != start) {
        Point parent = parent_grid[curr.r][curr.c];
        for (int i = 0; i < 4; ++i) {
            if (parent.r + dr[i] == curr.r && parent.c + dc[i] == curr.c) {
                path += move_char[i];
                break;
            }
        }
        curr = parent;
    }
    reverse(path.begin(), path.end());
    return path;
}


int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    cin >> N >> si >> sj;
    C.resize(N);
    for (int i = 0; i < N; ++i) {
        cin >> C[i];
    }

    set<Point> key_points_set;
    key_points_set.insert({si, sj});

    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            if (C[i][j] != '#') {
                bool has_horizontal = false;
                if ((j > 0 && C[i][j - 1] != '#') || (j < N - 1 && C[i][j + 1] != '#')) {
                    has_horizontal = true;
                }
                bool has_vertical = false;
                if ((i > 0 && C[i - 1][j] != '#') || (i < N - 1 && C[i + 1][j] != '#')) {
                    has_vertical = true;
                }
                if (has_horizontal && has_vertical) {
                    key_points_set.insert({i, j});
                }
            }
        }
    }
    
    if (key_points_set.size() <= 1) {
        for(int i=0; i<4; ++i) {
            if(is_valid(si+dr[i], sj+dc[i])) {
                cout << move_char[i] << move_char[i^1] << endl;
                return 0;
            }
        }
        cout << "" << endl;
        return 0;
    }

    vector<Point> key_points(key_points_set.begin(), key_points_set.end());
    map<Point, int> point_to_idx;
    for (int i = 0; i < key_points.size(); ++i) {
        point_to_idx[key_points[i]] = i;
    }

    int K = key_points.size();
    vector<vector<long long>> adj_matrix(K, vector<long long>(K));
    vector<vector<vector<Point>>> parent_grids(K);

    for (int i = 0; i < K; ++i) {
        vector<vector<long long>> dist_grid;
        dijkstra(key_points[i], dist_grid, parent_grids[i]);
        for (int j = 0; j < K; ++j) {
            adj_matrix[i][j] = dist_grid[key_points[j].r][key_points[j].c];
        }
    }

    vector<vector<pair<int, int>>> mst(K);
    vector<long long> min_cost(K, INF);
    vector<int> parent_in_mst(K, -1);
    vector<bool> in_mst(K, false);
    
    int start_idx = point_to_idx.at({si, sj});
    min_cost[start_idx] = 0;
    priority_queue<pair<long long, int>, vector<pair<long long, int>>, greater<pair<long long, int>>> pq_mst;
    pq_mst.push({0, start_idx});

    while (!pq_mst.empty()) {
        auto [cost, u] = pq_mst.top();
        pq_mst.pop();

        if (in_mst[u]) continue;
        in_mst[u] = true;

        if (parent_in_mst[u] != -1) {
            int v = parent_in_mst[u];
            mst[u].push_back({v, (int)adj_matrix[u][v]});
            mst[v].push_back({u, (int)adj_matrix[v][u]});
        }

        for (int v = 0; v < K; ++v) {
            if (!in_mst[v] && adj_matrix[u][v] < min_cost[v]) {
                min_cost[v] = adj_matrix[u][v];
                parent_in_mst[v] = u;
                pq_mst.push({min_cost[v], v});
            }
        }
    }
    for(int i = 0; i < K; ++i) {
        sort(mst[i].begin(), mst[i].end());
    }

    vector<int> tour_indices;
    vector<bool> visited(K, false);
    function<void(int)> generate_tour_dfs = 
        [&](int u) {
        visited[u] = true;
        tour_indices.push_back(u);
        for(auto& edge : mst[u]) {
            int v = edge.first;
            if (!visited[v]) {
                generate_tour_dfs(v);
            }
        }
    };
    generate_tour_dfs(start_idx);
    
    bool improved = true;
    for(int iter=0; iter<100 && improved; ++iter){ // Iterated 2-opt
        improved = false;
        for (int i = 0; i < K; i++) {
            for (int j = i + 2; j < K; j++) {
                int i_next = i + 1;
                int j_next = (j + 1) % K;

                long long current_dist = adj_matrix[tour_indices[i]][tour_indices[i_next]] + adj_matrix[tour_indices[j]][tour_indices[j_next]];
                long long new_dist = adj_matrix[tour_indices[i]][tour_indices[j]] + adj_matrix[tour_indices[i_next]][tour_indices[j_next]];

                if (new_dist < current_dist) {
                    reverse(tour_indices.begin() + i_next, tour_indices.begin() + j + 1);
                    improved = true;
                }
            }
        }
    }

    string final_path = "";
    for (size_t i = 0; i < tour_indices.size(); ++i) {
        int u_idx = tour_indices[i];
        int v_idx = tour_indices[(i + 1) % tour_indices.size()];
        final_path += reconstruct_path(key_points[u_idx], key_points[v_idx], parent_grids[u_idx]);
    }
    
    cout << final_path << endl;

    return 0;
}