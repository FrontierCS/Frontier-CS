/*
    AtCoder Shortest Path with Unknown Edge Lengths
    Solution using Dijkstra with iterative weight estimation.
    We maintain estimates for each edge.
    - Visited edges are updated using a variance-weighted distribution of the residual error (Kalman-like update).
    - Unvisited edges are estimated for pathfinding by using the average weight of visited edges in the same row/column (exploiting the problem's structural generation).
*/
#include <iostream>
#include <vector>
#include <string>
#include <queue>
#include <cmath>
#include <algorithm>
#include <iomanip>

using namespace std;

// Grid dimensions
const int N = 30;

// Initial guesses
const double INIT_VAL = 5000.0;
// Prior variance for an edge weight (uniform 1000-9000 -> variance ~ 5.33e6)
const double INIT_VAR = 5333333.0; 

// State arrays
// H[i][j] stores the estimated weight of the horizontal edge between (i,j) and (i,j+1)
double H[30][29];
int cntH[30][29];

// V[i][j] stores the estimated weight of the vertical edge between (i,j) and (i+1,j)
double V[29][30];
int cntV[29][30];

// Temporary weights used for pathfinding in the current query
double curH[30][29];
double curV[29][30];

void init() {
    for(int i=0; i<30; ++i) {
        for(int j=0; j<29; ++j) {
            H[i][j] = INIT_VAL;
            cntH[i][j] = 0;
        }
    }
    for(int i=0; i<29; ++i) {
        for(int j=0; j<30; ++j) {
            V[i][j] = INIT_VAL;
            cntV[i][j] = 0;
        }
    }
}

// Populate curH and curV.
// For edges that have been visited/updated (cnt > 0), use their estimated value.
// For edges never visited, use the average of the visited edges in the same row/column.
// If a row/column has no visited edges, use INIT_VAL.
void prepare_weights() {
    // Horizontal edges
    for (int i = 0; i < 30; ++i) {
        double sum = 0;
        int count = 0;
        for (int j = 0; j < 29; ++j) {
            if (cntH[i][j] > 0) {
                sum += H[i][j];
                count++;
            }
        }
        double avg = (count > 0) ? (sum / count) : INIT_VAL;
        for (int j = 0; j < 29; ++j) {
            if (cntH[i][j] > 0) {
                curH[i][j] = H[i][j];
            } else {
                curH[i][j] = avg;
            }
        }
    }
    
    // Vertical edges
    for (int j = 0; j < 30; ++j) {
        double sum = 0;
        int count = 0;
        for (int i = 0; i < 29; ++i) {
            if (cntV[i][j] > 0) {
                sum += V[i][j];
                count++;
            }
        }
        double avg = (count > 0) ? (sum / count) : INIT_VAL;
        for (int i = 0; i < 29; ++i) {
            if (cntV[i][j] > 0) {
                curV[i][j] = V[i][j];
            } else {
                curV[i][j] = avg;
            }
        }
    }
}

struct Node {
    int id;
    double dist;
    bool operator>(const Node& other) const {
        return dist > other.dist;
    }
};

// Dijkstra's algorithm
// Returns the path string and populates path_edges with the specific edges used
string solve_dijkstra(int si, int sj, int ti, int tj, vector<pair<bool, pair<int, int>>>& path_edges) {
    priority_queue<Node, vector<Node>, greater<Node>> pq;
    vector<double> dist(N * N, 1e18);
    vector<int> parent(N * N, -1);
    vector<char> move_char(N * N, 0);
    
    int start_node = si * N + sj;
    int target_node = ti * N + tj;
    
    dist[start_node] = 0;
    pq.push({start_node, 0});
    
    while (!pq.empty()) {
        Node current = pq.top();
        pq.pop();
        
        int u = current.id;
        if (current.dist > dist[u]) continue;
        if (u == target_node) break;
        
        int r = u / N;
        int c = u % N;
        
        // Up: (r, c) -> (r-1, c) using V[r-1][c]
        if (r > 0) {
            int v_idx = (r - 1) * N + c;
            double w = curV[r - 1][c];
            if (dist[u] + w < dist[v_idx]) {
                dist[v_idx] = dist[u] + w;
                parent[v_idx] = u;
                move_char[v_idx] = 'U';
                pq.push({v_idx, dist[v_idx]});
            }
        }
        // Down: (r, c) -> (r+1, c) using V[r][c]
        if (r < N - 1) {
            int v_idx = (r + 1) * N + c;
            double w = curV[r][c];
            if (dist[u] + w < dist[v_idx]) {
                dist[v_idx] = dist[u] + w;
                parent[v_idx] = u;
                move_char[v_idx] = 'D';
                pq.push({v_idx, dist[v_idx]});
            }
        }
        // Left: (r, c) -> (r, c-1) using H[r][c-1]
        if (c > 0) {
            int v_idx = r * N + (c - 1);
            double w = curH[r][c - 1];
            if (dist[u] + w < dist[v_idx]) {
                dist[v_idx] = dist[u] + w;
                parent[v_idx] = u;
                move_char[v_idx] = 'L';
                pq.push({v_idx, dist[v_idx]});
            }
        }
        // Right: (r, c) -> (r, c+1) using H[r][c]
        if (c < N - 1) {
            int v_idx = r * N + (c + 1);
            double w = curH[r][c];
            if (dist[u] + w < dist[v_idx]) {
                dist[v_idx] = dist[u] + w;
                parent[v_idx] = u;
                move_char[v_idx] = 'R';
                pq.push({v_idx, dist[v_idx]});
            }
        }
    }
    
    // Backtrack
    string path = "";
    int curr = target_node;
    while (curr != start_node) {
        int prev = parent[curr];
        char mv = move_char[curr];
        path += mv;
        
        int r = prev / N;
        int c = prev % N;
        
        if (mv == 'U') {
            path_edges.push_back({false, {r - 1, c}});
        } else if (mv == 'D') {
            path_edges.push_back({false, {r, c}});
        } else if (mv == 'L') {
            path_edges.push_back({true, {r, c - 1}});
        } else if (mv == 'R') {
            path_edges.push_back({true, {r, c}});
        }
        
        curr = prev;
    }
    reverse(path.begin(), path.end());
    reverse(path_edges.begin(), path_edges.end());
    return path;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    init();
    
    int si, sj, ti, tj;
    for (int k = 0; k < 1000; ++k) {
        if (!(cin >> si >> sj >> ti >> tj)) break;
        
        prepare_weights();
        
        vector<pair<bool, pair<int, int>>> path_edges;
        string path_str = solve_dijkstra(si, sj, ti, tj, path_edges);
        
        cout << path_str << endl;
        
        double measured_len;
        cin >> measured_len;
        
        // --- Estimation Update Step ---
        
        double estimated_len = 0;
        double sum_var = 0;
        
        // Compute the length predicted by our current persistent estimates (H/V)
        for (auto& edge : path_edges) {
            bool is_h = edge.first;
            int r = edge.second.first;
            int c = edge.second.second;
            
            if (is_h) {
                estimated_len += H[r][c];
                sum_var += INIT_VAR / (cntH[r][c] + 1.0);
            } else {
                estimated_len += V[r][c];
                sum_var += INIT_VAR / (cntV[r][c] + 1.0);
            }
        }
        
        double diff = measured_len - estimated_len;
        
        // Variance of the multiplicative noise (uniform +/- 10%)
        // Var(U[0.9L, 1.1L]) = (0.2L)^2 / 12 = 0.04L^2 / 12 = L^2 / 300
        double noise_var = (measured_len * measured_len) / 300.0;
        if (noise_var < 1.0) noise_var = 1.0;
        
        double total_var = sum_var + noise_var;
        
        // Distribute the residual `diff` based on relative variances
        for (auto& edge : path_edges) {
            bool is_h = edge.first;
            int r = edge.second.first;
            int c = edge.second.second;
            
            double my_var;
            if (is_h) my_var = INIT_VAR / (cntH[r][c] + 1.0);
            else      my_var = INIT_VAR / (cntV[r][c] + 1.0);
            
            double gain = my_var / total_var;
            double change = diff * gain;
            
            if (is_h) {
                H[r][c] += change;
                // Clamp values to valid range
                if(H[r][c] < 1000) H[r][c] = 1000;
                if(H[r][c] > 9000) H[r][c] = 9000;
                cntH[r][c]++;
            } else {
                V[r][c] += change;
                if(V[r][c] < 1000) V[r][c] = 1000;
                if(V[r][c] > 9000) V[r][c] = 9000;
                cntV[r][c]++;
            }
        }
    }
    
    return 0;
}