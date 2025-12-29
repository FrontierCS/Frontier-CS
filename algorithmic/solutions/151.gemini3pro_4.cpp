#include <iostream>
#include <vector>
#include <string>
#include <queue>
#include <tuple>
#include <bitset>
#include <algorithm>
#include <cmath>

using namespace std;

// Constants
const int MAXN = 75;
const int MAX_CELLS = MAXN * MAXN;
const int INF = 1e9;

// Global variables
int N;
int si, sj;
string grid_str[MAXN];
int cost_grid[MAXN][MAXN];
int cell_id[MAXN][MAXN];
pair<int, int> id_to_cell[MAX_CELLS];
int num_roads = 0;

// Directions: U, D, L, R
const int DR[] = {-1, 1, 0, 0};
const int DC[] = {0, 0, -1, 1};
const char DCHAR[] = {'U', 'D', 'L', 'R'};

// Visibility
// Maximum N is 69, so 69*69 = 4761 cells. Bitset of 5000 is sufficient.
typedef bitset<5000> BitSet;
BitSet visible_from[MAX_CELLS];

// Helper to check bounds and obstacle
bool isValid(int r, int c) {
    return r >= 0 && r < N && c >= 0 && c < N && grid_str[r][c] != '#';
}

// Precompute visibility for each cell
void precomputeVisibility() {
    for (int r = 0; r < N; ++r) {
        for (int c = 0; c < N; ++c) {
            if (!isValid(r, c)) continue;
            int u = cell_id[r][c];
            visible_from[u].set(u); // Sees itself
            
            // Check all 4 directions
            for (int d = 0; d < 4; ++d) {
                int cr = r + DR[d];
                int cc = c + DC[d];
                while (isValid(cr, cc)) {
                    int v = cell_id[cr][cc];
                    visible_from[u].set(v);
                    cr += DR[d];
                    cc += DC[d];
                }
            }
        }
    }
}

// Dijkstra state
struct State {
    int u;
    int dist;
    bool operator>(const State& other) const {
        return dist > other.dist;
    }
};

// Function to rebuild path from Dijkstra parents
string getPath(int start_u, int end_u, const vector<int>& parent, const vector<int>& move_dir) {
    string path = "";
    int curr = end_u;
    while (curr != start_u) {
        int p = parent[curr];
        int d = move_dir[curr];
        if (p == -1) break; // Should not happen if reachable
        path += DCHAR[d];
        curr = p;
    }
    reverse(path.begin(), path.end());
    return path;
}

int main() {
    // Fast IO
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    // Input
    if (!(cin >> N >> si >> sj)) return 0;
    for (int i = 0; i < N; ++i) {
        cin >> grid_str[i];
    }

    // Parse grid and assign IDs
    int id_counter = 0;
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            if (grid_str[i][j] != '#') {
                cell_id[i][j] = id_counter;
                id_to_cell[id_counter] = {i, j};
                cost_grid[i][j] = grid_str[i][j] - '0';
                id_counter++;
            } else {
                cell_id[i][j] = -1;
            }
        }
    }
    num_roads = id_counter;

    // Precompute visibility
    precomputeVisibility();

    // Simulation state
    BitSet unseen;
    for (int i = 0; i < num_roads; ++i) unseen.set(i);
    
    int curr_u = cell_id[si][sj];
    string total_route = "";
    
    // Initial visibility from start point
    unseen &= ~visible_from[curr_u];

    // Main greedy loop
    while (unseen.count() > 0) {
        // Run Dijkstra from curr_u to find distances to all other nodes
        vector<int> dist(num_roads, INF);
        vector<int> parent(num_roads, -1);
        vector<int> move_dir(num_roads, -1);
        priority_queue<State, vector<State>, greater<State>> pq;

        dist[curr_u] = 0;
        pq.push({curr_u, 0});

        vector<int> visited_nodes; 
        visited_nodes.reserve(num_roads);

        while (!pq.empty()) {
            State top = pq.top();
            pq.pop();
            int u = top.u;

            if (top.dist > dist[u]) continue;
            visited_nodes.push_back(u);

            int r = id_to_cell[u].first;
            int c = id_to_cell[u].second;

            for (int d = 0; d < 4; ++d) {
                int nr = r + DR[d];
                int nc = c + DC[d];
                if (isValid(nr, nc)) {
                    int v = cell_id[nr][nc];
                    int new_cost = dist[u] + cost_grid[nr][nc];
                    if (new_cost < dist[v]) {
                        dist[v] = new_cost;
                        parent[v] = u;
                        move_dir[v] = d;
                        pq.push({v, new_cost});
                    }
                }
            }
        }

        // Evaluate candidates
        // We look for a target that maximizes (gain^2 / cost)
        // This heuristic balances high visibility gain with travel time
        double best_score = -1.0;
        int best_target = -1;

        for (int v : visited_nodes) {
            int d = dist[v];
            
            // If d == 0 (current node), we gain nothing new since we already processed it.
            // Just skip.
            if (d == 0) continue; 
            
            // Calculate how many NEW cells we would see from v
            // Note: This ignores cells seen along the path to v, approximating gain.
            // Intersection of bitsets is fast.
            int gain = (visible_from[v] & unseen).count();

            if (gain > 0) {
                // Heuristic: Prefer nodes with high gain and low distance.
                // Squaring gain emphasizes visiting "hubs" or intersections that clear a lot.
                double score = (double)gain * gain / d;
                if (score > best_score) {
                    best_score = score;
                    best_target = v;
                }
            }
        }

        if (best_target == -1) {
            // Should not happen if graph is connected and there are unseen cells reachable.
            break; 
        }

        // Reconstruct path to best_target
        string segment = getPath(curr_u, best_target, parent, move_dir);
        total_route += segment;
        
        // Update unseen based on the path taken
        // We walk the path and update visibility at each step
        int r = id_to_cell[curr_u].first;
        int c = id_to_cell[curr_u].second;
        for (char move : segment) {
            int d = -1;
            if (move == 'U') d = 0;
            else if (move == 'D') d = 1;
            else if (move == 'L') d = 2;
            else if (move == 'R') d = 3;
            
            r += DR[d];
            c += DC[d];
            int u = cell_id[r][c];
            unseen &= ~visible_from[u];
        }
        curr_u = best_target;
    }

    // Return to start
    int start_node = cell_id[si][sj];
    if (curr_u != start_node) {
        vector<int> dist(num_roads, INF);
        vector<int> parent(num_roads, -1);
        vector<int> move_dir(num_roads, -1);
        priority_queue<State, vector<State>, greater<State>> pq;

        dist[curr_u] = 0;
        pq.push({curr_u, 0});

        bool found = false;
        while (!pq.empty()) {
            State top = pq.top();
            pq.pop();
            int u = top.u;

            if (u == start_node) {
                found = true;
                break;
            }
            if (top.dist > dist[u]) continue;

            int r = id_to_cell[u].first;
            int c = id_to_cell[u].second;

            for (int d = 0; d < 4; ++d) {
                int nr = r + DR[d];
                int nc = c + DC[d];
                if (isValid(nr, nc)) {
                    int v = cell_id[nr][nc];
                    int new_cost = dist[u] + cost_grid[nr][nc];
                    if (new_cost < dist[v]) {
                        dist[v] = new_cost;
                        parent[v] = u;
                        move_dir[v] = d;
                        pq.push({v, new_cost});
                    }
                }
            }
        }
        if (found) {
            total_route += getPath(curr_u, start_node, parent, move_dir);
        }
    }

    cout << total_route << endl;

    return 0;
}