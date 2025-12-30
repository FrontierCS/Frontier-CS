#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <cmath>

struct Company {
    int id;
    int x, y;
    long long r;
};

struct Rect {
    int x1, y1, x2, y2;
};

std::vector<Company> companies;
std::vector<Rect> final_rects;

void solve(int x1, int y1, int x2, int y2, std::vector<int> p_indices) {
    if (p_indices.empty()) {
        return;
    }
    if (p_indices.size() == 1) {
        final_rects[p_indices[0]] = {x1, y1, x2, y2};
        return;
    }

    long long total_r = 0;
    for (int idx : p_indices) {
        total_r += companies[idx].r;
    }

    std::vector<int> p_x = p_indices;
    std::sort(p_x.begin(), p_x.end(), [&](int a, int b){return companies[a].x < companies[b].x;});
    
    std::vector<int> p_y = p_indices;
    std::sort(p_y.begin(), p_y.end(), [&](int a, int b){return companies[a].y < companies[b].y;});
    
    bool can_split_v = (companies[p_x.front()].x < companies[p_x.back()].x);
    bool can_split_h = (companies[p_y.front()].y < companies[p_y.back()].y);
    
    bool use_v_split;
    if (can_split_v && !can_split_h) use_v_split = true;
    else if (!can_split_v && can_split_h) use_v_split = false;
    else if (!can_split_v && !can_split_h) return; // Should not happen for distinct points
    else use_v_split = (x2 - x1) >= (y2 - y1);

    p_indices = use_v_split ? p_x : p_y;

    int best_k = 0;
    long long current_r = 0;
    long long min_diff = -1;
    for (size_t i = 0; i < p_indices.size() - 1; ++i) {
        current_r += companies[p_indices[i]].r;
        if (min_diff == -1 || std::abs(total_r - 2 * current_r) < min_diff) {
            min_diff = std::abs(total_r - 2 * current_r);
            best_k = i;
        }
    }
    
    if (use_v_split) {
        if (companies[p_indices[best_k]].x >= companies[p_indices[best_k+1]].x) {
            for (size_t i = 0; i < p_indices.size() - 1; ++i) {
                if (companies[p_indices[i]].x < companies[p_indices[i+1]].x) {
                    best_k = i;
                    break;
                }
            }
        }
    } else {
        if (companies[p_indices[best_k]].y >= companies[p_indices[best_k+1]].y) {
            for (size_t i = 0; i < p_indices.size() - 1; ++i) {
                if (companies[p_indices[i]].y < companies[p_indices[i+1]].y) {
                    best_k = i;
                    break;
                }
            }
        }
    }
    
    std::vector<int> group1, group2;
    for(int i = 0; i <= best_k; ++i) group1.push_back(p_indices[i]);
    for(size_t i = best_k + 1; i < p_indices.size(); ++i) group2.push_back(p_indices[i]);

    long long r1_sum = 0;
    for (int idx : group1) r1_sum += companies[idx].r;
    
    if (use_v_split) {
        int max_x_left = companies[p_indices[best_k]].x;
        int min_x_right = companies[p_indices[best_k+1]].x;
        int x_cut = round(x1 + (double)(x2 - x1) * r1_sum / total_r);
        x_cut = std::max(x_cut, max_x_left + 1);
        x_cut = std::min(x_cut, min_x_right);
        
        solve(x1, y1, x_cut, y2, group1);
        solve(x_cut, y1, x2, y2, group2);
    } else {
        int max_y_bottom = companies[p_indices[best_k]].y;
        int min_y_top = companies[p_indices[best_k+1]].y;
        int y_cut = round(y1 + (double)(y2 - y1) * r1_sum / total_r);
        y_cut = std::max(y_cut, max_y_bottom + 1);
        y_cut = std::min(y_cut, min_y_top);
        
        solve(x1, y1, x2, y_cut, group1);
        solve(x1, y_cut, x2, y2, group2);
    }
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n;
    std::cin >> n;

    companies.resize(n);
    final_rects.resize(n);
    std::vector<int> initial_indices(n);

    for (int i = 0; i < n; ++i) {
        companies[i].id = i;
        std::cin >> companies[i].x >> companies[i].y >> companies[i].r;
        initial_indices[i] = i;
    }

    solve(0, 0, 10000, 10000, initial_indices);

    for (int i = 0; i < n; ++i) {
        std::cout << final_rects[i].x1 << " " << final_rects[i].y1 << " " << final_rects[i].x2 << " " << final_rects[i].y2 << "\n";
    }

    return 0;
}