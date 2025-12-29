#include <iostream>
#include <vector>
#include <algorithm>
#include <cmath>
#include <numeric>
#include <climits>
#include <cstdlib>

using namespace std;
using ll = long long;

struct Company {
    int x, y;
    ll r;
    int id;
};

vector<Company> comps;

void solve(int lx, int rx, int ly, int ry, vector<int>& ids, vector<array<int,4>>& ans) {
    int m = ids.size();
    if (m == 1) {
        int id = ids[0];
        ans[id] = {lx, ly, rx, ry};
        return;
    }
    
    ll total_r = 0;
    for (int id : ids) total_r += comps[id].r;
    int width = rx - lx;
    int height = ry - ly;
    
    // Try vertical splits
    vector<int> sorted_by_x = ids;
    sort(sorted_by_x.begin(), sorted_by_x.end(),
         [](int a, int b) { return comps[a].x < comps[b].x; });
    vector<ll> prefix_r(m+1, 0);
    for (int i = 0; i < m; ++i) prefix_r[i+1] = prefix_r[i] + comps[sorted_by_x[i]].r;
    
    double best_cost = 1e100;
    bool vertical = true;
    int split_c = -1;
    int split_k = -1;
    
    for (int k = 1; k < m; ++k) {
        ll sum_left = prefix_r[k];
        ll sum_right = total_r - sum_left;
        int left_max_x = comps[sorted_by_x[k-1]].x;
        int right_min_x = comps[sorted_by_x[k]].x;
        int c_min = left_max_x + 1;
        int c_max = right_min_x;
        if (c_min > c_max) continue;
        
        double c0 = lx + (double)sum_left / height;
        int c_floor = (int)floor(c0);
        int c_ceil = c_floor + 1;
        vector<int> candidates = {c_floor, c_ceil, c_min, c_max};
        sort(candidates.begin(), candidates.end());
        candidates.erase(unique(candidates.begin(), candidates.end()), candidates.end());
        
        ll best_diff = LLONG_MAX;
        int c_best = -1;
        for (int cand : candidates) {
            if (cand < c_min || cand > c_max) continue;
            ll area_left = (ll)(cand - lx) * height;
            ll diff = llabs(area_left - sum_left);
            if (diff < best_diff) {
                best_diff = diff;
                c_best = cand;
            }
        }
        if (c_best == -1) continue;
        
        int m1 = k;
        int m2 = m - k;
        double cost = (double)(best_diff * best_diff) *
                      ( (double)m1 / (sum_left * sum_left) +
                        (double)m2 / (sum_right * sum_right) );
        if (cost < best_cost) {
            best_cost = cost;
            vertical = true;
            split_c = c_best;
            split_k = k;
        }
    }
    
    // Try horizontal splits
    vector<int> sorted_by_y = ids;
    sort(sorted_by_y.begin(), sorted_by_y.end(),
         [](int a, int b) { return comps[a].y < comps[b].y; });
    vector<ll> prefix_r_y(m+1, 0);
    for (int i = 0; i < m; ++i) prefix_r_y[i+1] = prefix_r_y[i] + comps[sorted_by_y[i]].r;
    
    for (int k = 1; k < m; ++k) {
        ll sum_bottom = prefix_r_y[k];
        ll sum_top = total_r - sum_bottom;
        int bottom_max_y = comps[sorted_by_y[k-1]].y;
        int top_min_y = comps[sorted_by_y[k]].y;
        int d_min = bottom_max_y + 1;
        int d_max = top_min_y;
        if (d_min > d_max) continue;
        
        double d0 = ly + (double)sum_bottom / width;
        int d_floor = (int)floor(d0);
        int d_ceil = d_floor + 1;
        vector<int> candidates = {d_floor, d_ceil, d_min, d_max};
        sort(candidates.begin(), candidates.end());
        candidates.erase(unique(candidates.begin(), candidates.end()), candidates.end());
        
        ll best_diff = LLONG_MAX;
        int d_best = -1;
        for (int cand : candidates) {
            if (cand < d_min || cand > d_max) continue;
            ll area_bottom = (ll)(cand - ly) * width;
            ll diff = llabs(area_bottom - sum_bottom);
            if (diff < best_diff) {
                best_diff = diff;
                d_best = cand;
            }
        }
        if (d_best == -1) continue;
        
        int m1 = k;
        int m2 = m - k;
        double cost = (double)(best_diff * best_diff) *
                      ( (double)m1 / (sum_bottom * sum_bottom) +
                        (double)m2 / (sum_top * sum_top) );
        if (cost < best_cost) {
            best_cost = cost;
            vertical = false;
            split_c = d_best;
            split_k = k;
        }
    }
    
    // Perform the split
    if (vertical) {
        int c = split_c;
        vector<int> left_ids, right_ids;
        for (int id : ids) {
            if (comps[id].x < c) left_ids.push_back(id);
            else right_ids.push_back(id);
        }
        solve(lx, c, ly, ry, left_ids, ans);
        solve(c, rx, ly, ry, right_ids, ans);
    } else {
        int d = split_c;
        vector<int> bottom_ids, top_ids;
        for (int id : ids) {
            if (comps[id].y < d) bottom_ids.push_back(id);
            else top_ids.push_back(id);
        }
        solve(lx, rx, ly, d, bottom_ids, ans);
        solve(lx, rx, d, ry, top_ids, ans);
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    cin >> n;
    comps.resize(n);
    for (int i = 0; i < n; ++i) {
        int x, y;
        ll r;
        cin >> x >> y >> r;
        comps[i] = {x, y, r, i};
    }
    
    vector<array<int,4>> ans(n);
    vector<int> all_ids(n);
    iota(all_ids.begin(), all_ids.end(), 0);
    
    solve(0, 10000, 0, 10000, all_ids, ans);
    
    for (int i = 0; i < n; ++i) {
        cout << ans[i][0] << " " << ans[i][1] << " "
             << ans[i][2] << " " << ans[i][3] << "\n";
    }
    
    return 0;
}