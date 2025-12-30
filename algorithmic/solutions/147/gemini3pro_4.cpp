/*
    Competitive Programming Solution
    Problem: AtCoder Heuristic Contest 001
    Author: Assistant
*/
#include <iostream>
#include <vector>
#include <algorithm>
#include <cmath>
#include <random>
#include <chrono>

using namespace std;

// Constants
const int W = 10000;
const int H = 10000;

struct Point {
    int id;
    int x, y;
    int r;
};

struct Rect {
    int x1, y1, x2, y2; // [x1, x2), [y1, y2)
    int area() const {
        return (x2 - x1) * (y2 - y1);
    }
};

int n;
vector<Point> requests;
vector<Rect> ans;
double current_score_sum = 0;

// Score function for a single company
double calc_score(int i, int area) {
    int target = requests[i].r;
    if (area == 0) return 0.0;
    // Formula: 1 - (1 - min(r,s)/max(r,s))^2
    double ratio = (double)min(target, area) / max(target, area);
    return 1.0 - (1.0 - ratio) * (1.0 - ratio);
}

// Recursive function to generate initial layout
void divide_space(int x1, int y1, int x2, int y2, const vector<int>& indices) {
    if (indices.empty()) return;
    if (indices.size() == 1) {
        ans[indices[0]] = {x1, y1, x2, y2};
        return;
    }

    // Total required area for points in this region
    long long total_r = 0;
    for (int idx : indices) total_r += requests[idx].r;

    // We will select the best cut (horizontal or vertical) that minimizes deviation from target area proportions
    
    // Sort by X for vertical cut attempts
    vector<int> sorted_x = indices;
    sort(sorted_x.begin(), sorted_x.end(), [](int a, int b) {
        return requests[a].x < requests[b].x;
    });

    // Sort by Y for horizontal cut attempts
    vector<int> sorted_y = indices;
    sort(sorted_y.begin(), sorted_y.end(), [](int a, int b) {
        return requests[a].y < requests[b].y;
    });

    double best_cost = 1e18;
    int best_axis = -1; // 0 for X, 1 for Y
    int best_split_idx = -1; // Index in the sorted vector after which we split
    int best_cut_coord = -1;

    // Evaluate cuts along X (Vertical lines)
    long long current_r = 0;
    for (int i = 0; i < (int)sorted_x.size() - 1; ++i) {
        current_r += requests[sorted_x[i]].r;
        
        // The split line must be > requests[sorted_x[i]].x and <= requests[sorted_x[i+1]].x
        // Since coordinates are integers, the line coordinate C separates x < C and x >= C.
        // So C must be in (x_i, x_{i+1}]. Range of integers: [x_i + 1, x_{i+1}].
        
        int min_cut = requests[sorted_x[i]].x + 1;
        int max_cut = requests[sorted_x[i+1]].x;
        
        if (min_cut > max_cut) continue; // No valid integer cut possible

        // Target split position based on area ratio
        double ratio_target = (double)current_r / total_r;
        double target_width = (double)(x2 - x1) * ratio_target;
        int ideal_cut = x1 + (int)round(target_width);
        
        // Clamp to valid range
        int cut = max(min_cut, min(max_cut, ideal_cut));

        double ratio_actual = (double)(cut - x1) / (x2 - x1);
        double cost = (ratio_actual - ratio_target) * (ratio_actual - ratio_target);

        if (cost < best_cost) {
            best_cost = cost;
            best_axis = 0;
            best_split_idx = i;
            best_cut_coord = cut;
        }
    }

    // Evaluate cuts along Y (Horizontal lines)
    current_r = 0;
    for (int i = 0; i < (int)sorted_y.size() - 1; ++i) {
        current_r += requests[sorted_y[i]].r;
        
        int min_cut = requests[sorted_y[i]].y + 1;
        int max_cut = requests[sorted_y[i+1]].y;
        
        if (min_cut > max_cut) continue;

        double ratio_target = (double)current_r / total_r;
        double target_height = (double)(y2 - y1) * ratio_target;
        int ideal_cut = y1 + (int)round(target_height);
        
        int cut = max(min_cut, min(max_cut, ideal_cut));

        double ratio_actual = (double)(cut - y1) / (y2 - y1);
        double cost = (ratio_actual - ratio_target) * (ratio_actual - ratio_target);

        if (cost < best_cost) {
            best_cost = cost;
            best_axis = 1;
            best_split_idx = i;
            best_cut_coord = cut;
        }
    }

    // Perform split
    if (best_axis == -1) {
        // Fallback: This theoretically shouldn't happen if coordinates are distinct
        return; 
    }

    vector<int> group1, group2;
    if (best_axis == 0) {
        for (int i = 0; i <= best_split_idx; ++i) group1.push_back(sorted_x[i]);
        for (int i = best_split_idx + 1; i < (int)sorted_x.size(); ++i) group2.push_back(sorted_x[i]);
        divide_space(x1, y1, best_cut_coord, y2, group1);
        divide_space(best_cut_coord, y1, x2, y2, group2);
    } else {
        for (int i = 0; i <= best_split_idx; ++i) group1.push_back(sorted_y[i]);
        for (int i = best_split_idx + 1; i < (int)sorted_y.size(); ++i) group2.push_back(sorted_y[i]);
        divide_space(x1, y1, x2, best_cut_coord, group1);
        divide_space(x1, best_cut_coord, x2, y2, group2);
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    cin >> n;
    requests.resize(n);
    ans.resize(n);
    vector<int> indices(n);
    for (int i = 0; i < n; ++i) {
        cin >> requests[i].x >> requests[i].y >> requests[i].r;
        requests[i].id = i;
        indices[i] = i;
    }

    // 1. Initial Solution Construction using Recursive Partitioning
    divide_space(0, 0, W, H, indices);

    // Calculate initial score
    for (int i = 0; i < n; ++i) {
        current_score_sum += calc_score(i, ans[i].area());
    }

    // 2. Optimization using Simulated Annealing / Hill Climbing
    auto start_time = chrono::high_resolution_clock::now();
    double time_limit = 4.85; 
    
    mt19937 rng(12345);
    uniform_int_distribution<int> dist_idx(0, n - 1);
    uniform_int_distribution<int> dist_dir(0, 3);
    uniform_real_distribution<double> dist_prob(0.0, 1.0);

    double temp_start = 0.5;
    double temp_end = 1e-6;
    double temp = temp_start;

    int iter = 0;
    while (true) {
        iter++;
        if ((iter & 511) == 0) {
            auto now = chrono::high_resolution_clock::now();
            chrono::duration<double> diff = now - start_time;
            if (diff.count() > time_limit) break;
            
            double progress = diff.count() / time_limit;
            temp = temp_start * (1.0 - progress) + temp_end * progress;
        }

        int i = dist_idx(rng);
        int dir = dist_dir(rng); // 0: Left, 1: Right, 2: Up, 3: Down
        
        Rect old_rect = ans[i];
        Rect new_rect = old_rect;
        
        // Decide whether to expand or shrink
        // Mix strategies: 
        // A) Expand to max valid limit (or random subset)
        // B) Shrink by random amount
        
        bool try_expand = (dist_prob(rng) < 0.5);

        if (try_expand) {
            int max_dist = 0;
            if (dir == 0) { // Expand Left (x1 decreases)
                max_dist = old_rect.x1; 
                for (int j = 0; j < n; ++j) {
                    if (i == j) continue;
                    // Check if y-range overlaps
                    if (max(old_rect.y1, ans[j].y1) < min(old_rect.y2, ans[j].y2)) {
                        if (ans[j].x2 <= old_rect.x1) {
                            max_dist = min(max_dist, old_rect.x1 - ans[j].x2);
                        }
                    }
                }
            } else if (dir == 1) { // Expand Right (x2 increases)
                max_dist = W - old_rect.x2;
                for (int j = 0; j < n; ++j) {
                    if (i == j) continue;
                    if (max(old_rect.y1, ans[j].y1) < min(old_rect.y2, ans[j].y2)) {
                        if (ans[j].x1 >= old_rect.x2) {
                            max_dist = min(max_dist, ans[j].x1 - old_rect.x2);
                        }
                    }
                }
            } else if (dir == 2) { // Expand Up (y1 decreases)
                max_dist = old_rect.y1;
                for (int j = 0; j < n; ++j) {
                    if (i == j) continue;
                    if (max(old_rect.x1, ans[j].x1) < min(old_rect.x2, ans[j].x2)) {
                        if (ans[j].y2 <= old_rect.y1) {
                            max_dist = min(max_dist, old_rect.y1 - ans[j].y2);
                        }
                    }
                }
            } else { // Expand Down (y2 increases)
                max_dist = H - old_rect.y2;
                for (int j = 0; j < n; ++j) {
                    if (i == j) continue;
                    if (max(old_rect.x1, ans[j].x1) < min(old_rect.x2, ans[j].x2)) {
                        if (ans[j].y1 >= old_rect.y2) {
                            max_dist = min(max_dist, ans[j].y1 - old_rect.y2);
                        }
                    }
                }
            }

            if (max_dist > 0) {
                // Try moving a random amount within max_dist
                // Often moving 1 is good for gradient, but larger moves help jump gaps
                int move = 1;
                if (max_dist > 1 && dist_prob(rng) < 0.3) {
                     move = 1 + (rng() % max_dist);
                }
                
                if (dir == 0) new_rect.x1 -= move;
                else if (dir == 1) new_rect.x2 += move;
                else if (dir == 2) new_rect.y1 -= move;
                else new_rect.y2 += move;
            } else {
                continue;
            }
        } else {
            // Shrink
            // Must contain point
            int px = requests[i].x;
            int py = requests[i].y;
            
            if (dir == 0) { // Shrink Left side (x1 increases)
                int limit = px - old_rect.x1;
                if (limit <= 0) continue;
                int move = 1;
                if (limit > 1 && dist_prob(rng) < 0.2) move = 1 + (rng() % limit);
                new_rect.x1 += move;
            } else if (dir == 1) { // Shrink Right side (x2 decreases)
                int limit = old_rect.x2 - (px + 1);
                if (limit <= 0) continue;
                int move = 1;
                if (limit > 1 && dist_prob(rng) < 0.2) move = 1 + (rng() % limit);
                new_rect.x2 -= move;
            } else if (dir == 2) { // Shrink Top side (y1 increases)
                int limit = py - old_rect.y1;
                if (limit <= 0) continue;
                int move = 1;
                if (limit > 1 && dist_prob(rng) < 0.2) move = 1 + (rng() % limit);
                new_rect.y1 += move;
            } else { // Shrink Bottom side (y2 decreases)
                int limit = old_rect.y2 - (py + 1);
                if (limit <= 0) continue;
                int move = 1;
                if (limit > 1 && dist_prob(rng) < 0.2) move = 1 + (rng() % limit);
                new_rect.y2 -= move;
            }
        }

        double old_val = calc_score(i, old_rect.area());
        double new_val = calc_score(i, new_rect.area());
        double delta = new_val - old_val;

        if (delta >= 0 || dist_prob(rng) < exp(delta / temp)) {
            ans[i] = new_rect;
            current_score_sum += delta;
        }
    }

    // Output
    for (int i = 0; i < n; ++i) {
        cout << ans[i].x1 << " " << ans[i].y1 << " " << ans[i].x2 << " " << ans[i].y2 << "\n";
    }

    return 0;
}