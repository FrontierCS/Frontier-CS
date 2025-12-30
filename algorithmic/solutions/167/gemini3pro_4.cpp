#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <iomanip>

using namespace std;

struct Point {
    int x, y;
};

int N;
vector<Point> mackerels;
vector<Point> sardines;

const int W = 100000;
const int H = 100000;
const int K = 100; // X grid size
const int M = 200; // Y grid size
const int STEP_X = W / K;
const int STEP_Y = H / M;

// Precomputed potentials
// pot[i][j] = (Mackerels - Sardines) in strip i, with y < j*STEP_Y
int pot[K][M + 1]; 

struct Solution {
    double score_metric;
    long long perimeter;
    vector<pair<int, int>> vertices;
};

// DP tables
double dp_t[M + 1], dp_b[M + 1];
double new_dp_t[M + 1], new_dp_b[M + 1];
int parent_t[K][M + 1]; // parent_t[col][y] stores prev_y
int parent_b[K][M + 1];

Solution solve_for_lambda(double lambda) {
    double global_max_val = -1e18;
    int best_S = -1, best_E = -1;
    int best_end_yt = -1, best_end_yb = -1;

    // Phase 1: Find best indices
    for (int S = 0; S < K; ++S) {
        // Init DP at S
        for (int j = 0; j <= M; ++j) {
            double p = (double)pot[S][j];
            dp_t[j] = p - lambda * (j * STEP_Y) - lambda * STEP_X;
            dp_b[j] = -p + lambda * (j * STEP_Y) - lambda * STEP_X;
        }

        for (int E = S; E < K; ++E) {
            // Check closure at E
            // We want to maximize T[yt] + B[yb] such that yt > yb
            
            // Optimization: Maintain prefix max for B part
            double best_b_val = -1e18;
            int best_b_idx = -1;
            
            // Initial best B at yb=0
            if (dp_b[0] > best_b_val) {
                best_b_val = dp_b[0];
                best_b_idx = 0;
            }

            for (int yt = 1; yt <= M; ++yt) {
                // For current yt, combine with best yb < yt
                double val_t = dp_t[yt] - lambda * yt * STEP_Y;
                double total = val_t + best_b_val;
                
                if (total > global_max_val) {
                    global_max_val = total;
                    best_S = S;
                    best_E = E;
                    best_end_yt = yt;
                    best_end_yb = best_b_idx;
                }
                
                // Update best B for next iteration (yb can be yt)
                // For the next yt (which is yt+1), yb can go up to yt
                double val_b = dp_b[yt] + lambda * yt * STEP_Y;
                if (val_b > best_b_val) {
                    best_b_val = val_b;
                    best_b_idx = yt;
                }
            }

            // Transition to E+1
            if (E < K - 1) {
                int next_col = E + 1;
                
                // Forward pass for T
                double best = -1e18;
                for (int y = 0; y <= M; ++y) {
                    double val = dp_t[y] + lambda * y * STEP_Y;
                    if (val > best) best = val;
                    new_dp_t[y] = best - lambda * y * STEP_Y;
                }
                // Backward pass for T
                best = -1e18;
                for (int y = M; y >= 0; --y) {
                    double val = dp_t[y] - lambda * y * STEP_Y;
                    if (val > best) best = val;
                    new_dp_t[y] = max(new_dp_t[y], best + lambda * y * STEP_Y);
                }
                // Add common terms
                for (int y = 0; y <= M; ++y) {
                    new_dp_t[y] += (double)pot[next_col][y] - lambda * STEP_X;
                }
                
                // Forward pass for B
                best = -1e18;
                for (int y = 0; y <= M; ++y) {
                    double val = dp_b[y] + lambda * y * STEP_Y;
                    if (val > best) best = val;
                    new_dp_b[y] = best - lambda * y * STEP_Y;
                }
                // Backward pass for B
                best = -1e18;
                for (int y = M; y >= 0; --y) {
                    double val = dp_b[y] - lambda * y * STEP_Y;
                    if (val > best) best = val;
                    new_dp_b[y] = max(new_dp_b[y], best + lambda * y * STEP_Y);
                }
                // Add common terms
                for (int y = 0; y <= M; ++y) {
                    new_dp_b[y] += -(double)pot[next_col][y] - lambda * STEP_X;
                }
                
                // Copy back
                for(int y=0; y<=M; ++y) {
                    dp_t[y] = new_dp_t[y];
                    dp_b[y] = new_dp_b[y];
                }
            }
        }
    }

    Solution sol;
    sol.score_metric = global_max_val;
    if (best_S == -1) {
        sol.perimeter = 0;
        return sol;
    }

    // Phase 2: Reconstruction
    for (int j = 0; j <= M; ++j) {
        double p = (double)pot[best_S][j];
        dp_t[j] = p - lambda * (j * STEP_Y) - lambda * STEP_X;
        dp_b[j] = -p + lambda * (j * STEP_Y) - lambda * STEP_X;
        parent_t[best_S][j] = -1;
        parent_b[best_S][j] = -1;
    }

    for (int E = best_S; E < best_E; ++E) {
        int next_col = E + 1;
        
        // T reconstruction
        for (int y = 0; y <= M; ++y) {
            double best_val = -1e18;
            int best_yp = -1;
            // Limit search window for optimization if needed, but M=200 is small
            for (int yp = 0; yp <= M; ++yp) {
                double val = dp_t[yp] - lambda * abs(y - yp) * STEP_Y;
                if (val > best_val) {
                    best_val = val;
                    best_yp = yp;
                }
            }
            new_dp_t[y] = best_val + (double)pot[next_col][y] - lambda * STEP_X;
            parent_t[next_col][y] = best_yp;
        }

        // B reconstruction
        for (int y = 0; y <= M; ++y) {
            double best_val = -1e18;
            int best_yp = -1;
            for (int yp = 0; yp <= M; ++yp) {
                double val = dp_b[yp] - lambda * abs(y - yp) * STEP_Y;
                if (val > best_val) {
                    best_val = val;
                    best_yp = yp;
                }
            }
            new_dp_b[y] = best_val - (double)pot[next_col][y] - lambda * STEP_X;
            parent_b[next_col][y] = best_yp;
        }
        
        for(int y=0; y<=M; ++y) {
            dp_t[y] = new_dp_t[y];
            dp_b[y] = new_dp_b[y];
        }
    }

    // Trace back
    vector<int> path_t, path_b;
    int curr_t = best_end_yt;
    int curr_b = best_end_yb;
    
    for (int col = best_E; col > best_S; --col) {
        path_t.push_back(curr_t);
        path_b.push_back(curr_b);
        curr_t = parent_t[col][curr_t];
        curr_b = parent_b[col][curr_b];
    }
    path_t.push_back(curr_t);
    path_b.push_back(curr_b);
    
    reverse(path_t.begin(), path_t.end());
    reverse(path_b.begin(), path_b.end());
    
    // Construct vertices
    sol.vertices.push_back({best_S * STEP_X, path_b[0] * STEP_Y});
    sol.vertices.push_back({best_S * STEP_X, path_t[0] * STEP_Y});
    
    for (size_t i = 0; i < path_t.size(); ++i) {
        int y = path_t[i] * STEP_Y;
        int x_next = (best_S + i + 1) * STEP_X;
        sol.vertices.push_back({x_next, y});
        if (i < path_t.size() - 1) {
            int next_y = path_t[i+1] * STEP_Y;
            if (next_y != y) {
                sol.vertices.push_back({x_next, next_y});
            }
        }
    }
    
    sol.vertices.push_back({(best_E + 1) * STEP_X, path_b.back() * STEP_Y});
    
    for (int i = (int)path_b.size() - 1; i >= 0; --i) {
        int y = path_b[i] * STEP_Y;
        int x_prev = (best_S + i) * STEP_X;
        sol.vertices.push_back({x_prev, y});
        if (i > 0) {
            int prev_y = path_b[i-1] * STEP_Y;
            if (prev_y != y) {
                sol.vertices.push_back({x_prev, prev_y});
            }
        }
    }
    
    long long perim = 0;
    if (!sol.vertices.empty()) {
        for (size_t i = 0; i < sol.vertices.size(); ++i) {
            auto p1 = sol.vertices[i];
            auto p2 = sol.vertices[(i+1)%sol.vertices.size()];
            perim += abs(p1.first - p2.first) + abs(p1.second - p2.second);
        }
    }
    sol.perimeter = perim;
    
    // Simplify
    vector<pair<int, int>> simplified;
    if (!sol.vertices.empty()) {
        simplified.push_back(sol.vertices[0]);
        for (size_t i = 1; i < sol.vertices.size(); ++i) {
            auto& last = simplified.back();
            auto& curr = sol.vertices[i];
            bool collinear = false;
            if (simplified.size() >= 2) {
                auto& prev = simplified[simplified.size()-2];
                if ((prev.first == last.first && last.first == curr.first) || 
                    (prev.second == last.second && last.second == curr.second)) {
                    collinear = true;
                }
            }
            if (collinear) simplified.pop_back();
            simplified.push_back(curr);
        }
        if (simplified.size() >= 3) {
            auto& first = simplified[0];
            auto& last = simplified.back();
            auto& prev = simplified[simplified.size()-2];
             if ((prev.first == last.first && last.first == first.first) || 
                    (prev.second == last.second && last.second == first.second)) {
                    simplified.pop_back();
            }
        }
    }
    sol.vertices = simplified;
    
    return sol;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> N)) return 0;
    mackerels.resize(N);
    for (int i = 0; i < N; ++i) cin >> mackerels[i].x >> mackerels[i].y;
    sardines.resize(N);
    for (int i = 0; i < N; ++i) cin >> sardines[i].x >> sardines[i].y;

    for(int i=0; i<K; ++i) for(int j=0; j<=M; ++j) pot[i][j] = 0;

    for (const auto& p : mackerels) {
        int cx = min(p.x / STEP_X, K - 1);
        int cy = min(p.y / STEP_Y, M - 1);
        for (int j = cy + 1; j <= M; ++j) pot[cx][j]++;
    }
    for (const auto& p : sardines) {
        int cx = min(p.x / STEP_X, K - 1);
        int cy = min(p.y / STEP_Y, M - 1);
        for (int j = cy + 1; j <= M; ++j) pot[cx][j]--;
    }

    double L = 0.0, R = 1.0;
    Solution best_valid_sol;
    best_valid_sol.score_metric = -1e18;
    best_valid_sol.perimeter = 1e18; 
    
    Solution sol0 = solve_for_lambda(0.0);
    if (sol0.perimeter <= 400000) {
        best_valid_sol = sol0;
    } else {
        for (int iter = 0; iter < 12; ++iter) {
            double mid = (L + R) / 2.0;
            Solution s = solve_for_lambda(mid);
            if (s.perimeter <= 400000) {
                best_valid_sol = s;
                R = mid;
            } else {
                L = mid;
            }
        }
    }
    
    if (best_valid_sol.vertices.empty()) {
        cout << "4\n0 0\n1 0\n1 1\n0 1\n";
    } else {
        cout << best_valid_sol.vertices.size() << "\n";
        for (const auto& p : best_valid_sol.vertices) {
            cout << p.first << " " << p.second << "\n";
        }
    }

    return 0;
}