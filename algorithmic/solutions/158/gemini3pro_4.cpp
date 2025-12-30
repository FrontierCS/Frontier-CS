#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <numeric>
#include <chrono>
#include <random>
#include <cstring>

using namespace std;

struct Point {
    int x, y;
    int id;
};

int N, K = 100;
int A[11];
vector<Point> P;

// Current state
vector<int> cut_x; // vertical lines x coordinates
vector<int> cut_y; // horizontal lines y coordinates

// counts in each grid cell
int grid_counts[105][105];
int b[11]; 

// Occupied coordinates
bool occ_x[20005];
bool occ_y[20005];
const int OFFSET = 10000;

// Helper to find interval index
int get_interval(int val, const vector<int>& cuts) {
    auto it = lower_bound(cuts.begin(), cuts.end(), val);
    return distance(cuts.begin(), it);
}

// Global score
long long compute_score() {
    long long num = 0;
    for (int d = 1; d <= 10; ++d) {
        num += min(A[d], b[d]);
    }
    return num;
}

mt19937 rng(12345);

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> N >> K)) return 0;
    for (int d = 1; d <= 10; ++d) {
        cin >> A[d];
    }
    P.resize(N);
    for (int i = 0; i < N; ++i) {
        cin >> P[i].x >> P[i].y;
        P[i].id = i;
        occ_x[P[i].x + OFFSET] = true;
        occ_y[P[i].y + OFFSET] = true;
    }

    vector<int> sorted_x_vals, sorted_y_vals;
    sorted_x_vals.reserve(N);
    sorted_y_vals.reserve(N);
    for(int i=0; i<N; ++i) {
        sorted_x_vals.push_back(P[i].x);
        sorted_y_vals.push_back(P[i].y);
    }
    sort(sorted_x_vals.begin(), sorted_x_vals.end());
    sort(sorted_y_vals.begin(), sorted_y_vals.end());

    int kx = 50;
    int ky = 50;
    
    // Initialize cuts with valid coordinates
    auto init_cuts = [&](int k, const vector<int>& sorted_vals, const bool* occ, vector<int>& cuts) {
        for(int i=0; i<k; ++i) {
            int idx = (long long)(i + 1) * N / (k + 1);
            int val = sorted_vals[min(idx, N-1)];
            // Find nearest valid
            int dist = 0;
            int valid_val = -200000;
            while(true) {
                if (val + dist <= 10000 && !occ[val + dist + OFFSET]) { valid_val = val + dist; break; }
                if (val - dist >= -10000 && !occ[val - dist + OFFSET]) { valid_val = val - dist; break; }
                dist++;
                if (dist > 20000) break; 
            }
            val = valid_val;
            
            // Ensure strictly increasing
            if (!cuts.empty() && val <= cuts.back()) {
                val = cuts.back() + 1;
                while (val <= 10000 && occ[val + OFFSET]) val++;
            }
            if (val > 10000) {
                 continue; 
            }
            cuts.push_back(val);
        }
    };

    init_cuts(kx, sorted_x_vals, occ_x, cut_x);
    init_cuts(ky, sorted_y_vals, occ_y, cut_y);

    vector<pair<int, int>> pt_cell(N);
    memset(grid_counts, 0, sizeof(grid_counts));
    memset(b, 0, sizeof(b));

    for(int i=0; i<N; ++i) {
        int cx = get_interval(P[i].x, cut_x);
        int cy = get_interval(P[i].y, cut_y);
        pt_cell[i] = {cx, cy};
        grid_counts[cx][cy]++;
    }

    for(int i=0; i<=100; ++i) {
        for(int j=0; j<=100; ++j) {
            int c = grid_counts[i][j];
            if (c >= 1 && c <= 10) b[c]++;
        }
    }

    long long current_score = compute_score();
    long long best_score = current_score;
    vector<int> best_cut_x = cut_x;
    vector<int> best_cut_y = cut_y;

    // Sorting points for fast range query
    vector<int> p_by_x(N), p_by_y(N);
    iota(p_by_x.begin(), p_by_x.end(), 0);
    sort(p_by_x.begin(), p_by_x.end(), [&](int i, int j){ return P[i].x < P[j].x; });
    iota(p_by_y.begin(), p_by_y.end(), 0);
    sort(p_by_y.begin(), p_by_y.end(), [&](int i, int j){ return P[i].y < P[j].y; });

    auto start_time = chrono::steady_clock::now();
    double time_limit = 1.85; 

    long long iter = 0;
    int old_b[11];

    while(true) {
        iter++;
        if ((iter & 511) == 0) {
            auto now = chrono::steady_clock::now();
            if (chrono::duration<double>(now - start_time).count() > time_limit) break;
        }

        bool is_x = (rng() % 2 == 0);
        vector<int>& cuts = is_x ? cut_x : cut_y;
        int sz = cuts.size();
        if (sz == 0) continue;
        int idx = rng() % sz;
        
        int old_val = cuts[idx];
        int min_val = (idx == 0) ? -10000 : cuts[idx-1] + 1;
        int max_val = (idx == sz - 1) ? 10000 : cuts[idx+1] - 1;
        
        if (min_val > max_val) continue;

        int new_val;
        if (rng() % 2) {
            new_val = uniform_int_distribution<int>(min_val, max_val)(rng);
        } else {
            int range = max_val - min_val;
            int delta = max(1, range / 20);
            new_val = old_val + uniform_int_distribution<int>(-delta, delta)(rng);
            new_val = max(min_val, min(max_val, new_val));
        }

        if (new_val == old_val) continue;
        const bool* occ = is_x ? occ_x : occ_y;
        if (occ[new_val + OFFSET]) continue;

        // Apply change
        int r_l = min(old_val, new_val);
        int r_r = max(old_val, new_val);
        
        const vector<int>& sorted_indices = is_x ? p_by_x : p_by_y;
        
        auto it_l = upper_bound(sorted_indices.begin(), sorted_indices.end(), r_l, [&](int val, int id) {
            return val < (is_x ? P[id].x : P[id].y);
        });
        auto it_r = upper_bound(sorted_indices.begin(), sorted_indices.end(), r_r, [&](int val, int id) {
            return val < (is_x ? P[id].x : P[id].y);
        });
        
        memcpy(old_b, b, sizeof(b));
        
        vector<int> affected_points;
        affected_points.reserve(distance(it_l, it_r));
        for (auto it = it_l; it != it_r; ++it) {
            affected_points.push_back(*it);
        }
        
        for (int pid : affected_points) {
            int cx = pt_cell[pid].first;
            int cy = pt_cell[pid].second;
            int old_cnt = grid_counts[cx][cy];
            
            grid_counts[cx][cy]--;
            if (old_cnt <= 10 && old_cnt >= 1) b[old_cnt]--;
            if (old_cnt-1 <= 10 && old_cnt-1 >= 1) b[old_cnt-1]++;
            
            int new_cx = cx, new_cy = cy;
            if (is_x) {
                if (new_val > old_val) new_cx = cx - 1; 
                else new_cx = cx + 1;
            } else {
                 if (new_val > old_val) new_cy = cy - 1;
                else new_cy = cy + 1;
            }
            
            pt_cell[pid] = {new_cx, new_cy};
            
            int target_cnt = grid_counts[new_cx][new_cy];
            if (target_cnt >= 1 && target_cnt <= 10) b[target_cnt]--; 
            grid_counts[new_cx][new_cy]++;
            target_cnt++;
            if (target_cnt <= 10) b[target_cnt]++;
        }
        
        long long new_score = compute_score();
        
        if (new_score >= current_score) {
             current_score = new_score;
             cuts[idx] = new_val;
             if (new_score > best_score) {
                 best_score = new_score;
                 best_cut_x = cut_x;
                 best_cut_y = cut_y;
             }
        } else {
            memcpy(b, old_b, sizeof(b));
            for (int pid : affected_points) {
                int cx = pt_cell[pid].first;
                int cy = pt_cell[pid].second;
                
                grid_counts[cx][cy]--;
                
                int old_cx = cx, old_cy = cy;
                if (is_x) {
                    if (new_val > old_val) old_cx = cx + 1; 
                    else old_cx = cx - 1; 
                } else {
                    if (new_val > old_val) old_cy = cy + 1;
                    else old_cy = cy - 1;
                }
                
                pt_cell[pid] = {old_cx, old_cy};
                grid_counts[old_cx][old_cy]++;
            }
        }
    }
    
    cout << best_cut_x.size() + best_cut_y.size() << "\n";
    for (int x : best_cut_x) {
        cout << x << " " << -1000000000 << " " << x << " " << 1000000000 << "\n";
    }
    for (int y : best_cut_y) {
        cout << -1000000000 << " " << y << " " << 1000000000 << " " << y << "\n";
    }

    return 0;
}