#include <iostream>
#include <vector>
#include <algorithm>
#include <cmath>

using namespace std;

// Global constants
const int MAX_COORD = 100000;
const int GRID_K = 200; // Number of vertical strips
const int GRID_L = 200; // Number of horizontal levels
const int STEP_X = MAX_COORD / GRID_K; // 500
const int STEP_Y = MAX_COORD / GRID_L; // 500

struct Point {
    int x, y, id;
};

struct Solution {
    long long score;
    vector<pair<int, int>> vertices;
};

int N;
vector<Point> mackerels;
vector<Point> sardines;
int grid[GRID_K][GRID_L];
int prefix_sum[GRID_K][GRID_L + 1];

// DP tables (using double for values to handle lambda * distance)
double dp_up_d[GRID_K][GRID_L + 1];
int par_up[GRID_K][GRID_L + 1];
double dp_down_d[GRID_K][GRID_L + 1];
int par_down[GRID_K][GRID_L + 1];

// Function to compute DP transition for one column
// Maximizes dp_prev[k] - lambda * |j - k| * STEP_Y
void compute_transition(double* dp_curr, int* par_curr, double* dp_prev, double lambda) {
    double cost_step = lambda * STEP_Y;
    
    // Pass 1: k <= j. value = dp_prev[k] + k * cost_step - j * cost_step
    double best_val = -1e18;
    int best_k = -1;
    
    for (int j = 0; j <= GRID_L; ++j) {
        double val = dp_prev[j] + j * cost_step;
        if (val > best_val) {
            best_val = val;
            best_k = j;
        }
        dp_curr[j] = best_val - j * cost_step;
        par_curr[j] = best_k;
    }
    
    // Pass 2: k > j. value = dp_prev[k] - k * cost_step + j * cost_step
    best_val = -1e18;
    best_k = -1;
    for (int j = GRID_L; j >= 0; --j) {
        double val = dp_prev[j] - j * cost_step;
        if (val > best_val) {
            best_val = val;
            best_k = j;
        }
        double candidate = best_val + j * cost_step;
        // If this path is better, update
        if (candidate > dp_curr[j]) {
             dp_curr[j] = candidate;
             par_curr[j] = best_k;
        }
    }
}

long long polygon_perimeter(const vector<pair<int, int>>& poly) {
    long long p = 0;
    if (poly.empty()) return 0;
    for (size_t i = 0; i < poly.size(); ++i) {
        size_t j = (i + 1) % poly.size();
        p += abs(poly[i].first - poly[j].first) + abs(poly[i].second - poly[j].second);
    }
    return p;
}

long long calculate_exact_score(const vector<pair<int, int>>& polygon, const vector<Point>& macks, const vector<Point>& sards) {
    if (polygon.size() < 4) return 0;
    
    int min_x = MAX_COORD, max_x = 0, min_y = MAX_COORD, max_y = 0;
    for (auto& p : polygon) {
        if (p.first < min_x) min_x = p.first;
        if (p.first > max_x) max_x = p.first;
        if (p.second < min_y) min_y = p.second;
        if (p.second > max_y) max_y = p.second;
    }

    auto count_inside = [&](const vector<Point>& points) {
        int count = 0;
        for (const auto& pt : points) {
            if (pt.x < min_x || pt.x > max_x || pt.y < min_y || pt.y > max_y) continue;
            
            bool on_boundary = false;
            size_t j = polygon.size() - 1;
            // Check boundary first
            for (size_t i = 0; i < polygon.size(); i++) {
                 // Vertical segment
                if (pt.x == polygon[i].first && pt.x == polygon[j].first) {
                     if (pt.y >= min(polygon[i].second, polygon[j].second) && pt.y <= max(polygon[i].second, polygon[j].second)) {
                         on_boundary = true; break;
                     }
                }
                // Horizontal segment
                if (pt.y == polygon[i].second && pt.y == polygon[j].second) {
                     if (pt.x >= min(polygon[i].first, polygon[j].first) && pt.x <= max(polygon[i].first, polygon[j].first)) {
                         on_boundary = true; break;
                     }
                }
                j = i;
            }
            
            if (on_boundary) {
                count++;
                continue;
            }

            // Ray casting
            bool inside = false;
            j = polygon.size() - 1;
            for (size_t i = 0; i < polygon.size(); i++) {
                if ( (polygon[i].second > pt.y) != (polygon[j].second > pt.y) &&
                     (pt.x < (polygon[j].first - polygon[i].first) * (double)(pt.y - polygon[i].second) / (polygon[j].second - polygon[i].second) + polygon[i].first) ) {
                    inside = !inside;
                }
                j = i;
            }
            if (inside) count++;
        }
        return count;
    };
    
    int m_in = count_inside(macks);
    int s_in = count_inside(sards);
    
    return max(0LL, (long long)m_in - s_in + 1);
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> N)) return 0;

    mackerels.resize(N);
    for (int i = 0; i < N; ++i) {
        cin >> mackerels[i].x >> mackerels[i].y;
        mackerels[i].id = i;
    }

    sardines.resize(N);
    for (int i = 0; i < N; ++i) {
        cin >> sardines[i].x >> sardines[i].y;
        sardines[i].id = i;
    }

    // Initialize grid
    for (int i = 0; i < GRID_K; ++i) {
        for (int j = 0; j < GRID_L; ++j) {
            grid[i][j] = 0;
        }
    }

    for (const auto& p : mackerels) {
        int gx = min(p.x / STEP_X, GRID_K - 1);
        int gy = min(p.y / STEP_Y, GRID_L - 1);
        grid[gx][gy]++;
    }
    for (const auto& p : sardines) {
        int gx = min(p.x / STEP_X, GRID_K - 1);
        int gy = min(p.y / STEP_Y, GRID_L - 1);
        grid[gx][gy]--;
    }

    for (int i = 0; i < GRID_K; ++i) {
        prefix_sum[i][0] = 0;
        for (int j = 0; j < GRID_L; ++j) {
            prefix_sum[i][j + 1] = prefix_sum[i][j] + grid[i][j];
        }
    }

    vector<double> lambdas = {0.1, 0.5, 1.0, 2.0, 3.0, 5.0, 7.5, 10.0, 15.0, 25.0};
    Solution best_sol = {-1, {}};
    
    auto add_vertex = [](vector<pair<int, int>>& pts, int x, int y) {
        if (!pts.empty()) {
            if (pts.back().first == x && pts.back().second == y) return;
            if (pts.size() >= 2) {
                auto& p1 = pts[pts.size() - 2];
                auto& p2 = pts.back();
                // Check if p2 is between p1 and new point (collinear horizontal or vertical)
                if ((p1.first == p2.first && p2.first == x) || (p1.second == p2.second && p2.second == y)) {
                    pts.pop_back();
                }
            }
        }
        pts.push_back({x, y});
    };

    for (double lambda : lambdas) {
        // Init DP for first column
        for (int j = 0; j <= GRID_L; ++j) {
            dp_up_d[0][j] = prefix_sum[0][j]; 
            dp_down_d[0][j] = -prefix_sum[0][j];
        }

        for (int i = 1; i < GRID_K; ++i) {
            compute_transition(dp_up_d[i], par_up[i], dp_up_d[i-1], lambda);
            compute_transition(dp_down_d[i], par_down[i], dp_down_d[i-1], lambda);
            
            for (int j = 0; j <= GRID_L; ++j) {
                dp_up_d[i][j] += prefix_sum[i][j];
                dp_down_d[i][j] += -prefix_sum[i][j];
            }
        }

        // Try ending at every column to catch best partial solution
        // Traceback from every column i, and evaluate valid intervals
        
        // Optimization: only process 'i' that looks promising or simply all (K=200 is small)
        for (int end_i = 0; end_i < GRID_K; ++end_i) {
             // Find best endpoints at this column
             double best_u_val = -1e18, best_d_val = -1e18;
             int curr_u = -1, curr_d = -1;
             
             for(int j=0; j<=GRID_L; ++j) {
                 if(dp_up_d[end_i][j] > best_u_val) { best_u_val = dp_up_d[end_i][j]; curr_u = j; }
                 if(dp_down_d[end_i][j] > best_d_val) { best_d_val = dp_down_d[end_i][j]; curr_d = j; }
             }
             
             // Trace back
             vector<int> path_u, path_d;
             int u = curr_u, d = curr_d;
             for (int k = end_i; k >= 0; --k) {
                 path_u.push_back(u);
                 path_d.push_back(d);
                 if (k > 0) {
                     u = par_up[k][u];
                     d = par_down[k][d];
                 }
             }
             reverse(path_u.begin(), path_u.end());
             reverse(path_d.begin(), path_d.end());
             
             // Identify intervals where u > d
             int start_idx = -1;
             for (int k = 0; k <= end_i; ++k) {
                 if (path_u[k] > path_d[k]) {
                     if (start_idx == -1) start_idx = k;
                 } else {
                     if (start_idx != -1) {
                         // Process interval [start_idx, k-1]
                         int L = start_idx, R = k - 1;
                         vector<pair<int, int>> poly;
                         add_vertex(poly, L * STEP_X, path_d[L] * STEP_Y);
                         for (int p = L; p <= R; ++p) {
                             add_vertex(poly, p * STEP_X, path_d[p] * STEP_Y);
                             add_vertex(poly, (p + 1) * STEP_X, path_d[p] * STEP_Y);
                         }
                         for (int p = R; p >= L; --p) {
                             add_vertex(poly, (p + 1) * STEP_X, path_u[p] * STEP_Y);
                             add_vertex(poly, p * STEP_X, path_u[p] * STEP_Y);
                         }
                         if (poly.size() > 1 && poly.back() == poly.front()) poly.pop_back();
                         
                         if (poly.size() <= 1000 && polygon_perimeter(poly) <= 400000) {
                             long long sc = calculate_exact_score(poly, mackerels, sardines);
                             if (sc > best_sol.score) {
                                 best_sol.score = sc;
                                 best_sol.vertices = poly;
                             }
                         }
                         start_idx = -1;
                     }
                 }
             }
             if (start_idx != -1) {
                 int L = start_idx, R = end_i;
                 vector<pair<int, int>> poly;
                 add_vertex(poly, L * STEP_X, path_d[L] * STEP_Y);
                 for (int p = L; p <= R; ++p) {
                     add_vertex(poly, p * STEP_X, path_d[p] * STEP_Y);
                     add_vertex(poly, (p + 1) * STEP_X, path_d[p] * STEP_Y);
                 }
                 for (int p = R; p >= L; --p) {
                     add_vertex(poly, (p + 1) * STEP_X, path_u[p] * STEP_Y);
                     add_vertex(poly, p * STEP_X, path_u[p] * STEP_Y);
                 }
                 if (poly.size() > 1 && poly.back() == poly.front()) poly.pop_back();

                 if (poly.size() <= 1000 && polygon_perimeter(poly) <= 400000) {
                     long long sc = calculate_exact_score(poly, mackerels, sardines);
                     if (sc > best_sol.score) {
                         best_sol.score = sc;
                         best_sol.vertices = poly;
                     }
                 }
             }
        }
    }
    
    if (best_sol.vertices.empty()) {
        best_sol.vertices = {{0,0}, {1,0}, {1,1}, {0,1}};
    }
    
    cout << best_sol.vertices.size() << "\n";
    for (auto& p : best_sol.vertices) {
        cout << p.first << " " << p.second << "\n";
    }

    return 0;
}