#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <cmath>

struct Rect {
    int x1, y1, x2, y2;
};

struct Company {
    int id;
    int x, y;
    long long r;
    Rect rect;
    long long s;
};

double calculate_satisfaction(long long s, long long r) {
    if (s == 0) return 0;
    double ratio = std::min((double)r, (double)s) / std::max((double)r, (double)s);
    return 1.0 - (1.0 - ratio) * (1.0 - ratio);
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
        companies[i].rect.x1 = companies[i].x;
        companies[i].rect.y1 = companies[i].y;
        companies[i].rect.x2 = companies[i].x + 1;
        companies[i].rect.y2 = companies[i].y + 1;
        companies[i].s = 1;
    }

    // Phase 1: Proportional growth
    int n1_iterations = 40000;
    std::vector<bool> stuck(n, false);
    int stuck_count = 0;

    for (int iter = 0; iter < n1_iterations && stuck_count < n; ++iter) {
        int best_i = -1;
        double max_prio = -1.0;

        for (int i = 0; i < n; ++i) {
            if (stuck[i] || companies[i].s >= companies[i].r) {
                continue;
            }
            double prio = (double)companies[i].r / companies[i].s;
            if (prio > max_prio) {
                max_prio = prio;
                best_i = i;
            }
        }

        if (best_i == -1) {
            break;
        }

        int current_best_i = best_i;
        int best_dir = -1;
        long long max_gain = 0;

        long long width = companies[current_best_i].rect.x2 - companies[current_best_i].rect.x1;
        long long height = companies[current_best_i].rect.y2 - companies[current_best_i].rect.y1;

        // UP
        if (width > 0) {
            int limit = 10000;
            for (int j = 0; j < n; ++j) if (current_best_i != j) if (companies[j].rect.x1 < companies[current_best_i].rect.x2 && companies[j].rect.x2 > companies[current_best_i].rect.x1 && companies[j].rect.y1 >= companies[current_best_i].rect.y2) limit = std::min(limit, companies[j].rect.y1);
            long long max_expand = limit - companies[current_best_i].rect.y2;
            if (max_expand > 0) {
                 long long need_expand = (companies[current_best_i].r - companies[current_best_i].s) / width;
                 long long expand = std::min(max_expand, need_expand);
                 if (expand > 0) { long long gain = expand * width; if (gain > max_gain) { max_gain = gain; best_dir = 0; } }
            }
        }
        // DOWN
        if (width > 0) {
            int limit = 0;
            for (int j = 0; j < n; ++j) if (current_best_i != j) if (companies[j].rect.x1 < companies[current_best_i].rect.x2 && companies[j].rect.x2 > companies[current_best_i].rect.x1 && companies[j].rect.y2 <= companies[current_best_i].rect.y1) limit = std::max(limit, companies[j].rect.y2);
            long long max_expand = companies[current_best_i].rect.y1 - limit;
            if (max_expand > 0) {
                 long long need_expand = (companies[current_best_i].r - companies[current_best_i].s) / width;
                 long long expand = std::min(max_expand, need_expand);
                 if (expand > 0) { long long gain = expand * width; if (gain > max_gain) { max_gain = gain; best_dir = 1; } }
            }
        }
        // LEFT
        if (height > 0) {
            int limit = 0;
            for (int j = 0; j < n; ++j) if (current_best_i != j) if (companies[j].rect.y1 < companies[current_best_i].rect.y2 && companies[j].rect.y2 > companies[current_best_i].rect.y1 && companies[j].rect.x2 <= companies[current_best_i].rect.x1) limit = std::max(limit, companies[j].rect.x2);
            long long max_expand = companies[current_best_i].rect.x1 - limit;
            if (max_expand > 0) {
                 long long need_expand = (companies[current_best_i].r - companies[current_best_i].s) / height;
                 long long expand = std::min(max_expand, need_expand);
                 if (expand > 0) { long long gain = expand * height; if (gain > max_gain) { max_gain = gain; best_dir = 2; } }
            }
        }
        // RIGHT
        if (height > 0) {
            int limit = 10000;
            for (int j = 0; j < n; ++j) if (current_best_i != j) if (companies[j].rect.y1 < companies[current_best_i].rect.y2 && companies[j].rect.y2 > companies[current_best_i].rect.y1 && companies[j].rect.x1 >= companies[current_best_i].rect.x2) limit = std::min(limit, companies[j].rect.x1);
            long long max_expand = limit - companies[current_best_i].rect.x2;
            if (max_expand > 0) {
                 long long need_expand = (companies[current_best_i].r - companies[current_best_i].s) / height;
                 long long expand = std::min(max_expand, need_expand);
                 if (expand > 0) { long long gain = expand * height; if (gain > max_gain) { max_gain = gain; best_dir = 3; } }
            }
        }

        if (best_dir != -1) {
            long long need_expand, expand;
            if (best_dir == 0) { // UP
                int limit = 10000; for (int j=0; j<n; ++j) if(current_best_i!=j) if (companies[j].rect.x1 < companies[current_best_i].rect.x2 && companies[j].rect.x2 > companies[current_best_i].rect.x1 && companies[j].rect.y1 >= companies[current_best_i].rect.y2) limit = std::min(limit, companies[j].rect.y1);
                need_expand = (companies[current_best_i].r - companies[current_best_i].s) / width;
                expand = std::min((long long)limit - companies[current_best_i].rect.y2, need_expand);
                companies[current_best_i].rect.y2 += expand;
            } else if (best_dir == 1) { // DOWN
                int limit = 0; for (int j=0; j<n; ++j) if(current_best_i!=j) if (companies[j].rect.x1 < companies[current_best_i].rect.x2 && companies[j].rect.x2 > companies[current_best_i].rect.x1 && companies[j].rect.y2 <= companies[current_best_i].rect.y1) limit = std::max(limit, companies[j].rect.y2);
                need_expand = (companies[current_best_i].r - companies[current_best_i].s) / width;
                expand = std::min((long long)companies[current_best_i].rect.y1 - limit, need_expand);
                companies[current_best_i].rect.y1 -= expand;
            } else if (best_dir == 2) { // LEFT
                int limit = 0; for (int j=0; j<n; ++j) if(current_best_i!=j) if (companies[j].rect.y1 < companies[current_best_i].rect.y2 && companies[j].rect.y2 > companies[current_best_i].rect.y1 && companies[j].rect.x2 <= companies[current_best_i].rect.x1) limit = std::max(limit, companies[j].rect.x2);
                need_expand = (companies[current_best_i].r - companies[current_best_i].s) / height;
                expand = std::min((long long)companies[current_best_i].rect.x1 - limit, need_expand);
                companies[current_best_i].rect.x1 -= expand;
            } else { // RIGHT
                int limit = 10000; for (int j=0; j<n; ++j) if(current_best_i!=j) if (companies[j].rect.y1 < companies[current_best_i].rect.y2 && companies[j].rect.y2 > companies[current_best_i].rect.y1 && companies[j].rect.x1 >= companies[current_best_i].rect.x2) limit = std::min(limit, companies[j].rect.x1);
                need_expand = (companies[current_best_i].r - companies[current_best_i].s) / height;
                expand = std::min((long long)limit - companies[current_best_i].rect.x2, need_expand);
                companies[current_best_i].rect.x2 += expand;
            }
            companies[current_best_i].s = (long long)(companies[current_best_i].rect.x2 - companies[current_best_i].rect.x1) * (companies[current_best_i].rect.y2 - companies[current_best_i].rect.y1);
        } else {
            stuck[current_best_i] = true;
            stuck_count++;
        }
    }

    // Phase 2: Gap filling
    int n2_iterations = 2 * n;
    for (int iter = 0; iter < n2_iterations; ++iter) {
        int best_i = -1, best_dir = -1;
        double max_gain = -1e18; 
        bool can_expand = false;

        for (int i = 0; i < n; ++i) {
            double current_p = calculate_satisfaction(companies[i].s, companies[i].r);
            
            // UP
            int limit_up = 10000; for (int j=0;j<n;++j) if(i!=j) if(companies[j].rect.x1<companies[i].rect.x2&&companies[j].rect.x2>companies[i].rect.x1&&companies[j].rect.y1>=companies[i].rect.y2) limit_up = std::min(limit_up,companies[j].rect.y1);
            if (limit_up > companies[i].rect.y2) { can_expand = true; long long delta_s = (long long)(companies[i].rect.x2 - companies[i].rect.x1) * (limit_up-companies[i].rect.y2); double next_p = calculate_satisfaction(companies[i].s + delta_s, companies[i].r); if (next_p - current_p > max_gain) { max_gain = next_p - current_p; best_i = i; best_dir = 0; } }
            // DOWN
            int limit_down = 0; for (int j=0;j<n;++j) if(i!=j) if(companies[j].rect.x1<companies[i].rect.x2&&companies[j].rect.x2>companies[i].rect.x1&&companies[j].rect.y2<=companies[i].rect.y1) limit_down = std::max(limit_down,companies[j].rect.y2);
            if (limit_down < companies[i].rect.y1) { can_expand = true; long long delta_s = (long long)(companies[i].rect.x2 - companies[i].rect.x1) * (companies[i].rect.y1 - limit_down); double next_p = calculate_satisfaction(companies[i].s + delta_s, companies[i].r); if (next_p - current_p > max_gain) { max_gain = next_p - current_p; best_i = i; best_dir = 1; } }
            // LEFT
            int limit_left = 0; for (int j=0;j<n;++j) if(i!=j) if(companies[j].rect.y1<companies[i].rect.y2&&companies[j].rect.y2>companies[i].rect.y1&&companies[j].rect.x2<=companies[i].rect.x1) limit_left = std::max(limit_left,companies[j].rect.x2);
            if (limit_left < companies[i].rect.x1) { can_expand = true; long long delta_s = (long long)(companies[i].rect.y2 - companies[i].rect.y1) * (companies[i].rect.x1 - limit_left); double next_p = calculate_satisfaction(companies[i].s + delta_s, companies[i].r); if (next_p - current_p > max_gain) { max_gain = next_p - current_p; best_i = i; best_dir = 2; } }
            // RIGHT
            int limit_right = 10000; for (int j=0;j<n;++j) if(i!=j) if(companies[j].rect.y1<companies[i].rect.y2&&companies[j].rect.y2>companies[i].rect.y1&&companies[j].rect.x1>=companies[i].rect.x2) limit_right = std::min(limit_right,companies[j].rect.x1);
            if (limit_right > companies[i].rect.x2) { can_expand = true; long long delta_s = (long long)(companies[i].rect.y2 - companies[i].rect.y1) * (limit_right - companies[i].rect.x2); double next_p = calculate_satisfaction(companies[i].s + delta_s, companies[i].r); if (next_p - current_p > max_gain) { max_gain = next_p - current_p; best_i = i; best_dir = 3; } }
        }
        
        if (best_i != -1) {
            if (best_dir == 0) { int limit = 10000; for (int j=0;j<n;++j) if(best_i!=j) if(companies[j].rect.x1<companies[best_i].rect.x2&&companies[j].rect.x2>companies[best_i].rect.x1&&companies[j].rect.y1>=companies[best_i].rect.y2) limit=std::min(limit,companies[j].rect.y1); companies[best_i].rect.y2 = limit; } 
            else if (best_dir == 1) { int limit = 0; for (int j=0;j<n;++j) if(best_i!=j) if(companies[j].rect.x1<companies[best_i].rect.x2&&companies[j].rect.x2>companies[best_i].rect.x1&&companies[j].rect.y2<=companies[best_i].rect.y1) limit=std::max(limit,companies[j].rect.y2); companies[best_i].rect.y1 = limit; }
            else if (best_dir == 2) { int limit = 0; for (int j=0;j<n;++j) if(best_i!=j) if(companies[j].rect.y1<companies[best_i].rect.y2&&companies[j].rect.y2>companies[best_i].rect.y1&&companies[j].rect.x2<=companies[best_i].rect.x1) limit=std::max(limit,companies[j].rect.x2); companies[best_i].rect.x1 = limit; }
            else { int limit = 10000; for (int j=0;j<n;++j) if(best_i!=j) if(companies[j].rect.y1<companies[best_i].rect.y2&&companies[j].rect.y2>companies[best_i].rect.y1&&companies[j].rect.x1>=companies[best_i].rect.x2) limit=std::min(limit,companies[j].rect.x1); companies[best_i].rect.x2 = limit; }
            companies[best_i].s = (long long)(companies[best_i].rect.x2 - companies[best_i].rect.x1) * (companies[best_i].rect.y2 - companies[best_i].rect.y1);
        } else if (!can_expand) {
            break;
        }
    }

    for (int i = 0; i < n; ++i) {
        std::cout << companies[i].rect.x1 << " " << companies[i].rect.y1 << " "
                  << companies[i].rect.x2 << " " << companies[i].rect.y2 << "\n";
    }

    return 0;
}