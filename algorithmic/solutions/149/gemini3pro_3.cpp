#include <iostream>
#include <vector>
#include <string>
#include <queue>
#include <cmath>
#include <algorithm>
#include <iomanip>

using namespace std;

const int N = 30;
const int NUM_QUERIES = 1000;
const double INF = 1e18;

// Map (row, col) to linear edge index
// Horizontal edges: (r, c) -> (r, c+1). r: 0..29, c: 0..28
// Index = r * 29 + c
// Range: [0, 869]
int get_h_idx(int r, int c) {
    return r * 29 + c;
}

// Vertical edges: (r, c) -> (r+1, c). r: 0..28, c: 0..29
// Index = 870 + r * 30 + c
// Range: [870, 1739]
int get_v_idx(int r, int c) {
    return 870 + r * 30 + c;
}

// Global weights
vector<double> weights;

struct Query {
    vector<int> path_edges;
    int measured_val;
};
vector<Query> history;

// Directions for Dijkstra: U, D, L, R
int dr[] = {-1, 1, 0, 0};
int dc[] = {0, 0, -1, 1};
char dchar[] = {'U', 'D', 'L', 'R'};

struct Node {
    int r, c;
    double dist;
    bool operator>(const Node& other) const {
        return dist > other.dist;
    }
};

struct Parent {
    int r, c;
    int edge_idx;
    int dir_idx;
};

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    // Initial weights guess. 
    // Edge weights are generated in range roughly [1000, 9000] with mean 5000.
    weights.assign(1740, 5000.0);
    history.reserve(NUM_QUERIES);

    for (int k = 0; k < NUM_QUERIES; ++k) {
        int si, sj, ti, tj;
        if (!(cin >> si >> sj >> ti >> tj)) break;

        // Dijkstra to find shortest path with current weights
        vector<vector<double>> dist(N, vector<double>(N, INF));
        vector<vector<Parent>> parent(N, vector<Parent>(N, {-1, -1, -1, -1}));
        priority_queue<Node, vector<Node>, greater<Node>> pq;

        dist[si][sj] = 0;
        pq.push({si, sj, 0});

        while (!pq.empty()) {
            Node current = pq.top();
            pq.pop();
            int r = current.r;
            int c = current.c;

            if (current.dist > dist[r][c]) continue;
            if (r == ti && c == tj) break;

            for (int i = 0; i < 4; ++i) {
                int nr = r + dr[i];
                int nc = c + dc[i];

                if (nr >= 0 && nr < N && nc >= 0 && nc < N) {
                    int edge_idx = -1;
                    if (i == 0) { // U: (r,c) -> (r-1,c) uses v-edge at (r-1, c)
                        edge_idx = get_v_idx(r - 1, c);
                    } else if (i == 1) { // D: (r,c) -> (r+1,c) uses v-edge at (r, c)
                        edge_idx = get_v_idx(r, c);
                    } else if (i == 2) { // L: (r,c) -> (r,c-1) uses h-edge at (r, c-1)
                        edge_idx = get_h_idx(r, c - 1);
                    } else if (i == 3) { // R: (r,c) -> (r,c+1) uses h-edge at (r, c)
                        edge_idx = get_h_idx(r, c);
                    }

                    double w = weights[edge_idx];
                    if (dist[r][c] + w < dist[nr][nc]) {
                        dist[nr][nc] = dist[r][c] + w;
                        parent[nr][nc] = {r, c, edge_idx, i};
                        pq.push({nr, nc, dist[nr][nc]});
                    }
                }
            }
        }

        // Reconstruct path
        string path_str = "";
        vector<int> path_edges;
        int curr_r = ti;
        int curr_c = tj;

        while (curr_r != si || curr_c != sj) {
            Parent p = parent[curr_r][curr_c];
            path_str += dchar[p.dir_idx];
            path_edges.push_back(p.edge_idx);
            curr_r = p.r;
            curr_c = p.c;
        }
        reverse(path_str.begin(), path_str.end());
        reverse(path_edges.begin(), path_edges.end());

        cout << path_str << endl;

        int measured_val;
        cin >> measured_val;

        history.push_back({path_edges, measured_val});

        // Update weights
        // Use iterative update on history + spatial smoothing to estimate edge weights
        // This solves a regularized least squares problem approximately using Kaczmarz/SGD like updates.
        // We smooth along rows/cols because weights in same row/col are correlated.
        
        double eta = 0.5; // Update step size for path constraints
        double alpha = 0.1; // Smoothing factor
        int iterations = 6; // Number of iterations over history per query

        for (int iter = 0; iter < iterations; ++iter) {
            // Apply path constraints
            for (const auto& q : history) {
                double current_len = 0;
                for (int e_idx : q.path_edges) current_len += weights[e_idx];
                
                double diff = q.measured_val - current_len;
                if (q.path_edges.empty()) continue;
                double correction = (diff / q.path_edges.size()) * eta;
                
                for (int e_idx : q.path_edges) {
                    weights[e_idx] += correction;
                    // Clamp to valid range to prevent instability
                    if (weights[e_idx] < 100.0) weights[e_idx] = 100.0;
                }
            }

            // Apply smoothing
            // Horizontal edges: smooth across columns
            for (int r = 0; r < 30; ++r) {
                for (int c = 0; c < 29; ++c) {
                    int idx = get_h_idx(r, c);
                    double val = weights[idx];
                    double sum_neighbors = 0;
                    int count = 0;
                    if (c > 0) { sum_neighbors += weights[get_h_idx(r, c - 1)]; count++; }
                    if (c < 28) { sum_neighbors += weights[get_h_idx(r, c + 1)]; count++; }
                    if (count > 0) {
                        weights[idx] = (1.0 - alpha) * val + alpha * (sum_neighbors / count);
                    }
                }
            }
            // Vertical edges: smooth across rows
            for (int c = 0; c < 30; ++c) {
                for (int r = 0; r < 29; ++r) {
                    int idx = get_v_idx(r, c);
                    double val = weights[idx];
                    double sum_neighbors = 0;
                    int count = 0;
                    if (r > 0) { sum_neighbors += weights[get_v_idx(r - 1, c)]; count++; }
                    if (r < 28) { sum_neighbors += weights[get_v_idx(r + 1, c)]; count++; }
                    if (count > 0) {
                        weights[idx] = (1.0 - alpha) * val + alpha * (sum_neighbors / count);
                    }
                }
            }
        }
    }

    return 0;
}