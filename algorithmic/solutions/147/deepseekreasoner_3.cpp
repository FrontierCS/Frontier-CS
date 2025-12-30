#include <iostream>
#include <vector>
#include <algorithm>
#include <cmath>
#include <numeric>
#include <cstdlib>

using namespace std;

struct Point {
    int id, x, y, r;
};

struct Rect {
    int a, b, c, d; // a<c, b<d
};

int n;
vector<Point> pts;
vector<Rect> ans;

void partition(int lx, int rx, int ly, int ry, vector<int> ids) {
    if (ids.size() == 1) {
        int i = ids[0];
        ans[i] = {lx, ly, rx, ry};
        return;
    }
    int total_r = 0;
    for (int id : ids) total_r += pts[id].r;
    
    int best_axis = -1;
    int best_split = -1;
    vector<int> best_left, best_right;
    double best_cost = 1e18;
    
    // try vertical split
    sort(ids.begin(), ids.end(), [&](int a, int b) {
        return pts[a].x < pts[b].x;
    });
    int m = ids.size();
    for (int i = 0; i < m-1; ++i) {
        if (pts[ids[i]].x == pts[ids[i+1]].x) continue;
        vector<int> left(ids.begin(), ids.begin()+i+1);
        vector<int> right(ids.begin()+i+1, ids.end());
        int left_r = 0;
        for (int id : left) left_r += pts[id].r;
        int right_r = total_r - left_r;
        int L = pts[left.back()].x + 1;
        int R = pts[right.front()].x;
        if (L > R) continue;
        int H = ry - ly;
        double ideal_s = lx + left_r / (double)H;
        int s = round(ideal_s);
        if (s < L) s = L;
        if (s > R) s = R;
        int area_left = (s - lx) * H;
        int area_right = (rx - s) * H;
        double cost = abs(area_left - left_r) + abs(area_right - right_r);
        if (cost < best_cost) {
            best_cost = cost;
            best_axis = 0;
            best_split = s;
            best_left = left;
            best_right = right;
        }
    }
    
    // try horizontal split
    sort(ids.begin(), ids.end(), [&](int a, int b) {
        return pts[a].y < pts[b].y;
    });
    for (int i = 0; i < m-1; ++i) {
        if (pts[ids[i]].y == pts[ids[i+1]].y) continue;
        vector<int> left(ids.begin(), ids.begin()+i+1);
        vector<int> right(ids.begin()+i+1, ids.end());
        int left_r = 0;
        for (int id : left) left_r += pts[id].r;
        int right_r = total_r - left_r;
        int L = pts[left.back()].y + 1;
        int R = pts[right.front()].y;
        if (L > R) continue;
        int W = rx - lx;
        double ideal_s = ly + left_r / (double)W;
        int s = round(ideal_s);
        if (s < L) s = L;
        if (s > R) s = R;
        int area_left = (s - ly) * W;
        int area_right = (ry - s) * W;
        double cost = abs(area_left - left_r) + abs(area_right - right_r);
        if (cost < best_cost) {
            best_cost = cost;
            best_axis = 1;
            best_split = s;
            best_left = left;
            best_right = right;
        }
    }
    
    // fallback if no feasible split found (should rarely happen)
    if (best_axis == -1) {
        // try to isolate a single point
        for (int id : ids) {
            int x = pts[id].x, y = pts[id].y;
            bool ok;
            // vertical: s = x+1, all others with x' >= s
            ok = true;
            for (int j : ids) if (j != id) if (pts[j].x < x+1) { ok = false; break; }
            if (ok) {
                best_axis = 0;
                best_split = x+1;
                best_left = {id};
                best_right = ids;
                best_right.erase(find(best_right.begin(), best_right.end(), id));
                break;
            }
            // vertical: s = x, all others with x' <= x-1
            ok = true;
            for (int j : ids) if (j != id) if (pts[j].x > x-1) { ok = false; break; }
            if (ok) {
                best_axis = 0;
                best_split = x;
                best_left = ids;
                best_left.erase(find(best_left.begin(), best_left.end(), id));
                best_right = {id};
                break;
            }
            // horizontal: s = y+1
            ok = true;
            for (int j : ids) if (j != id) if (pts[j].y < y+1) { ok = false; break; }
            if (ok) {
                best_axis = 1;
                best_split = y+1;
                best_left = {id};
                best_right = ids;
                best_right.erase(find(best_right.begin(), best_right.end(), id));
                break;
            }
            // horizontal: s = y
            ok = true;
            for (int j : ids) if (j != id) if (pts[j].y > y-1) { ok = false; break; }
            if (ok) {
                best_axis = 1;
                best_split = y;
                best_left = ids;
                best_left.erase(find(best_left.begin(), best_left.end(), id));
                best_right = {id};
                break;
            }
        }
        // if still no, brute force over all possible split lines
        if (best_axis == -1) {
            // vertical
            for (int s = lx+1; s < rx; ++s) {
                vector<int> left, right;
                for (int id : ids) {
                    if (pts[id].x+1 <= s) left.push_back(id);
                    else if (pts[id].x >= s) right.push_back(id);
                    else { left.clear(); right.clear(); break; }
                }
                if (left.empty() || right.empty()) continue;
                int left_r = 0; for (int id : left) left_r += pts[id].r;
                int right_r = total_r - left_r;
                int H = ry - ly;
                int area_left = (s - lx) * H;
                int area_right = (rx - s) * H;
                double cost = abs(area_left - left_r) + abs(area_right - right_r);
                if (cost < best_cost) {
                    best_cost = cost;
                    best_axis = 0;
                    best_split = s;
                    best_left = left;
                    best_right = right;
                }
            }
            // horizontal
            if (best_axis == -1) {
                for (int s = ly+1; s < ry; ++s) {
                    vector<int> left, right;
                    for (int id : ids) {
                        if (pts[id].y+1 <= s) left.push_back(id);
                        else if (pts[id].y >= s) right.push_back(id);
                        else { left.clear(); right.clear(); break; }
                    }
                    if (left.empty() || right.empty()) continue;
                    int left_r = 0; for (int id : left) left_r += pts[id].r;
                    int right_r = total_r - left_r;
                    int W = rx - lx;
                    int area_left = (s - ly) * W;
                    int area_right = (ry - s) * W;
                    double cost = abs(area_left - left_r) + abs(area_right - right_r);
                    if (cost < best_cost) {
                        best_cost = cost;
                        best_axis = 1;
                        best_split = s;
                        best_left = left;
                        best_right = right;
                    }
                }
            }
            // last resort: split at middle and assign arbitrarily
            if (best_axis == -1) {
                best_axis = 0;
                best_split = (lx + rx) / 2;
                best_left.clear(); best_right.clear();
                for (int id : ids) {
                    if (pts[id].x < best_split) best_left.push_back(id);
                    else best_right.push_back(id);
                }
            }
        }
    }
    
    if (best_axis == 0) {
        partition(lx, best_split, ly, ry, best_left);
        partition(best_split, rx, ly, ry, best_right);
    } else {
        partition(lx, rx, ly, best_split, best_left);
        partition(lx, rx, best_split, ry, best_right);
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    cin >> n;
    pts.resize(n);
    for (int i = 0; i < n; ++i) {
        cin >> pts[i].x >> pts[i].y >> pts[i].r;
        pts[i].id = i;
    }
    
    ans.resize(n);
    vector<int> all_ids(n);
    iota(all_ids.begin(), all_ids.end(), 0);
    partition(0, 10000, 0, 10000, all_ids);
    
    for (int i = 0; i < n; ++i) {
        cout << ans[i].a << " " << ans[i].b << " " << ans[i].c << " " << ans[i].d << "\n";
    }
    
    return 0;
}