#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <cmath>

struct Company {
    int id;
    int x, y, r;
};

struct Rect {
    int x1, y1, x2, y2;
};

Rect solution[201];

void solve(int x1, int y1, int x2, int y2, std::vector<Company> companies);

void solve(int x1, int y1, int x2, int y2, std::vector<Company> companies) {
    if (companies.empty()) {
        return;
    }

    if (companies.size() == 1) {
        solution[companies[0].id] = {x1, y1, x2, y2};
        return;
    }

    bool can_vcut = false;
    int first_x = companies[0].x;
    for (size_t i = 1; i < companies.size(); ++i) {
        if (companies[i].x != first_x) {
            can_vcut = true;
            break;
        }
    }

    bool can_hcut = false;
    int first_y = companies[0].y;
    for (size_t i = 1; i < companies.size(); ++i) {
        if (companies[i].y != first_y) {
            can_hcut = true;
            break;
        }
    }

    bool do_vcut;
    if (can_vcut && !can_hcut) {
        do_vcut = true;
    } else if (!can_vcut && can_hcut) {
        do_vcut = false;
    } else if (!can_vcut && !can_hcut) {
        // This case should not be reached if n > 1 and all (x_i, y_i) are distinct.
        // As a safeguard, just assign a minimal area to each, which is likely not optimal.
        solution[companies[0].id] = {x1, y1, x2, y2};
        for (size_t i = 1; i < companies.size(); ++i) {
            solution[companies[i].id] = {companies[i].x, companies[i].y, companies[i].x + 1, companies[i].y + 1};
        }
        return;
    } else {
        if (x2 - x1 >= y2 - y1) {
            do_vcut = true;
        } else {
            do_vcut = false;
        }
    }

    if (do_vcut) {
        std::sort(companies.begin(), companies.end(), [](const Company& a, const Company& b) {
            if (a.x != b.x) return a.x < b.x;
            return a.y < b.y;
        });

        long long total_r = 0;
        for (const auto& c : companies) {
            total_r += c.r;
        }

        int best_k = -1;
        int best_x_split = -1;
        double min_score = 1e18;

        long long s1 = 0;
        for (size_t k = 0; k < companies.size() - 1; ++k) {
            s1 += companies[k].r;
            if (companies[k].x < companies[k+1].x) {
                double x_target = (double)x1 + (double)(x2 - x1) * s1 / total_r;
                
                int low = companies[k].x + 1;
                int high = companies[k+1].x;
                
                if (low > high) continue;

                int x_act = round(x_target);
                if (x_act < low) x_act = low;
                if (x_act > high) x_act = high;
                
                double score = std::abs(x_act - x_target);
                if (score < min_score) {
                    min_score = score;
                    best_k = k;
                    best_x_split = x_act;
                }
            }
        }
        
        std::vector<Company> group1, group2;
        for (size_t i = 0; i <= (size_t)best_k; ++i) group1.push_back(companies[i]);
        for (size_t i = best_k + 1; i < companies.size(); ++i) group2.push_back(companies[i]);

        solve(x1, y1, best_x_split, y2, group1);
        solve(best_x_split, y1, x2, y2, group2);

    } else { // Horizontal cut
        std::sort(companies.begin(), companies.end(), [](const Company& a, const Company& b) {
            if (a.y != b.y) return a.y < b.y;
            return a.x < b.x;
        });
        
        long long total_r = 0;
        for (const auto& c : companies) {
            total_r += c.r;
        }

        int best_k = -1;
        int best_y_split = -1;
        double min_score = 1e18;

        long long s1 = 0;
        for (size_t k = 0; k < companies.size() - 1; ++k) {
            s1 += companies[k].r;
            if (companies[k].y < companies[k+1].y) {
                double y_target = (double)y1 + (double)(y2 - y1) * s1 / total_r;
                
                int low = companies[k].y + 1;
                int high = companies[k+1].y;

                if (low > high) continue;

                int y_act = round(y_target);
                if (y_act < low) y_act = low;
                if (y_act > high) y_act = high;
                
                double score = std::abs(y_act - y_target);
                if (score < min_score) {
                    min_score = score;
                    best_k = k;
                    best_y_split = y_act;
                }
            }
        }
        
        std::vector<Company> group1, group2;
        for (size_t i = 0; i <= (size_t)best_k; ++i) group1.push_back(companies[i]);
        for (size_t i = best_k + 1; i < companies.size(); ++i) group2.push_back(companies[i]);

        solve(x1, y1, x2, best_y_split, group1);
        solve(x1, best_y_split, x2, y2, group2);
    }
}


int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    int n;
    std::cin >> n;
    std::vector<Company> companies(n);
    for (int i = 0; i < n; ++i) {
        companies[i].id = i;
        std::cin >> companies[i].x >> companies[i].y >> companies[i].r;
    }

    solve(0, 0, 10000, 10000, companies);

    for (int i = 0; i < n; ++i) {
        std::cout << solution[i].x1 << " " << solution[i].y1 << " " << solution[i].x2 << " " << solution[i].y2 << "\n";
    }

    return 0;
}