#include <iostream>
#include <vector>
#include <string>
#include <queue>
#include <tuple>
#include <algorithm>
#include <bitset>
#include <cmath>

using namespace std;

// Maximum dimensions based on problem statement
const int MAX_N = 70;
const int MAX_NODES = MAX_N * MAX_N; // Approx 4900
const int INF = 1e9;

int N;
int si, sj;
vector<string> grid;
int node_id[MAX_N][MAX_N];
pair<int, int> id_to_pos[MAX_NODES];
int road_count = 0;

// Bitsets to track visibility. N*N <= 4761, so 5000 is sufficient.
bitset<5000> visibility[MAX_NODES];
bitset<5000> seen_mask;

int dr[] = {-1, 1, 0, 0};
int dc[] = {0, 0, -1, 1};

bool is_valid(int r, int c) {
    return r >= 0 && r < N && c >= 0 && c < N && grid[r][c] != '#';
}

int get_cost(int r, int c) {
    return grid[r][c] - '0';
}

void precompute_visibility() {
    for (int r = 0; r < N; ++r) {
        for (int c = 0; c < N; ++c) {
            if (grid[r][c] == '#') continue;
            int u = node_id[r][c];
            
            // Look in 4 directions to find visible squares
            // Up
            for (int i = r; i >= 0; --i) {
                if (grid[i][c] == '#') break;
                visibility[u].set(node_id[i][c]);
            }
            // Down
            for (int i = r + 1; i < N; ++i) {
                if (grid[i][c] == '#') break;
                visibility[u].set(node_id[i][c]);
            }
            // Left
            for (int j = c - 1; j >= 0; --j) {
                if (grid[r][j] == '#') break;
                visibility[u].set(node_id[r][j]);
            }
            // Right
            for (int j = c + 1; j < N; ++j) {
                if (grid[r][j] == '#') break;
                visibility[u].set(node_id[r][j]);
            }
        }
    }
}

struct State {
    int d;
    int u;
    bool operator>(const State& other) const {
        return d > other.d;
    }
};

int dist_map[MAX_NODES];
int parent_node[MAX_NODES];

// Dijkstra to find shortest paths from start_u to all other nodes
void run_dijkstra(int start_u) {
    for (int i = 0; i < road_count; ++i) {
        dist_map[i] = INF;
        parent_node[i] = -1;
    }
    
    priority_queue<State, vector<State>, greater<State>> pq;
    dist_map[start_u] = 0;
    pq.push({0, start_u});
    
    while (!pq.empty()) {
        State top = pq.top();
        pq.pop();
        
        if (top.d > dist_map[top.u]) continue;
        
        int u = top.u;
        int r = id_to_pos[u].first;
        int c = id_to_pos[u].second;
        
        for (int k = 0; k < 4; ++k) {
            int nr = r + dr[k];
            int nc = c + dc[k];
            if (is_valid(nr, nc)) {
                int v = node_id[nr][nc];
                int weight = get_cost(nr, nc);
                if (dist_map[u] + weight < dist_map[v]) {
                    dist_map[v] = dist_map[u] + weight;
                    parent_node[v] = u;
                    pq.push({dist_map[v], v});
                }
            }
        }
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    if (!(cin >> N >> si >> sj)) return 0;
    
    grid.resize(N);
    for (int i = 0; i < N; ++i) {
        cin >> grid[i];
    }
    
    road_count = 0;
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            if (grid[i][j] != '#') {
                node_id[i][j] = road_count;
                id_to_pos[road_count] = {i, j};
                road_count++;
            } else {
                node_id[i][j] = -1;
            }
        }
    }
    
    precompute_visibility();
    
    // Identify candidate targets: Intersections, Endpoints, Corners
    vector<int> candidates;
    for (int u = 0; u < road_count; ++u) {
        int r = id_to_pos[u].first;
        int c = id_to_pos[u].second;
        vector<pair<int, int>> nbrs;
        for(int k=0; k<4; ++k) {
            int nr = r + dr[k];
            int nc = c + dc[k];
            if(is_valid(nr, nc)) nbrs.push_back({nr, nc});
        }
        
        if (nbrs.size() != 2) {
            candidates.push_back(u); // Endpoint (1) or Intersection (>2)
        } else {
            // Check if it is a corner (degree 2 but not straight)
            bool row_same = (nbrs[0].first == nbrs[1].first);
            bool col_same = (nbrs[0].second == nbrs[1].second);
            if (!row_same && !col_same) candidates.push_back(u);
        }
    }
    
    int curr_u = node_id[si][sj];
    seen_mask |= visibility[curr_u];
    
    string total_path = "";
    
    // Greedy strategy: repeatedly move towards the best target
    // We update decision after every single step
    while (seen_mask.count() < road_count) {
        run_dijkstra(curr_u);
        
        int best_target = -1;
        double best_score = -1.0;
        
        // Evaluate candidates
        for (int u : candidates) {
            if (u == curr_u || dist_map[u] == INF) continue;
            
            // Calculate how many NEW squares become visible
            bitset<5000> diff = visibility[u];
            diff &= ~seen_mask;
            int gain = diff.count();
            
            if (gain == 0) continue;
            
            double cost = dist_map[u];
            // Heuristic: favor large gains, penalize distance
            double score = (double)gain * gain / (cost + 1e-9);
            
            if (score > best_score) {
                best_score = score;
                best_target = u;
            }
        }
        
        // Safety fallback: check all nodes if candidates fail (should correspond to edge cases)
        if (best_target == -1) {
            for (int u = 0; u < road_count; ++u) {
                if (u == curr_u || dist_map[u] == INF) continue;
                bitset<5000> diff = visibility[u];
                diff &= ~seen_mask;
                int gain = diff.count();
                if (gain > 0) {
                    double cost = dist_map[u];
                    double score = (double)gain * gain / (cost + 1e-9);
                    if (score > best_score) {
                        best_score = score;
                        best_target = u;
                    }
                }
            }
            if (best_target == -1) break; // All reachable nodes seen/visited
        }
        
        // Move one step towards best_target
        int next = best_target;
        while (parent_node[next] != curr_u) {
            next = parent_node[next];
        }
        
        int cr = id_to_pos[curr_u].first;
        int cc = id_to_pos[curr_u].second;
        int nr = id_to_pos[next].first;
        int nc = id_to_pos[next].second;
        
        if (nr == cr - 1) total_path += 'U';
        else if (nr == cr + 1) total_path += 'D';
        else if (nc == cc - 1) total_path += 'L';
        else if (nc == cc + 1) total_path += 'R';
        
        curr_u = next;
        seen_mask |= visibility[curr_u];
    }
    
    // Return to start
    run_dijkstra(curr_u);
    int start_node = node_id[si][sj];
    
    if (curr_u != start_node) {
        int curr = start_node;
        string ret_path = "";
        while (curr != curr_u) {
            int p = parent_node[curr];
            // Move was p -> curr
            int pr = id_to_pos[p].first;
            int pc = id_to_pos[p].second;
            int cr = id_to_pos[curr].first;
            int cc = id_to_pos[curr].second;
            
            if (pr == cr + 1) ret_path += 'U';
            else if (pr == cr - 1) ret_path += 'D';
            else if (pc == cc + 1) ret_path += 'L';
            else if (pc == cc - 1) ret_path += 'R';
            
            curr = p;
        }
        reverse(ret_path.begin(), ret_path.end());
        total_path += ret_path;
    }
    
    cout << total_path << endl;
    
    return 0;
}