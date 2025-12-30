#include <iostream>
#include <vector>
#include <string>
#include <queue>
#include <tuple>
#include <cmath>
#include <algorithm>
#include <map>

using namespace std;

const int INF = 1e9;
int N;
int si, sj;
vector<string> grid_map;
int costs[70][70];
bool is_road[70][70];

struct Point {
    int r, c;
    bool operator==(const Point& other) const { return r == other.r && c == other.c; }
};

struct Node {
    int id;
    Point p;
    vector<Point> visible_cells;
};

vector<Node> nodes;
int node_idx[70][70];
vector<pair<int, int>> adj[5000]; // to_id, cost
vector<string> adj_path[5000]; // path string

bool cell_covered[70][70];
int total_road_cells = 0;
int covered_count = 0;

// Optimization: Inverse mapping
vector<int> nodes_seeing[70][70];
int current_gain[5000];

int dr[] = {-1, 1, 0, 0};
int dc[] = {0, 0, -1, 1};
char dchar[] = {'U', 'D', 'L', 'R'};

bool is_valid(int r, int c) {
    return r >= 0 && r < N && c >= 0 && c < N;
}

// Check if a cell is a "Junction"
// Degree != 2, or degree == 2 but not straight (corner)
bool is_junction(int r, int c) {
    if (!is_road[r][c]) return false;
    if (r == si && c == sj) return true;
    
    int neighbors = 0;
    bool u = false, d = false, l = false, ri = false;
    if (is_valid(r-1, c) && is_road[r-1][c]) { neighbors++; u = true; }
    if (is_valid(r+1, c) && is_road[r+1][c]) { neighbors++; d = true; }
    if (is_valid(r, c-1) && is_road[r][c-1]) { neighbors++; l = true; }
    if (is_valid(r, c+1) && is_road[r][c+1]) { neighbors++; ri = true; }
    
    if (neighbors != 2) return true;
    if (u && d) return false; // Vertical straight
    if (l && ri) return false; // Horizontal straight
    return true; // Corner
}

// Precompute visible cells from a point
vector<Point> get_visible(int r, int c) {
    vector<Point> vis;
    if (!is_road[r][c]) return vis;
    
    vis.push_back({r, c});
    for (int d = 0; d < 4; d++) {
        int cr = r + dr[d];
        int cc = c + dc[d];
        while (is_valid(cr, cc) && is_road[cr][cc]) {
            vis.push_back({cr, cc});
            cr += dr[d];
            cc += dc[d];
        }
    }
    return vis;
}

void update_coverage(int r, int c) {
    // Recomputing visible cells here is slightly inefficient but safe.
    // Optimization: Just traverse and mark, using the inverse map update logic.
    
    // Center
    if (!cell_covered[r][c]) {
        cell_covered[r][c] = true;
        covered_count++;
        for (int id : nodes_seeing[r][c]) current_gain[id]--;
    }
    
    for (int d = 0; d < 4; d++) {
        int cr = r + dr[d];
        int cc = c + dc[d];
        while (is_valid(cr, cc) && is_road[cr][cc]) {
            if (!cell_covered[cr][cc]) {
                cell_covered[cr][cc] = true;
                covered_count++;
                for (int id : nodes_seeing[cr][cc]) current_gain[id]--;
            }
            cr += dr[d];
            cc += dc[d];
        }
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    cin >> N >> si >> sj;
    grid_map.resize(N);
    for (int i = 0; i < N; i++) {
        cin >> grid_map[i];
        for (int j = 0; j < N; j++) {
            if (grid_map[i][j] != '#') {
                costs[i][j] = grid_map[i][j] - '0';
                is_road[i][j] = true;
                total_road_cells++;
                node_idx[i][j] = -1;
            } else {
                is_road[i][j] = false;
            }
        }
    }
    
    // Identify Nodes
    for (int i = 0; i < N; i++) {
        for (int j = 0; j < N; j++) {
            if (is_junction(i, j)) {
                Node node;
                node.id = nodes.size();
                node.p = {i, j};
                node.visible_cells = get_visible(i, j);
                node_idx[i][j] = node.id;
                
                // Init gains
                current_gain[node.id] = node.visible_cells.size();
                for (auto& p : node.visible_cells) {
                    nodes_seeing[p.r][p.c].push_back(node.id);
                }
                
                nodes.push_back(node);
            }
        }
    }
    
    // Build Graph
    for (auto& u : nodes) {
        for (int d = 0; d < 4; d++) {
            int cr = u.p.r + dr[d];
            int cc = u.p.c + dc[d];
            int cost_sum = 0;
            string path = "";
            path += dchar[d];
            
            while (is_valid(cr, cc) && is_road[cr][cc]) {
                cost_sum += costs[cr][cc];
                if (node_idx[cr][cc] != -1) {
                    int v_id = node_idx[cr][cc];
                    adj[u.id].push_back({v_id, cost_sum});
                    adj_path[u.id].push_back(path);
                    break;
                }
                cr += dr[d];
                cc += dc[d];
                path += dchar[d];
            }
        }
    }
    
    string final_route = "";
    int cur_node_id = node_idx[si][sj];
    
    // Initial coverage update
    update_coverage(si, sj);
    
    // Greedy Loop
    while (covered_count < total_road_cells) {
        // Dijkstra to all nodes
        vector<int> dist(nodes.size(), INF);
        vector<int> parent(nodes.size(), -1);
        priority_queue<pair<int, int>, vector<pair<int, int>>, greater<pair<int, int>>> pq;
        
        dist[cur_node_id] = 0;
        pq.push({0, cur_node_id});
        
        while (!pq.empty()) {
            auto [d, u] = pq.top();
            pq.pop();
            
            if (d > dist[u]) continue;
            
            for (int k = 0; k < adj[u].size(); k++) {
                int v = adj[u][k].first;
                int weight = adj[u][k].second;
                if (dist[u] + weight < dist[v]) {
                    dist[v] = dist[u] + weight;
                    parent[v] = u;
                    pq.push({dist[v], v});
                }
            }
        }
        
        // Select target
        int best_target = -1;
        double best_score = -1.0;
        
        for (int i = 0; i < nodes.size(); i++) {
            if (dist[i] == INF) continue;
            if (current_gain[i] == 0) continue;
            
            // Heuristic: Gain / Cost
            double score = (double)current_gain[i] / (dist[i] + 1.0);
            if (score > best_score) {
                best_score = score;
                best_target = i;
            }
        }
        
        if (best_target == -1) break;
        
        // Reconstruct path
        vector<int> path_nodes;
        int curr = best_target;
        while (curr != cur_node_id) {
            path_nodes.push_back(curr);
            curr = parent[curr];
        }
        reverse(path_nodes.begin(), path_nodes.end());
        
        int temp_curr = cur_node_id;
        for (int next_node : path_nodes) {
            int edge_idx = -1;
            // Find edge matching Dijkstra
            for(int k=0; k<adj[temp_curr].size(); k++){
                if(adj[temp_curr][k].first == next_node && 
                   dist[next_node] == dist[temp_curr] + adj[temp_curr][k].second) {
                     edge_idx = k; break;
                }
            }
            if (edge_idx == -1) {
                for(int k=0; k<adj[temp_curr].size(); k++) 
                    if(adj[temp_curr][k].first == next_node) { edge_idx = k; break; }
            }
            
            string p_str = adj_path[temp_curr][edge_idx];
            final_route += p_str;
            
            // Step-by-step simulation to update coverage
            int r = nodes[temp_curr].p.r;
            int c = nodes[temp_curr].p.c;
            for (char move : p_str) {
                if (move == 'U') r--;
                else if (move == 'D') r++;
                else if (move == 'L') c--;
                else if (move == 'R') c++;
                update_coverage(r, c);
            }
            temp_curr = next_node;
        }
        cur_node_id = best_target;
    }
    
    // Return to start
    int start_node_id = node_idx[si][sj];
    if (cur_node_id != start_node_id) {
        vector<int> dist(nodes.size(), INF);
        vector<int> parent(nodes.size(), -1);
        priority_queue<pair<int, int>, vector<pair<int, int>>, greater<pair<int, int>>> pq;
        
        dist[cur_node_id] = 0;
        pq.push({0, cur_node_id});
        
        while (!pq.empty()) {
            auto [d, u] = pq.top();
            pq.pop();
            
            if (u == start_node_id) break;
            if (d > dist[u]) continue;
            
            for (int k = 0; k < adj[u].size(); k++) {
                int v = adj[u][k].first;
                int weight = adj[u][k].second;
                if (dist[u] + weight < dist[v]) {
                    dist[v] = dist[u] + weight;
                    parent[v] = u;
                    pq.push({dist[v], v});
                }
            }
        }
        
        vector<int> path_nodes;
        int curr = start_node_id;
        while (curr != cur_node_id && curr != -1) {
            path_nodes.push_back(curr);
            curr = parent[curr];
        }
        reverse(path_nodes.begin(), path_nodes.end());
        
        int temp_curr = cur_node_id;
        for (int next_node : path_nodes) {
            int edge_idx = -1;
            for(int k=0; k<adj[temp_curr].size(); k++){
                if(adj[temp_curr][k].first == next_node && 
                   dist[next_node] == dist[temp_curr] + adj[temp_curr][k].second) {
                     edge_idx = k; break;
                }
            }
            if (edge_idx == -1) {
                for(int k=0; k<adj[temp_curr].size(); k++) 
                    if(adj[temp_curr][k].first == next_node) { edge_idx = k; break; }
            }
            
            final_route += adj_path[temp_curr][edge_idx];
            temp_curr = next_node;
        }
    }
    
    cout << final_route << endl;
    return 0;
}