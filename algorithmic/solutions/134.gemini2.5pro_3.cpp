#include <iostream>
#include <vector>
#include <array>
#include <algorithm>
#include <numeric>

using namespace std;

using ull = unsigned long long;

struct Rect {
    ull lx, hx, ly, hy;
};

int query(ull x, ull y) {
    if (x == 0) x = 1;
    if (y == 0) y = 1;
    cout << x << " " << y << endl;
    int resp;
    cin >> resp;
    return resp;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    ull n;
    cin >> n;

    vector<Rect> regions;
    regions.push_back({1, n, 1, n});

    while (true) {
        if(regions.empty()) {
            // This case indicates a logic error, as the solution should always be within a region.
            return 1;
        }

        ull min_lx = -1, max_hx = 0, min_ly = -1, max_hy = 0;
        bool first = true;
        for (const auto& r : regions) {
            if (first) {
                min_lx = r.lx; max_hx = r.hx;
                min_ly = r.ly; max_hy = r.hy;
                first = false;
            } else {
                min_lx = min(min_lx, r.lx);
                max_hx = max(max_hx, r.hx);
                min_ly = min(min_ly, r.ly);
                max_hy = max(max_hy, r.hy);
            }
        }

        if (max_hx == min_lx && max_hy == min_ly) {
            query(min_lx, min_ly);
            return 0;
        }

        ull qx, qy;
        if (max_hx - min_lx >= max_hy - min_ly) {
            qx = min_lx + (max_hx - min_lx) / 2;
            if (qx < min_lx) qx = min_lx; // Avoid underflow for small ranges
            qy = max_hy;
        } else {
            qx = max_hx;
            qy = min_ly + (max_hy - min_ly) / 2;
            if (qy < min_ly) qy = min_ly; // Avoid underflow
        }
        
        int resp = query(qx, qy);

        if (resp == 0) {
            return 0;
        }
        
        vector<Rect> next_regions;
        if (resp == 1) { // x < a
            ull new_lx = qx + 1;
            for (const auto& r : regions) {
                ull updated_lx = max(r.lx, new_lx);
                if (updated_lx <= r.hx) {
                    next_regions.push_back({updated_lx, r.hx, r.ly, r.hy});
                }
            }
        } else if (resp == 2) { // y < b
            ull new_ly = qy + 1;
            for (const auto& r : regions) {
                ull updated_ly = max(r.ly, new_ly);
                if (updated_ly <= r.hy) {
                    next_regions.push_back({r.lx, r.hx, updated_ly, r.hy});
                }
            }
        } else { // resp == 3: x > a or y > b
            ull bound_x, bound_y;
            if (max_hx - min_lx >= max_hy - min_ly) { // query was (qx, max_hy)
                // a <= qx or b < max_hy
                bound_x = qx;
                bound_y = max_hy > 1 ? max_hy - 1 : 0;
            } else { // query was (max_hx, qy)
                // a < max_hx or b <= qy
                bound_x = max_hx > 1 ? max_hx - 1 : 0;
                bound_y = qy;
            }

            for (const auto& r : regions) {
                // Part 1: intersection with a <= bound_x
                ull r1_hx = min(r.hx, bound_x);
                if (r.lx <= r1_hx) {
                    next_regions.push_back({r.lx, r1_hx, r.ly, r.hy});
                }
                
                // Part 2: intersection with b <= bound_y, but not in part 1
                // This is R intersect [bound_x+1, n] x [1, bound_y]
                ull r2_lx = bound_x < n ? bound_x + 1 : n + 1;
                r2_lx = max(r.lx, r2_lx);
                ull r2_hy = min(r.hy, bound_y);
                if (r2_lx <= r.hx && r.ly <= r2_hy) {
                    next_regions.push_back({r2_lx, r.hx, r.ly, r2_hy});
                }
            }
        }
        regions = next_regions;
    }

    return 0;
}