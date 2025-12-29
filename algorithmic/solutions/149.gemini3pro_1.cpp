#include <iostream>
#include <vector>
#include <string>
#include <queue>
#include <tuple>
#include <cmath>
#include <algorithm>
#include <iomanip>

using namespace std;

// Constants
// N: Grid size 30x30
// NUM_VARS: Number of variables for RLS (Recursive Least Squares)
// We divide each of the 30 rows and 30 columns into 4 segments (bins) to capture edge weight variations.
// 30 rows * 4 bins + 30 cols * 4 bins = 240 variables.
const int N = 30;
const int NUM_VARS = 240; 

// RLS State
// theta: Estimated weight for each block variable. Initialized to expected mean (5000).
vector<double> theta(NUM_VARS, 5000.0);
// P: Inverse covariance matrix. Initialized to identity * large value (representing high uncertainty).
vector<vector<double>> P(NUM_VARS, vector<double>(NUM_VARS, 0.0));

// Direction arrays for grid movement: U, D, L, R
const int dr[] = {-1, 1, 0, 0};
const int dc[] = {0, 0, -1, 1};
const char moves_char[] = {'U', 'D', 'L', 'R'};

// Helper to get bin index for edge position
// Divides the range [0, 28] into 4 bins roughly equal size.
int get_bin(int idx) {
    if (idx < 7) return 0;
    if (idx < 14) return 1;
    if (idx < 21) return 2;
    return 3;
}

// Helper to get variable index for a specific edge
// type 0: Horizontal edge, 1: Vertical edge
// Horizontal edge at (r, c) connects (r, c) and (r, c+1)
// Vertical edge at (r, c) connects (r, c) and (r+1, c)
int get_var_index(int type, int r, int c) {
    if (type == 0) { // Horizontal: associated with row r, bin based on c
        return r * 4 + get_bin(c);
    } else { // Vertical: associated with col c, bin based on r
        return 120 + c * 4 + get_bin(r);
    }
}

// Get estimated weight for Dijkstra
// Returns the theta value corresponding to the edge's block, clamped to valid range.
double get_weight(int type, int r, int c) {
    int idx = get_var_index(type, r, c);
    double w = theta[idx];
    if (w < 1000.0) return 1000.0;
    if (w > 9000.0) return 9000.0;
    return w;
}

struct Node {
    int r, c;
    double dist;
    bool operator>(const Node& other) const {
        return dist > other.dist;
    }
};

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    // Initialize P matrix
    // A high initial value allows the parameters to adapt quickly from the initial guess.
    for (int i = 0; i < NUM_VARS; ++i) {
        P[i][i] = 100000.0;
    }

    // Process 1000 queries
    for (int k = 0; k < 1000; ++k) {
        int si, sj, ti, tj;
        cin >> si >> sj >> ti >> tj;

        // Dijkstra's Algorithm to find shortest path using current estimates
        vector<vector<double>> dist(N, vector<double>(N, 1e18));
        vector<vector<int>> parent_dir(N, vector<int>(N, -1));
        priority_queue<Node, vector<Node>, greater<Node>> pq;

        dist[si][sj] = 0;
        pq.push({si, sj, 0});

        while (!pq.empty()) {
            Node top = pq.top();
            pq.pop();
            int r = top.r;
            int c = top.c;
            double d = top.dist;

            if (d > dist[r][c]) continue;
            if (r == ti && c == tj) break;

            for (int i = 0; i < 4; ++i) {
                int nr = r + dr[i];
                int nc = c + dc[i];

                if (nr >= 0 && nr < N && nc >= 0 && nc < N) {
                    double weight = 0;
                    // Determine edge type and coordinates for weight lookup
                    if (i == 0) { // U: (nr, c) -> (r, c), Vertical at (nr, c)
                        weight = get_weight(1, nr, c);
                    } else if (i == 1) { // D: (r, c) -> (nr, c), Vertical at (r, c)
                        weight = get_weight(1, r, c);
                    } else if (i == 2) { // L: (r, nc) -> (r, c), Horizontal at (r, nc)
                        weight = get_weight(0, r, nc);
                    } else if (i == 3) { // R: (r, c) -> (r, nc), Horizontal at (r, c)
                        weight = get_weight(0, r, c);
                    }

                    if (dist[r][c] + weight < dist[nr][nc]) {
                        dist[nr][nc] = dist[r][c] + weight;
                        parent_dir[nr][nc] = i;
                        pq.push({nr, nc, dist[nr][nc]});
                    }
                }
            }
        }

        // Reconstruct path string and feature vector
        string path = "";
        int curr_r = ti;
        int curr_c = tj;
        
        // phi stores the count of times each block variable is used in the path
        vector<double> phi(NUM_VARS, 0.0);
        
        while (curr_r != si || curr_c != sj) {
            int dir = parent_dir[curr_r][curr_c];
            path += moves_char[dir];
            
            int prev_r = curr_r - dr[dir];
            int prev_c = curr_c - dc[dir];

            int var_idx = -1;
            // Identify the edge traversed
            if (dir == 0) { // U
                var_idx = get_var_index(1, curr_r, curr_c);
            } else if (dir == 1) { // D
                var_idx = get_var_index(1, prev_r, curr_c);
            } else if (dir == 2) { // L
                var_idx = get_var_index(0, curr_r, curr_c);
            } else if (dir == 3) { // R
                var_idx = get_var_index(0, curr_r, prev_c);
            }
            
            if (var_idx != -1) {
                phi[var_idx] += 1.0;
            }
            
            curr_r = prev_r;
            curr_c = prev_c;
        }
        reverse(path.begin(), path.end());
        cout << path << endl; // Flush output

        // Read actual result
        int result_len;
        cin >> result_len;

        // RLS Update Steps
        // The algorithm updates estimates to minimize prediction error.
        
        // 1. Calculate P * phi
        vector<double> Pphi(NUM_VARS, 0.0);
        for (int i = 0; i < NUM_VARS; ++i) {
            for (int j = 0; j < NUM_VARS; ++j) {
                // Optimization: phi is sparse, check for non-zero entries
                if (phi[j] > 0.5) {
                    Pphi[i] += P[i][j] * phi[j];
                }
            }
        }

        // 2. Calculate denominator = R_noise + phi^T * P * phi
        // Measurement noise variance roughly scales with square of path length.
        double R_noise = max(100.0, result_len * result_len * 0.005); 
        
        double denom = R_noise;
        for (int j = 0; j < NUM_VARS; ++j) {
            if (phi[j] > 0.5) {
                denom += phi[j] * Pphi[j];
            }
        }

        // 3. Calculate Kalman Gain K = Pphi / denom
        vector<double> K(NUM_VARS);
        for (int i = 0; i < NUM_VARS; ++i) {
            K[i] = Pphi[i] / denom;
        }

        // 4. Calculate Prediction Error
        double pred_len = 0;
        for (int i = 0; i < NUM_VARS; ++i) {
            if (phi[i] > 0.5) {
                pred_len += phi[i] * theta[i];
            }
        }
        double error = result_len - pred_len;

        // 5. Update parameters theta
        for (int i = 0; i < NUM_VARS; ++i) {
            theta[i] += K[i] * error;
        }

        // 6. Update covariance matrix P
        for (int i = 0; i < NUM_VARS; ++i) {
            for (int j = 0; j < NUM_VARS; ++j) {
                P[i][j] -= K[i] * Pphi[j];
            }
        }
    }

    return 0;
}