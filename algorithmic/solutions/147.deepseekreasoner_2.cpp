#include <iostream>
#include <vector>
#include <algorithm>
#include <cmath>
#include <cstdlib>
#include <cassert>

using namespace std;

struct Rect {
    int a, b, c, d;
};

int n;
vector<int> x, y, r;
vector<Rect> ans;

void solve(vector<int> indices, Rect rect) {
    int m = indices.size();
    if (m == 1) {
        ans[indices[0]] = rect;
        return;
    }
    long long total_sum = 0;
    for (int idx : indices) total_sum += r[idx];
    
    double best_error = 1e18;
    bool best_vert = false;
    int best_s = 0;
    vector<int> best_left, best_right;
    
    // Try vertical split
    vector<int> idx_x = indices;
    sort(idx_x.begin(), idx_x.end(), [&](int i, int j) { return x[i] < x[j]; });
    vector<long long> pref_x(m+1, 0);
    for (int i = 0; i < m; ++i) pref_x[i+1] = pref_x[i] + r[idx_x[i]];
    
    for (int k = 1; k < m; ++k) {
        long long sum_left = pref_x[k];
        int left_max = x[idx_x[k-1]];
        int right_min = x[idx_x[k]];
        if (left_max >= right_min) continue;
        int s_min = left_max + 1;
        int s_max = right_min;
        double ideal = rect.a + (double)sum_left / total_sum * (rect.c - rect.a);
        vector<int> candidates = { (int)floor(ideal), (int)ceil(ideal), s_min, s_max };
        sort(candidates.begin(), candidates.end());
        for (int s : candidates) {
            if (s < s_min || s > s_max) continue;
            long long area_left = (long long)(s - rect.a) * (rect.d - rect.b);
            double error = abs(area_left - sum_left);
            if (error < best_error) {
                best_error = error;
                best_vert = true;
                best_s = s;
                best_left.assign(idx_x.begin(), idx_x.begin() + k);
                best_right.assign(idx_x.begin() + k, idx_x.end());
            }
        }
    }
    
    // Try horizontal split
    vector<int> idx_y = indices;
    sort(idx_y.begin(), idx_y.end(), [&](int i, int j) { return y[i] < y[j]; });
    vector<long long> pref_y(m+1, 0);
    for (int i = 0; i < m; ++i) pref_y[i+1] = pref_y[i] + r[idx_y[i]];
    
    for (int k = 1; k < m; ++k) {
        long long sum_left = pref_y[k];
        int left_max = y[idx_y[k-1]];
        int right_min = y[idx_y[k]];
        if (left_max >= right_min) continue;
        int s_min = left_max + 1;
        int s_max = right_min;
        double ideal = rect.b + (double)sum_left / total_sum * (rect.d - rect.b);
        vector<int> candidates = { (int)floor(ideal), (int)ceil(ideal), s_min, s_max };
        sort(candidates.begin(), candidates.end());
        for (int s : candidates) {
            if (s < s_min || s > s_max) continue;
            long long area_left = (long long)(s - rect.b) * (rect.c - rect.a);
            double error = abs(area_left - sum_left);
            if (error < best_error) {
                best_error = error;
                best_vert = false;
                best_s = s;
                best_left.assign(idx_y.begin(), idx_y.begin() + k);
                best_right.assign(idx_y.begin() + k, idx_y.end());
            }
        }
    }
    
    // Fallback if no feasible split found (should not happen)
    if (best_error == 1e18) {
        // Try vertical gaps
        for (int k = 1; k < m; ++k) {
            int left_max = x[idx_x[k-1]];
            int right_min = x[idx_x[k]];
            if (left_max < right_min) {
                best_vert = true;
                best_s = (left_max + right_min) / 2;
                if (best_s <= left_max) best_s = left_max + 1;
                if (best_s > right_min) best_s = right_min;
                best_left.assign(idx_x.begin(), idx_x.begin() + k);
                best_right.assign(idx_x.begin() + k, idx_x.end());
                break;
            }
        }
        if (best_error == 1e18) {
            // Try horizontal gaps
            for (int k = 1; k < m; ++k) {
                int left_max = y[idx_y[k-1]];
                int right_min = y[idx_y[k]];
                if (left_max < right_min) {
                    best_vert = false;
                    best_s = (left_max + right_min) / 2;
                    if (best_s <= left_max) best_s = left_max + 1;
                    if (best_s > right_min) best_s = right_min;
                    best_left.assign(idx_y.begin(), idx_y.begin() + k);
                    best_right.assign(idx_y.begin() + k, idx_y.end());
                    break;
                }
            }
        }
    }
    
    if (best_vert) {
        Rect left_rect = {rect.a, rect.b, best_s, rect.d};
        Rect right_rect = {best_s, rect.b, rect.c, rect.d};
        solve(best_left, left_rect);
        solve(best_right, right_rect);
    } else {
        Rect bottom_rect = {rect.a, rect.b, rect.c, best_s};
        Rect top_rect = {rect.a, best_s, rect.c, rect.d};
        solve(best_left, bottom_rect);
        solve(best_right, top_rect);
    }
}

int main() {
    cin >> n;
    x.resize(n); y.resize(n); r.resize(n);
    for (int i = 0; i < n; ++i) {
        cin >> x[i] >> y[i] >> r[i];
    }
    ans.resize(n);
    
    vector<int> indices(n);
    for (int i = 0; i < n; ++i) indices[i] = i;
    
    Rect whole = {0, 0, 10000, 10000};
    solve(indices, whole);
    
    for (int i = 0; i < n; ++i) {
        cout << ans[i].a << " " << ans[i].b << " " << ans[i].c << " " << ans[i].d << "\n";
    }
    
    return 0;
}