#include <iostream>
#include <vector>
#include <algorithm>
#include <cmath>
#include <cstdlib>
#include <ctime>
#include <chrono>
#include <random>

using namespace std;

const int W = 10000;
const int H = 10000;

struct Input {
    int id;
    int x, y, r;
};

struct Rect {
    int a, b, c, d; // [a, c) x [b, d)
    
    int area() const {
        return max(0, c - a) * max(0, d - b);
    }
    
    bool contains(int x, int y) const {
        return x >= a && x < c && y >= b && y < d;
    }
    
    bool overlaps(const Rect& other) const {
        return max(a, other.a) < min(c, other.c) && max(b, other.b) < min(d, other.d);
    }
};

int n;
vector<Input> inputs;
vector<Rect> solution;

double calc_satisfaction(int idx, const Rect& r) {
    if (!r.contains(inputs[idx].x, inputs[idx].y)) return 0.0;
    int s = r.area();
    int target = inputs[idx].r;
    if (s == 0) return 0.0;
    double val = 1.0 - min(s, target) * 1.0 / max(s, target);
    return 1.0 - val * val;
}

double get_score() {
    double sum = 0;
    for (int i = 0; i < n; i++) {
        sum += calc_satisfaction(i, solution[i]);
    }
    return sum;
}

// Initial recursive partition
void partition(int x, int y, int w, int h, const vector<int>& indices) {
    if (indices.empty()) return;
    if (indices.size() == 1) {
        int idx = indices[0];
        solution[idx] = {x, y, x + w, y + h};
        return;
    }
    
    // Choose axis: cut perpendicular to the longer side
    bool split_x = (w > h);
    
    // Sort indices
    vector<int> sorted_indices = indices;
    if (split_x) {
        sort(sorted_indices.begin(), sorted_indices.end(), [&](int a, int b){
            return inputs[a].x < inputs[b].x;
        });
    } else {
        sort(sorted_indices.begin(), sorted_indices.end(), [&](int a, int b){
            return inputs[a].y < inputs[b].y;
        });
    }
    
    // Find best split point
    long long total_r = 0;
    for (int idx : indices) total_r += inputs[idx].r;
    
    long long current_r = 0;
    int best_k = -1;
    int best_cut_pos = -1;
    double min_diff = 1e18;
    
    for (size_t k = 1; k < sorted_indices.size(); k++) {
        int prev_idx = sorted_indices[k-1];
        int curr_idx = sorted_indices[k];
        current_r += inputs[prev_idx].r;
        
        // Allowed cut range
        int min_cut, max_cut;
        if (split_x) {
            min_cut = inputs[prev_idx].x + 1;
            max_cut = inputs[curr_idx].x;
        } else {
            min_cut = inputs[prev_idx].y + 1;
            max_cut = inputs[curr_idx].y;
        }
        
        // Ideal cut
        double ratio = (double)current_r / total_r;
        int size = split_x ? w : h;
        int start = split_x ? x : y;
        int ideal_cut = start + (int)(size * ratio + 0.5);
        
        int actual_cut = max(min_cut, min(max_cut, ideal_cut));
        
        // Minimize deviation from ideal position
        double diff = abs(actual_cut - ideal_cut);
        
        if (diff < min_diff) {
            min_diff = diff;
            best_k = k;
            best_cut_pos = actual_cut;
        }
    }
    
    // Perform split
    vector<int> group1(sorted_indices.begin(), sorted_indices.begin() + best_k);
    vector<int> group2(sorted_indices.begin() + best_k, sorted_indices.end());
    
    if (split_x) {
        partition(x, y, best_cut_pos - x, h, group1);
        partition(best_cut_pos, y, x + w - best_cut_pos, h, group2);
    } else {
        partition(x, y, w, best_cut_pos - y, group1);
        partition(x, best_cut_pos, w, y + h - best_cut_pos, group2);
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> n)) return 0;
    inputs.resize(n);
    vector<int> all_indices(n);
    for (int i = 0; i < n; i++) {
        inputs[i].id = i;
        cin >> inputs[i].x >> inputs[i].y >> inputs[i].r;
        all_indices[i] = i;
    }
    
    solution.resize(n);
    
    // Step 1: Initial partition
    partition(0, 0, W, H, all_indices);
    
    // Step 2: Optimization with Hill Climbing / Simulated Annealing
    auto start_time = chrono::high_resolution_clock::now();
    double time_limit = 1.90; // seconds
    
    mt19937 rng(12345);
    
    long long iter = 0;
    while (true) {
        iter++;
        // Check time every 256 iterations
        if ((iter & 255) == 0) {
            auto now = chrono::high_resolution_clock::now();
            chrono::duration<double> elapsed = now - start_time;
            if (elapsed.count() > time_limit) break;
        }
        
        // Pick a random rectangle and a random edge to move
        int i = rng() % n;
        int edge = rng() % 4; // 0: left(a), 1: bottom(b), 2: right(c), 3: top(d)
        int delta = (rng() % 2 == 0) ? 1 : -1;
        
        // Proposed new rectangle for i
        Rect old_ri = solution[i];
        Rect new_ri = old_ri;
        
        if (edge == 0) new_ri.a += delta;
        else if (edge == 1) new_ri.b += delta;
        else if (edge == 2) new_ri.c += delta;
        else if (edge == 3) new_ri.d += delta;
        
        // Basic validity checks for i
        if (new_ri.a < 0 || new_ri.b < 0 || new_ri.c > W || new_ri.d > H) continue;
        if (new_ri.a >= new_ri.c || new_ri.b >= new_ri.d) continue; 
        if (!new_ri.contains(inputs[i].x, inputs[i].y)) continue;
        
        // Determine if this is a shrink or expand operation
        // Shrink: (edge 0 or 1 with delta +1) or (edge 2 or 3 with delta -1)
        bool is_shrink = false;
        if ((edge == 0 || edge == 1) && delta == 1) is_shrink = true;
        if ((edge == 2 || edge == 3) && delta == -1) is_shrink = true;
        
        vector<int> modified_indices;
        modified_indices.push_back(i);
        vector<Rect> old_rects;
        old_rects.push_back(old_ri);
        
        bool possible = true;
        
        if (!is_shrink) {
            // Check for collisions with other rectangles
            for (int j = 0; j < n; j++) {
                if (i == j) continue;
                if (solution[j].overlaps(new_ri)) {
                    // Collision detected with j. Try to shrink j to accommodate i's expansion.
                    Rect new_rj = solution[j];
                    
                    if (edge == 0) { // i expanded left, push j's right edge
                        new_rj.c = new_ri.a;
                    } else if (edge == 1) { // i expanded down, push j's top edge
                        new_rj.d = new_ri.b;
                    } else if (edge == 2) { // i expanded right, push j's left edge
                        new_rj.a = new_ri.c;
                    } else if (edge == 3) { // i expanded up, push j's bottom edge
                        new_rj.b = new_ri.d;
                    }
                    
                    // Validate new_rj
                    if (new_rj.a >= new_rj.c || new_rj.b >= new_rj.d || !new_rj.contains(inputs[j].x, inputs[j].y)) {
                        possible = false;
                        break;
                    }
                    
                    modified_indices.push_back(j);
                    old_rects.push_back(solution[j]);
                }
            }
        }
        
        if (!possible) continue;
        
        // Calculate score change
        double old_local_score = 0;
        for (int idx : modified_indices) old_local_score += calc_satisfaction(idx, solution[idx]);
        
        // Apply changes tentatively
        solution[i] = new_ri;
        // Neighbors
        for (size_t k = 1; k < modified_indices.size(); k++) {
            int j = modified_indices[k];
            if (edge == 0) solution[j].c = new_ri.a;
            else if (edge == 1) solution[j].d = new_ri.b;
            else if (edge == 2) solution[j].a = new_ri.c;
            else if (edge == 3) solution[j].b = new_ri.d;
        }
        
        double new_local_score = 0;
        for (int idx : modified_indices) new_local_score += calc_satisfaction(idx, solution[idx]);
        
        // Accept or Reject logic
        // We use a simple acceptance criterion (Hill Climbing with small probability for bad moves)
        double diff = new_local_score - old_local_score;
        
        bool accept = false;
        if (diff >= 0) {
            accept = true;
        } else {
            // Simulated Annealing probability
            auto now = chrono::high_resolution_clock::now();
            chrono::duration<double> elapsed = now - start_time;
            double progress = elapsed.count() / time_limit;
            double T = 0.05 * (1.0 - progress); 
            if (T > 0) {
                 double prob = exp(diff / T);
                 if (prob > (rng() % 10000) / 10000.0) accept = true;
            }
        }
        
        if (!accept) {
            // Revert changes
            for (size_t k = 0; k < modified_indices.size(); k++) {
                solution[modified_indices[k]] = old_rects[k];
            }
        }
    }
    
    for (int i = 0; i < n; i++) {
        cout << solution[i].a << " " << solution[i].b << " " << solution[i].c << " " << solution[i].d << "\n";
    }

    return 0;
}