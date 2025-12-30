#include <iostream>
#include <vector>
#include <algorithm>
#include <cmath>
#include <chrono>
#include <random>

using namespace std;

// Constants
const int W = 10000;
const int TIME_LIMIT_MS = 4900; 

struct Point {
    int id;
    int x, y;
    int r;
};

struct Rect {
    int id;
    int a, b, c, d; // [a, c), [b, d)
    
    int area() const {
        return (c - a) * (d - b);
    }
};

int n;
vector<Point> points;
vector<Rect> solution;
vector<int> r_vals;

// Function to calculate satisfaction for a single company
double calc_satisfaction(int r, int s) {
    if (s == 0) return 0.0;
    double val = 1.0 - (double)min(r, s) / max(r, s);
    return 1.0 - val * val;
}

// Function to calculate total score (sum of satisfactions)
double calc_score(const vector<Rect>& rects) {
    double sum = 0;
    for (const auto& rect : rects) {
        int px = points[rect.id].x;
        int py = points[rect.id].y;
        if (px >= rect.a && px < rect.c && py >= rect.b && py < rect.d) {
            sum += calc_satisfaction(points[rect.id].r, rect.area());
        }
    }
    return sum;
}

// Calculate score for a single rectangle
double get_rect_score(const Rect& rect) {
    int px = points[rect.id].x;
    int py = points[rect.id].y;
    if (px >= rect.a && px < rect.c && py >= rect.b && py < rect.d) {
        return calc_satisfaction(points[rect.id].r, rect.area());
    }
    return 0.0;
}

// Check if two rectangles overlap with positive area
bool intersect(const Rect& r1, const Rect& r2) {
    return max(r1.a, r2.a) < min(r1.c, r2.c) && max(r1.b, r2.b) < min(r1.d, r2.d);
}

// Recursive function to generate initial layout based on area requirements
void divide(int x, int y, int w, int h, vector<int>& p_idxs) {
    if (p_idxs.empty()) return;
    if (p_idxs.size() == 1) {
        int idx = p_idxs[0];
        solution[idx] = {idx, x, y, x + w, y + h};
        return;
    }

    // Calculate total desired area for current points
    long long total_r = 0;
    for (int idx : p_idxs) total_r += points[idx].r;

    // Try splitting X
    vector<int> sorted_x = p_idxs;
    sort(sorted_x.begin(), sorted_x.end(), [](int i, int j) {
        return points[i].x < points[j].x;
    });

    int best_k_x = -1;
    double best_cost_x = 1e18;
    int split_x_val = -1;

    for (size_t k = 0; k < sorted_x.size() - 1; ++k) {
        long long current_r = 0;
        for (size_t i = 0; i <= k; ++i) current_r += points[sorted_x[i]].r;
        
        double ratio = (double)current_r / total_r;
        int target_w = round(w * ratio);
        int target_split = x + target_w;
        
        int min_split = points[sorted_x[k]].x + 1;
        int max_split = points[sorted_x[k+1]].x;
        
        if (min_split > max_split) continue;
        
        int actual_split = clamp(target_split, min_split, max_split);
        double cost = abs(actual_split - target_split);
        
        if (cost < best_cost_x) {
            best_cost_x = cost;
            best_k_x = k;
            split_x_val = actual_split;
        }
    }

    // Try splitting Y
    vector<int> sorted_y = p_idxs;
    sort(sorted_y.begin(), sorted_y.end(), [](int i, int j) {
        return points[i].y < points[j].y;
    });

    int best_k_y = -1;
    double best_cost_y = 1e18;
    int split_y_val = -1;

    for (size_t k = 0; k < sorted_y.size() - 1; ++k) {
        long long current_r = 0;
        for (size_t i = 0; i <= k; ++i) current_r += points[sorted_y[i]].r;
        
        double ratio = (double)current_r / total_r;
        int target_h = round(h * ratio);
        int target_split = y + target_h;
        
        int min_split = points[sorted_y[k]].y + 1;
        int max_split = points[sorted_y[k+1]].y;
        
        int actual_split = clamp(target_split, min_split, max_split);
        double cost = abs(actual_split - target_split);
        
        if (cost < best_cost_y) {
            best_cost_y = cost;
            best_k_y = k;
            split_y_val = actual_split;
        }
    }

    // Heuristic decision on split axis
    bool use_x = true;
    if (best_k_x == -1) use_x = false;
    else if (best_k_y != -1) {
        if (best_cost_y < best_cost_x) use_x = false;
        else if (best_cost_x == best_cost_y) {
            if (h > w) use_x = false; 
        }
    }

    if (use_x) {
        vector<int> left, right;
        for(size_t i=0; i<=best_k_x; ++i) left.push_back(sorted_x[i]);
        for(size_t i=best_k_x+1; i<sorted_x.size(); ++i) right.push_back(sorted_x[i]);
        divide(x, y, split_x_val - x, h, left);
        divide(split_x_val, y, x + w - split_x_val, h, right);
    } else {
        vector<int> top, bottom;
        for(size_t i=0; i<=best_k_y; ++i) top.push_back(sorted_y[i]);
        for(size_t i=best_k_y+1; i<sorted_y.size(); ++i) bottom.push_back(sorted_y[i]);
        divide(x, y, w, split_y_val - y, top);
        divide(x, split_y_val, w, y + h - split_y_val, bottom);
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    auto start_time = chrono::steady_clock::now();

    cin >> n;
    points.resize(n);
    r_vals.resize(n);
    solution.resize(n);
    vector<int> p_idxs(n);
    
    for (int i = 0; i < n; ++i) {
        cin >> points[i].x >> points[i].y >> points[i].r;
        points[i].id = i;
        r_vals[i] = points[i].r;
        p_idxs[i] = i;
    }

    // 1. Initial Solution Generation (Recursive Partitioning)
    divide(0, 0, W, W, p_idxs);

    // 2. Optimization using Simulated Annealing
    mt19937 rng(12345);
    uniform_int_distribution<int> dist_idx(0, n - 1);
    uniform_int_distribution<int> dist_dir(0, 3);
    
    double current_total_score = calc_score(solution);
    
    double t_start = 0.5;
    double t_end = 0.0;

    int iter = 0;
    while (true) {
        iter++;
        if ((iter & 1023) == 0) {
            auto now = chrono::steady_clock::now();
            double elapsed = chrono::duration<double, milli>(now - start_time).count();
            if (elapsed > TIME_LIMIT_MS) break;
        }

        auto now = chrono::steady_clock::now();
        double elapsed = chrono::duration<double, milli>(now - start_time).count();
        double ratio = elapsed / TIME_LIMIT_MS;
        if (ratio >= 1.0) break;

        double temp = t_start + (t_end - t_start) * ratio;

        int i = dist_idx(rng);
        int dir = dist_dir(rng);
        
        // Determine expansion or contraction bias
        int s = solution[i].area();
        int r = r_vals[i];
        int delta = 0;

        if (s < r) {
            // Bias towards expansion
            if (rng() % 3 != 0) delta = 1; 
            else delta = -1;
        } else {
            // Bias towards contraction
             if (rng() % 3 != 0) delta = -1; 
             else delta = 1;
        }

        Rect old_rect = solution[i];
        Rect new_rect = old_rect;
        
        // Apply move
        if (dir == 0) new_rect.a -= delta; 
        else if (dir == 1) new_rect.c += delta;
        else if (dir == 2) new_rect.b -= delta;
        else if (dir == 3) new_rect.d += delta;

        // Validity Checks
        // 1. Bounds
        if (new_rect.a < 0 || new_rect.b < 0 || new_rect.c > W || new_rect.d > W) continue;
        // 2. Positive Area
        if (new_rect.a >= new_rect.c || new_rect.b >= new_rect.d) continue;
        // 3. Contains required point
        if (points[i].x < new_rect.a || points[i].x >= new_rect.c ||
            points[i].y < new_rect.b || points[i].y >= new_rect.d) continue;

        // 4. Overlaps (only check if expanded)
        bool possible_overlap = (delta == 1);
        
        if (possible_overlap) {
            bool ok = true;
            for (int j = 0; j < n; ++j) {
                if (i == j) continue;
                if (intersect(new_rect, solution[j])) {
                    ok = false;
                    break;
                }
            }
            if (!ok) continue;
        }

        double old_p = get_rect_score(old_rect);
        double new_p = get_rect_score(new_rect);
        double diff = new_p - old_p;

        if (diff >= 0 || exp(diff / temp) > (double)(rng()%10000)/10000.0) {
            solution[i] = new_rect;
            current_total_score += diff;
        }
    }

    for (int i = 0; i < n; ++i) {
        cout << solution[i].a << " " << solution[i].b << " " << solution[i].c << " " << solution[i].d << "\n";
    }

    return 0;
}