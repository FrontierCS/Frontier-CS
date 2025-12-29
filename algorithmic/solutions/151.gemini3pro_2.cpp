#include <iostream>
#include <vector>
#include <string>
#include <queue>
#include <tuple>
#include <algorithm>
#include <cmath>
#include <cstring>
#include <iomanip>

using namespace std;

// Constants
const int INF = 1e9;
const int MAXN = 75;
const int MAX_NODES = 5000;

// Directions: U, D, L, R
const int DR[] = {-1, 1, 0, 0};
const int DC[] = {0, 0, -1, 1};

struct Point {
    int r, c;
    bool operator==(const Point& other) const { return r == other.r && c == other.c; }
    bool operator!=(const Point& other) const { return !(*this == other); }
};

struct Edge {
    int to;
    int weight;
};

// Global Data
int N;
int si, sj;
string grid_str[MAXN];
int grid_id[MAXN][MAXN]; // Maps (r, c) to 0..num_road_cells-1
vector<Point> id_to_point;
int road_weights[MAXN][MAXN];
vector<Edge> adj[MAX_NODES];
vector<int> visible_from[MAX_NODES]; // List of cell IDs visible from cell i
int see_count[MAX_NODES]; // How many cells can see cell i
double rarity[MAX_NODES];
bool covered[MAX_NODES];
int num_road_cells = 0;
int total_covered = 0;

// Dijkstra Data
int dist_mat[MAX_NODES];
int parent[MAX_NODES];

// Function to check if a cell is valid road
bool is_road(int r, int c) {
    if (r < 0 || r >= N || c < 0 || c >= N) return false;
    return grid_str[r][c] != '#';
}

void parse_input() {
    if (!(cin >> N >> si >> sj)) return;
    for (int i = 0; i < N; ++i) {
        cin >> grid_str[i];
    }
}

void build_graph() {
    memset(grid_id, -1, sizeof(grid_id));
    for (int r = 0; r < N; ++r) {
        for (int c = 0; c < N; ++c) {
            if (grid_str[r][c] != '#') {
                grid_id[r][c] = num_road_cells;
                id_to_point.push_back({r, c});
                road_weights[r][c] = grid_str[r][c] - '0';
                num_road_cells++;
            }
        }
    }

    for (int i = 0; i < num_road_cells; ++i) {
        Point p = id_to_point[i];
        for (int d = 0; d < 4; ++d) {
            int nr = p.r + DR[d];
            int nc = p.c + DC[d];
            if (is_road(nr, nc)) {
                int neighbor_id = grid_id[nr][nc];
                adj[i].push_back({neighbor_id, road_weights[nr][nc]});
            }
        }
    }
}

void precompute_visibility() {
    for (int i = 0; i < num_road_cells; ++i) {
        Point p = id_to_point[i];
        
        // Horizontal
        // Left
        for (int c = p.c; c >= 0; --c) {
            if (!is_road(p.r, c)) break;
            visible_from[i].push_back(grid_id[p.r][c]);
        }
        // Right
        for (int c = p.c + 1; c < N; ++c) {
            if (!is_road(p.r, c)) break;
            visible_from[i].push_back(grid_id[p.r][c]);
        }
        
        // Vertical
        // Up
        for (int r = p.r - 1; r >= 0; --r) {
            if (!is_road(r, p.c)) break;
            visible_from[i].push_back(grid_id[r][p.c]);
        }
        // Down
        for (int r = p.r + 1; r < N; ++r) {
            if (!is_road(r, p.c)) break;
            visible_from[i].push_back(grid_id[r][p.c]);
        }
        
        // Sort and unique to remove duplicates
        sort(visible_from[i].begin(), visible_from[i].end());
        visible_from[i].erase(unique(visible_from[i].begin(), visible_from[i].end()), visible_from[i].end());
    }

    memset(see_count, 0, sizeof(see_count));
    for (int i = 0; i < num_road_cells; ++i) {
        for (int v : visible_from[i]) {
            see_count[v]++;
        }
    }

    for (int i = 0; i < num_road_cells; ++i) {
        // Rarity is inverse of how easily a cell is seen. 
        // Cells seen by fewer positions are more critical.
        if (see_count[i] > 0)
            rarity[i] = 1000.0 / (double)see_count[i];
        else 
            rarity[i] = 1000.0; // Should not happen in connected component
    }
}

void run_dijkstra(int start_node) {
    for (int i = 0; i < num_road_cells; ++i) {
        dist_mat[i] = INF;
        parent[i] = -1;
    }
    dist_mat[start_node] = 0;
    
    // Min-priority queue
    priority_queue<pair<int, int>, vector<pair<int, int>>, greater<pair<int, int>>> pq;
    pq.push({0, start_node});
    
    while (!pq.empty()) {
        int d = pq.top().first;
        int u = pq.top().second;
        pq.pop();
        
        if (d > dist_mat[u]) continue;
        
        for (auto& edge : adj[u]) {
            int v = edge.to;
            int w = edge.weight;
            if (dist_mat[u] + w < dist_mat[v]) {
                dist_mat[v] = dist_mat[u] + w;
                parent[v] = u;
                pq.push({dist_mat[v], v});
            }
        }
    }
}

void update_coverage(int u) {
    for (int v : visible_from[u]) {
        if (!covered[v]) {
            covered[v] = true;
            total_covered++;
        }
    }
}

string get_move_char(int from_id, int to_id) {
    Point p1 = id_to_point[from_id];
    Point p2 = id_to_point[to_id];
    if (p2.r == p1.r - 1) return "U";
    if (p2.r == p1.r + 1) return "D";
    if (p2.c == p1.c - 1) return "L";
    if (p2.c == p1.c + 1) return "R";
    return "";
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    parse_input();
    if (N == 0) return 0; // Handle potential empty input

    build_graph();
    precompute_visibility();
    
    int current_node = grid_id[si][sj];
    memset(covered, 0, sizeof(covered));
    update_coverage(current_node);
    
    string route = "";
    
    while (total_covered < num_road_cells) {
        run_dijkstra(current_node);
        
        int best_target = -1;
        double max_score = -1.0;
        
        // Evaluate candidates
        for (int t = 0; t < num_road_cells; ++t) {
            if (dist_mat[t] == INF) continue; 
            
            double gain = 0;
            // Calculate potential gain from t
            for (int v : visible_from[t]) {
                if (!covered[v]) {
                    gain += rarity[v];
                }
            }
            
            if (gain <= 1e-9) continue;
            
            double cost = dist_mat[t];
            // Heuristic: Score = Gain^2 / (Cost + C)
            // Prioritize high gain significantly, penalize distance moderately.
            double score = (gain * gain) / (cost + 10.0);
            
            if (score > max_score) {
                max_score = score;
                best_target = t;
            }
        }
        
        if (best_target == -1) break; // Should be done
        
        // Reconstruct path to best_target
        vector<int> path;
        int curr = best_target;
        while (curr != current_node) {
            path.push_back(curr);
            curr = parent[curr];
        }
        reverse(path.begin(), path.end());
        
        // Move along path
        for (int next_node : path) {
            route += get_move_char(current_node, next_node);
            current_node = next_node;
            update_coverage(current_node);
            
            // Optimization: If the best_target no longer offers gain due to views along the path, stop early.
            bool still_useful = false;
            for (int v : visible_from[best_target]) {
                if (!covered[v]) {
                    still_useful = true;
                    break;
                }
            }
            if (!still_useful) break; 
        }
    }
    
    // Return to start
    int start_node = grid_id[si][sj];
    if (current_node != start_node) {
        run_dijkstra(current_node);
        int curr = start_node;
        vector<int> path;
        while (curr != current_node) {
            path.push_back(curr);
            curr = parent[curr];
        }
        reverse(path.begin(), path.end());
        for (int next_node : path) {
            route += get_move_char(current_node, next_node);
            current_node = next_node;
        }
    }
    
    cout << route << endl;
    
    return 0;
}