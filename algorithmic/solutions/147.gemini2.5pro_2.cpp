#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <cmath>

struct Ad {
    int id;
    int x, y;
    long long r;
};

struct Result {
    int a, b, c, d;
};

std::vector<Ad> ads;
std::vector<Result> results;

void solve(int start_idx, int end_idx, int a, int b, int c, int d) {
    if (start_idx >= end_idx) {
        return;
    }

    if (end_idx - start_idx == 1) {
        results[ads[start_idx].id] = {a, b, c, d};
        return;
    }

    int n_pts = end_idx - start_idx;
    
    int width = c - a;
    int height = d - b;

    bool prefer_v_split = (width >= height);

    if (prefer_v_split) {
        std::sort(ads.begin() + start_idx, ads.begin() + end_idx, [](const Ad& p1, const Ad& p2) {
            return p1.x < p2.x;
        });
        
        std::vector<long long> prefix_r(n_pts + 1, 0);
        for(int i = 0; i < n_pts; ++i) {
            prefix_r[i+1] = prefix_r[i] + ads[start_idx + i].r;
        }
        long long total_r = prefix_r.back();

        int best_k_idx = -1;
        long long min_diff = -1;

        for (int k = 1; k < n_pts; ++k) {
            if (ads[start_idx + k - 1].x < ads[start_idx + k].x) {
                long long left_r = prefix_r[k];
                long long diff = std::abs(left_r - (total_r - left_r));
                if (best_k_idx == -1 || diff < min_diff) {
                    min_diff = diff;
                    best_k_idx = k;
                }
            }
        }
        
        if (best_k_idx != -1) {
            int best_k = start_idx + best_k_idx;
            long long left_r = prefix_r[best_k_idx];
            int ideal_cut_x = a + static_cast<int>(round((double)width * left_r / total_r));
            int cut_x = std::max(ads[best_k - 1].x + 1, std::min(ads[best_k].x, ideal_cut_x));
            cut_x = std::max(a + 1, std::min(c - 1, cut_x));

            solve(start_idx, best_k, a, b, cut_x, d);
            solve(best_k, end_idx, cut_x, b, c, d);
            return;
        }
    }
    
    // Fallback to horizontal or preferred horizontal
    std::sort(ads.begin() + start_idx, ads.begin() + end_idx, [](const Ad& p1, const Ad& p2) {
        return p1.y < p2.y;
    });

    std::vector<long long> prefix_r(n_pts + 1, 0);
    for(int i = 0; i < n_pts; ++i) {
        prefix_r[i+1] = prefix_r[i] + ads[start_idx + i].r;
    }
    long long total_r = prefix_r.back();

    int best_k_idx = -1;
    long long min_diff = -1;
    
    for (int k = 1; k < n_pts; ++k) {
        if (ads[start_idx + k - 1].y < ads[start_idx + k].y) {
            long long bottom_r = prefix_r[k];
            long long diff = std::abs(bottom_r - (total_r - bottom_r));
            if (best_k_idx == -1 || diff < min_diff) {
                min_diff = diff;
                best_k_idx = k;
            }
        }
    }

    if (best_k_idx != -1) {
        int best_k = start_idx + best_k_idx;
        long long bottom_r = prefix_r[best_k_idx];
        int ideal_cut_y = b + static_cast<int>(round((double)height * bottom_r / total_r));
        int cut_y = std::max(ads[best_k - 1].y + 1, std::min(ads[best_k].y, ideal_cut_y));
        cut_y = std::max(b + 1, std::min(d - 1, cut_y));
        
        solve(start_idx, best_k, a, b, c, cut_y);
        solve(best_k, end_idx, a, cut_y, c, d);
        return;
    }
    
    results[ads[start_idx].id] = {a, b, c, d};
    for(int i = start_idx + 1; i < end_idx; ++i) {
        results[ads[i].id] = {ads[i].x, ads[i].y, ads[i].x + 1, ads[i].y + 1};
    }
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n;
    std::cin >> n;

    ads.resize(n);
    results.resize(n);

    for (int i = 0; i < n; ++i) {
        ads[i].id = i;
        std::cin >> ads[i].x >> ads[i].y >> ads[i].r;
    }

    solve(0, n, 0, 0, 10000, 10000);

    for (int i = 0; i < n; ++i) {
        std::cout << results[i].a << " " << results[i].b << " " << results[i].c << " " << results[i].d << "\n";
    }

    return 0;
}