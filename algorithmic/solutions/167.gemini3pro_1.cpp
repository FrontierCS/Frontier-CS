#include <iostream>
#include <vector>
#include <algorithm>
#include <random>
#include <chrono>

using namespace std;

const int MAX_COORD = 100000;
const int N = 5000;

struct Point {
    int x, y, id;
    int type; // 1 for mackerel, -1 for sardine
};

struct Vertex {
    int x, y;
};

vector<Point> points;
chrono::high_resolution_clock::time_point start_time;

double get_time() {
    auto now = chrono::high_resolution_clock::now();
    return chrono::duration<double>(now - start_time).count();
}

mt19937 rng(12345);

int rand_int(int l, int r) {
    return uniform_int_distribution<int>(l, r)(rng);
}

struct Solution {
    vector<Vertex> polygon;
    long long score;
};

long long evaluate(const vector<Vertex>& poly) {
    if (poly.size() < 4) return 0;
    int a = 0, b = 0;
    
    int min_x = MAX_COORD, max_x = 0, min_y = MAX_COORD, max_y = 0;
    for(auto& v : poly) {
        min_x = min(min_x, v.x);
        max_x = max(max_x, v.x);
        min_y = min(min_y, v.y);
        max_y = max(max_y, v.y);
    }

    for (const auto& p : points) {
        if (p.x < min_x || p.x > max_x || p.y < min_y || p.y > max_y) continue;
        
        bool inside = false;
        int n = poly.size();
        bool on_boundary = false;
        
        for (int i = 0; i < n; i++) {
            int j = (i + 1) % n;
            int x1 = poly[i].x, y1 = poly[i].y;
            int x2 = poly[j].x, y2 = poly[j].y;
            
            if (y1 == y2) {
                if (p.y == y1 && p.x >= min(x1, x2) && p.x <= max(x1, x2)) {
                    on_boundary = true;
                    break;
                }
            } else {
                if (p.x == x1 && p.y >= min(y1, y2) && p.y <= max(y1, y2)) {
                    on_boundary = true;
                    break;
                }
                if (((y1 > p.y) != (y2 > p.y)) && (p.x < x1)) {
                    inside = !inside;
                }
            }
        }
        
        if (on_boundary || inside) {
            if (p.type == 1) a++;
            else b++;
        }
    }
    
    return max(0, a - b + 1);
}

Solution solve_dp(bool swap_xy) {
    vector<Point> current_points = points;
    if (swap_xy) {
        for(auto& p : current_points) swap(p.x, p.y);
    }
    
    int M = rand_int(50, 220); 
    int K = rand_int(40, 100); 
    
    vector<int> X_grid;
    X_grid.push_back(0);
    for (int i = 1; i < M; i++) {
        X_grid.push_back(i * 100000 / M);
    }
    X_grid.push_back(100001); 
    
    vector<int> Y_coords;
    for(const auto& p : current_points) Y_coords.push_back(p.y);
    sort(Y_coords.begin(), Y_coords.end());
    Y_coords.erase(unique(Y_coords.begin(), Y_coords.end()), Y_coords.end());
    
    vector<int> Y_grid;
    if (Y_coords.size() <= K) {
        Y_grid = Y_coords;
    } else {
        for(int i=0; i<K; i++) {
            Y_grid.push_back(Y_coords[i * Y_coords.size() / K]);
        }
    }
    Y_grid.push_back(100001);
    int real_K = Y_grid.size() - 1;
    
    sort(current_points.begin(), current_points.end(), [](const Point& a, const Point& b){
        return a.x < b.x;
    });
    
    vector<vector<int>> grid_val(M, vector<int>(real_K, 0));
    
    int p_idx = 0;
    for (int i = 0; i < M; i++) {
        int x_end = X_grid[i+1];
        while(p_idx < current_points.size() && current_points[p_idx].x < x_end) {
            int y = current_points[p_idx].y;
            auto it = upper_bound(Y_grid.begin(), Y_grid.end(), y);
            int band = distance(Y_grid.begin(), it) - 1;
            if (band >= 0 && band < real_K) {
                grid_val[i][band] += current_points[p_idx].type;
            }
            p_idx++;
        }
    }
    
    vector<vector<int>> pref(M, vector<int>(real_K + 1, 0));
    for(int i=0; i<M; i++) {
        for(int j=0; j<real_K; j++) {
            pref[i][j+1] = pref[i][j] + grid_val[i][j];
        }
    }
    
    static int dp[120][120];
    static int next_dp[120][120];
    static short parent_l[250][120][120];
    static short parent_r[250][120][120];
    
    for(int l=0; l<=real_K; ++l) 
        for(int r=0; r<=real_K; ++r) 
            dp[l][r] = -1e9;
            
    for(int l=0; l<real_K; ++l) {
        for(int r=l+1; r<=real_K; ++r) {
            dp[l][r] = pref[0][r] - pref[0][l];
            parent_l[0][l][r] = -1;
            parent_r[0][l][r] = -1;
        }
    }
    
    int best_val = -1e9;
    int best_i = -1, best_l = -1, best_r = -1;
    
    static pair<int, int> suff[120][120]; 
    static pair<int, pair<int,int>> query_table[120][120]; 

    for (int i = 1; i < M; i++) {
        for(int x=0; x<real_K; ++x) {
             int b_val = -1e9;
             int b_r = -1;
             for(int y=real_K; y>x; --y) { 
                 if (dp[x][y] > b_val) {
                     b_val = dp[x][y];
                     b_r = y;
                 }
                 suff[x][y] = {b_val, b_r};
             }
             for(int y=x; y>=0; --y) suff[x][y] = {b_val, b_r};
        }
        
        for(int y=0; y<=real_K; ++y) {
            int b_val = -1e9;
            pair<int,int> b_loc = {-1, -1};
            for(int x=0; x<real_K; ++x) { 
                if (suff[x][y].first > b_val) {
                    b_val = suff[x][y].first;
                    b_loc = {x, suff[x][y].second};
                }
                query_table[x][y] = {b_val, b_loc};
            }
        }
        
        for(int l=0; l<real_K; ++l) {
            int current_strip_score_base = pref[i][l];
            for(int r=l+1; r<=real_K; ++r) {
                int s = pref[i][r] - current_strip_score_base;
                
                int best_prev = -1e9;
                int pl = -1, pr = -1;
                
                int q_x = r-1;
                int q_y = l+1;
                if (q_x >= 0 && q_y <= real_K) {
                    auto res = query_table[q_x][q_y];
                    if (res.first > -1e8) { 
                         if (res.first > 0) { 
                             best_prev = res.first;
                             pl = res.second.first;
                             pr = res.second.second;
                         }
                    }
                }
                
                if (best_prev > 0) { 
                    next_dp[l][r] = s + best_prev;
                    parent_l[i][l][r] = pl;
                    parent_r[i][l][r] = pr;
                } else {
                    next_dp[l][r] = s;
                    parent_l[i][l][r] = -1;
                    parent_r[i][l][r] = -1;
                }
                
                if (next_dp[l][r] > best_val) {
                    best_val = next_dp[l][r];
                    best_i = i;
                    best_l = l;
                    best_r = r;
                }
            }
        }
        
        for(int l=0; l<=real_K; ++l)
            for(int r=0; r<=real_K; ++r)
                dp[l][r] = next_dp[l][r];
    }
    
    Solution sol;
    sol.score = best_val;
    if (best_i == -1) return sol; 
    
    vector<pair<int, int>> intervals;
    int curr_i = best_i;
    int curr_l = best_l;
    int curr_r = best_r;
    
    while(curr_i >= 0 && curr_l != -1) {
        intervals.push_back({curr_l, curr_r});
        int pl = parent_l[curr_i][curr_l][curr_r];
        int pr = parent_r[curr_i][curr_l][curr_r];
        curr_l = pl;
        curr_r = pr;
        curr_i--;
    }
    reverse(intervals.begin(), intervals.end());
    
    int start_strip = best_i - intervals.size() + 1;
    
    vector<Vertex> top_chain, bottom_chain;
    
    for(int k=0; k<intervals.size(); ++k) {
        int strip_idx = start_strip + k;
        int l = intervals[k].first;
        int r = intervals[k].second; 
        
        int y_min = min(Y_grid[l], 100000);
        int y_max = min(Y_grid[r], 100000); 
        
        int x_left = min(X_grid[strip_idx], 100000);
        int x_right = min(X_grid[strip_idx+1], 100000);
        
        if (k == 0) {
            bottom_chain.push_back({x_left, y_min});
            top_chain.push_back({x_left, y_max});
        } else {
            int l_prev = intervals[k-1].first;
            int r_prev = intervals[k-1].second;
            int y_min_prev = min(Y_grid[l_prev], 100000);
            int y_max_prev = min(Y_grid[r_prev], 100000);
            
            if (y_min != y_min_prev) {
                bottom_chain.push_back({x_left, y_min_prev});
                bottom_chain.push_back({x_left, y_min});
            }
            if (y_max != y_max_prev) {
                top_chain.push_back({x_left, y_max_prev});
                top_chain.push_back({x_left, y_max});
            }
        }
    }
    
    int last_idx = intervals.size() - 1;
    int l = intervals[last_idx].first;
    int r = intervals[last_idx].second;
    int y_min = min(Y_grid[l], 100000);
    int y_max = min(Y_grid[r], 100000);
    int x_right = min(X_grid[start_strip + last_idx + 1], 100000);
    
    bottom_chain.push_back({x_right, y_min});
    top_chain.push_back({x_right, y_max});
    
    vector<Vertex> final_poly;
    for(auto p : bottom_chain) {
        if (!final_poly.empty()) {
            Vertex back = final_poly.back();
            if (back.x == p.x && back.y == p.y) continue;
            if (final_poly.size() >= 2) {
                Vertex back2 = final_poly[final_poly.size()-2];
                if ((back2.x == back.x && back.x == p.x) || (back2.y == back.y && back.y == p.y)) {
                    final_poly.pop_back();
                }
            }
        }
        final_poly.push_back(p);
    }
    
    final_poly.push_back(top_chain.back()); 
    
    for(int i = top_chain.size() - 2; i >= 0; i--) {
        Vertex p = top_chain[i];
        if (!final_poly.empty()) {
            Vertex back = final_poly.back();
            if (back.x == p.x && back.y == p.y) continue;
            if (final_poly.size() >= 2) {
                Vertex back2 = final_poly[final_poly.size()-2];
                if ((back2.x == back.x && back.x == p.x) || (back2.y == back.y && back.y == p.y)) {
                    final_poly.pop_back();
                }
            }
        }
        final_poly.push_back(p);
    }
    
    if (final_poly.size() > 2) {
        Vertex back = final_poly.back();
        Vertex start = final_poly.front();
        if (back.x == start.x && back.y == start.y) final_poly.pop_back();
        if (final_poly.size() > 2) {
            Vertex back = final_poly.back();
            Vertex back2 = final_poly[final_poly.size()-2];
            Vertex start = final_poly.front();
            if ((back2.x == back.x && back.x == start.x) || (back2.y == back.y && back.y == start.y)) {
                 final_poly.pop_back();
            }
        }
    }
    
    if (swap_xy) {
        for(auto& v : final_poly) swap(v.x, v.y);
    }
    
    sol.polygon = final_poly;
    return sol;
}

int main() {
    start_time = chrono::high_resolution_clock::now();
    
    int N_in;
    if (!(cin >> N_in)) return 0;
    
    for (int i = 0; i < N; i++) {
        int x, y; cin >> x >> y;
        points.push_back({x, y, i, 1});
    }
    for (int i = 0; i < N; i++) {
        int x, y; cin >> x >> y;
        points.push_back({x, y, N+i, -1});
    }
    
    Solution best_sol;
    best_sol.score = -1;
    best_sol.polygon = {{0,0}, {1,0}, {1,1}, {0,1}};
    
    while (get_time() < 1.85) {
        bool swap_xy = rand_int(0, 1);
        Solution cand = solve_dp(swap_xy);
        
        long long len = 0;
        bool valid = true;
        if (cand.polygon.size() < 4) valid = false;
        else {
            for(size_t i=0; i<cand.polygon.size(); ++i) {
                int j = (i+1) % cand.polygon.size();
                len += abs(cand.polygon[i].x - cand.polygon[j].x) + abs(cand.polygon[i].y - cand.polygon[j].y);
            }
        }
        
        if (valid && cand.polygon.size() <= 1000 && len <= 400000) {
             long long exact_score = evaluate(cand.polygon);
             if (exact_score > best_sol.score) {
                 best_sol = cand;
                 best_sol.score = exact_score;
             }
        }
    }
    
    cout << best_sol.polygon.size() << endl;
    for(const auto& v : best_sol.polygon) {
        cout << v.x << " " << v.y << endl;
    }
    
    return 0;
}