#include <iostream>
#include <vector>
#include <algorithm>
#include <tuple>
#include <cmath>
#include <cassert>

using namespace std;

struct Point {
    int x, y;
    Point(int x = 0, int y = 0) : x(x), y(y) {}
    bool operator==(const Point& other) const { return x == other.x && y == other.y; }
    bool operator<(const Point& other) const { return tie(x, y) < tie(other.x, other.y); }
};

int N, M;
vector<vector<bool>> dot;               // [x][y]
vector<vector<int>> by_x;               // for each x, sorted list of y
vector<vector<int>> by_y;               // for each y, sorted list of x
vector<vector<int>> by_u;               // u = x+y, size 2N-1, sorted list of v
vector<vector<int>> by_v;               // index = v + N-1, sorted list of u
vector<vector<bool>> used_h;            // horizontal unit edges [x][y] (x in [0,N-2])
vector<vector<bool>> used_v;            // vertical unit edges [x][y] (y in [0,N-2])
vector<vector<bool>> used_d1;           // diagonal (slope 1) unit edges [x][y] (x,y in [0,N-2])
vector<vector<bool>> used_d2;           // diagonal (slope -1) unit edges [x][y] (x in [0,N-2], y in [1,N-1])

vector<Point> dots_list;                // all existing dots
int center;                             // (N-1)/2
const int MAX_SIDE = 20;                // limit side length for candidate generation
const int MAX_CANDIDATES = 5000;        // limit candidates per step

// insert value into sorted vector
void insert_sorted(vector<int>& vec, int val) {
    vec.insert(upper_bound(vec.begin(), vec.end(), val), val);
}

int weight(const Point& p) {
    int dx = p.x - center;
    int dy = p.y - center;
    return dx * dx + dy * dy + 1;
}

// condition 2 helpers
bool exists_dot_between_x(int y, int x1, int x2) {
    const vector<int>& xs = by_y[y];
    auto it = upper_bound(xs.begin(), xs.end(), x1);
    return it != xs.end() && *it < x2;
}
bool exists_dot_between_y(int x, int y1, int y2) {
    const vector<int>& ys = by_x[x];
    auto it = upper_bound(ys.begin(), ys.end(), y1);
    return it != ys.end() && *it < y2;
}
bool exists_dot_between_u(int v, int u1, int u2) {
    int vidx = v + N - 1;
    const vector<int>& us = by_v[vidx];
    auto it = upper_bound(us.begin(), us.end(), u1);
    return it != us.end() && *it < u2;
}
bool exists_dot_between_v(int u, int v1, int v2) {
    const vector<int>& vs = by_u[u];
    auto it = upper_bound(vs.begin(), vs.end(), v1);
    return it != vs.end() && *it < v2;
}

// check condition 2 for a segment
bool check_segment_no_dots(const Point& a, const Point& b) {
    if (a.y == b.y) { // horizontal
        int y = a.y;
        int x1 = min(a.x, b.x), x2 = max(a.x, b.x);
        if (x2 - x1 <= 1) return true;
        return !exists_dot_between_x(y, x1, x2);
    }
    if (a.x == b.x) { // vertical
        int x = a.x;
        int y1 = min(a.y, b.y), y2 = max(a.y, b.y);
        if (y2 - y1 <= 1) return true;
        return !exists_dot_between_y(x, y1, y2);
    }
    if (a.x + a.y == b.x + b.y) { // u constant (slope -1)
        int u = a.x + a.y;
        int v1 = a.x - a.y, v2 = b.x - b.y;
        if (abs(v2 - v1) <= 2) return true;
        int v_min = min(v1, v2), v_max = max(v1, v2);
        return !exists_dot_between_v(u, v_min, v_max);
    }
    if (a.x - a.y == b.x - b.y) { // v constant (slope 1)
        int v = a.x - a.y;
        int u1 = a.x + a.y, u2 = b.x + b.y;
        if (abs(u2 - u1) <= 2) return true;
        int u_min = min(u1, u2), u_max = max(u1, u2);
        return !exists_dot_between_u(v, u_min, u_max);
    }
    return false;
}

// check condition 3 for a segment
bool check_segment_no_overlap(const Point& a, const Point& b) {
    if (a.y == b.y) { // horizontal
        int y = a.y;
        int x1 = min(a.x, b.x), x2 = max(a.x, b.x);
        for (int x = x1; x < x2; ++x)
            if (used_h[x][y]) return false;
        return true;
    }
    if (a.x == b.x) { // vertical
        int x = a.x;
        int y1 = min(a.y, b.y), y2 = max(a.y, b.y);
        for (int y = y1; y < y2; ++y)
            if (used_v[x][y]) return false;
        return true;
    }
    if (a.x + a.y == b.x + b.y) { // u constant (slope -1)
        Point p1 = a, p2 = b;
        if (p1.x > p2.x) swap(p1, p2);
        for (int i = 0; i < p2.x - p1.x; ++i) {
            int x = p1.x + i;
            int y = p1.y - i;
            if (used_d2[x][y]) return false;
        }
        return true;
    }
    if (a.x - a.y == b.x - b.y) { // v constant (slope 1)
        Point p1 = a, p2 = b;
        if (p1.x > p2.x) swap(p1, p2);
        for (int i = 0; i < p2.x - p1.x; ++i) {
            int x = p1.x + i;
            int y = p1.y + i;
            if (used_d1[x][y]) return false;
        }
        return true;
    }
    return false;
}

// mark a segment as used (condition 3 update)
void mark_segment(const Point& a, const Point& b) {
    if (a.y == b.y) {
        int y = a.y;
        int x1 = min(a.x, b.x), x2 = max(a.x, b.x);
        for (int x = x1; x < x2; ++x) used_h[x][y] = true;
    } else if (a.x == b.x) {
        int x = a.x;
        int y1 = min(a.y, b.y), y2 = max(a.y, b.y);
        for (int y = y1; y < y2; ++y) used_v[x][y] = true;
    } else if (a.x + a.y == b.x + b.y) {
        Point p1 = a, p2 = b;
        if (p1.x > p2.x) swap(p1, p2);
        for (int i = 0; i < p2.x - p1.x; ++i) {
            int x = p1.x + i;
            int y = p1.y - i;
            used_d2[x][y] = true;
        }
    } else if (a.x - a.y == b.x - b.y) {
        Point p1 = a, p2 = b;
        if (p1.x > p2.x) swap(p1, p2);
        for (int i = 0; i < p2.x - p1.x; ++i) {
            int x = p1.x + i;
            int y = p1.y + i;
            used_d1[x][y] = true;
        }
    }
}

bool inside(const Point& p) {
    return p.x >= 0 && p.x < N && p.y >= 0 && p.y < N;
}

struct Candidate {
    Point p1, p2, p3, p4;
    int score;
    Candidate(Point p1, Point p2, Point p3, Point p4, int s)
        : p1(p1), p2(p2), p3(p3), p4(p4), score(s) {}
};

int main() {
    cin >> N >> M;
    center = (N - 1) / 2;

    // initialize data structures
    dot.assign(N, vector<bool>(N, false));
    by_x.resize(N);
    by_y.resize(N);
    int max_u = 2 * N - 2;
    by_u.resize(max_u + 1);
    int max_v_idx = 2 * N - 2; // v ranges from -(N-1) to N-1
    by_v.resize(max_v_idx + 1);

    used_h.assign(N - 1, vector<bool>(N, false));
    used_v.assign(N, vector<bool>(N - 1, false));
    used_d1.assign(N - 1, vector<bool>(N - 1, false));
    used_d2.assign(N - 1, vector<bool>(N, false));

    dots_list.reserve(N * N);

    // read initial dots
    for (int i = 0; i < M; ++i) {
        int x, y;
        cin >> x >> y;
        dot[x][y] = true;
        dots_list.emplace_back(x, y);
        insert_sorted(by_x[x], y);
        insert_sorted(by_y[y], x);
        int u = x + y;
        int v = x - y;
        insert_sorted(by_u[u], v);
        int vidx = v + N - 1;
        insert_sorted(by_v[vidx], u);
    }

    vector<tuple<Point, Point, Point, Point>> operations;

    while (true) {
        vector<Candidate> candidates;
        candidates.reserve(MAX_CANDIDATES);

        // sort existing dots by weight descending (prioritize high weight)
        sort(dots_list.begin(), dots_list.end(),
             [](const Point& a, const Point& b) { return weight(a) > weight(b); });

        for (const Point& d : dots_list) {
            // ----- horizontal pairs (same y) -----
            int y = d.y;
            int low_x = max(0, d.x - MAX_SIDE);
            int high_x = min(N - 1, d.x + MAX_SIDE);
            auto it_x_start = lower_bound(by_y[y].begin(), by_y[y].end(), low_x);
            auto it_x_end = upper_bound(by_y[y].begin(), by_y[y].end(), high_x);
            for (auto it = it_x_start; it != it_x_end; ++it) {
                int ex = *it;
                if (ex == d.x) continue;
                Point e(ex, y);
                // f: same x as d, different y, within MAX_SIDE
                int low_y = max(0, d.y - MAX_SIDE);
                int high_y = min(N - 1, d.y + MAX_SIDE);
                auto it_y_start = lower_bound(by_x[d.x].begin(), by_x[d.x].end(), low_y);
                auto it_y_end = upper_bound(by_x[d.x].begin(), by_x[d.x].end(), high_y);
                for (auto itf = it_y_start; itf != it_y_end; ++itf) {
                    int fy = *itf;
                    if (fy == d.y) continue;
                    Point f(d.x, fy);
                    Point g(e.x, fy);
                    if (!inside(g) || dot[g.x][g.y]) continue;
                    if (!check_segment_no_dots(g, e)) continue;
                    if (!check_segment_no_dots(e, d)) continue;
                    if (!check_segment_no_dots(d, f)) continue;
                    if (!check_segment_no_dots(f, g)) continue;
                    if (!check_segment_no_overlap(g, e)) continue;
                    if (!check_segment_no_overlap(e, d)) continue;
                    if (!check_segment_no_overlap(d, f)) continue;
                    if (!check_segment_no_overlap(f, g)) continue;
                    candidates.emplace_back(g, e, d, f, weight(g));
                    if (candidates.size() >= MAX_CANDIDATES) break;
                }
                if (candidates.size() >= MAX_CANDIDATES) break;
            }
            if (candidates.size() >= MAX_CANDIDATES) break;

            // ----- vertical pairs (same x) -----
            int x = d.x;
            int low_y = max(0, d.y - MAX_SIDE);
            int high_y = min(N - 1, d.y + MAX_SIDE);
            auto it_y_start2 = lower_bound(by_x[x].begin(), by_x[x].end(), low_y);
            auto it_y_end2 = upper_bound(by_x[x].begin(), by_x[x].end(), high_y);
            for (auto it = it_y_start2; it != it_y_end2; ++it) {
                int ey = *it;
                if (ey == d.y) continue;
                Point e(x, ey);
                // f: same y as d, different x, within MAX_SIDE
                int low_x2 = max(0, d.x - MAX_SIDE);
                int high_x2 = min(N - 1, d.x + MAX_SIDE);
                auto it_x_start2 = lower_bound(by_y[d.y].begin(), by_y[d.y].end(), low_x2);
                auto it_x_end2 = upper_bound(by_y[d.y].begin(), by_y[d.y].end(), high_x2);
                for (auto itf = it_x_start2; itf != it_x_end2; ++itf) {
                    int fx = *itf;
                    if (fx == d.x) continue;
                    Point f(fx, d.y);
                    Point g(fx, e.y);
                    if (!inside(g) || dot[g.x][g.y]) continue;
                    if (!check_segment_no_dots(g, f)) continue;
                    if (!check_segment_no_dots(f, d)) continue;
                    if (!check_segment_no_dots(d, e)) continue;
                    if (!check_segment_no_dots(e, g)) continue;
                    if (!check_segment_no_overlap(g, f)) continue;
                    if (!check_segment_no_overlap(f, d)) continue;
                    if (!check_segment_no_overlap(d, e)) continue;
                    if (!check_segment_no_overlap(e, g)) continue;
                    candidates.emplace_back(g, f, d, e, weight(g));
                    if (candidates.size() >= MAX_CANDIDATES) break;
                }
                if (candidates.size() >= MAX_CANDIDATES) break;
            }
            if (candidates.size() >= MAX_CANDIDATES) break;

            // ----- u pairs (same u) -----
            int u = d.x + d.y;
            int v_d = d.x - d.y;
            int max_v_diff = MAX_SIDE * 2;
            int low_v = v_d - max_v_diff;
            int high_v = v_d + max_v_diff;
            auto it_v_start = lower_bound(by_u[u].begin(), by_u[u].end(), low_v);
            auto it_v_end = upper_bound(by_u[u].begin(), by_u[u].end(), high_v);
            for (auto it = it_v_start; it != it_v_end; ++it) {
                int ev = *it;
                if (ev == v_d) continue;
                int ex = (u + ev) / 2, ey = (u - ev) / 2;
                if ((u + ev) % 2 != 0 || (u - ev) % 2 != 0) continue;
                Point e(ex, ey);
                // f: same v as d, different u, within max_u_diff
                int vidx = v_d + N - 1;
                int max_u_diff = MAX_SIDE * 2;
                int low_u = u - max_u_diff;
                int high_u = u + max_u_diff;
                auto it_u_start = lower_bound(by_v[vidx].begin(), by_v[vidx].end(), low_u);
                auto it_u_end = upper_bound(by_v[vidx].begin(), by_v[vidx].end(), high_u);
                for (auto itf = it_u_start; itf != it_u_end; ++itf) {
                    int fu = *itf;
                    if (fu == u) continue;
                    int fx = (fu + v_d) / 2, fy = (fu - v_d) / 2;
                    if ((fu + v_d) % 2 != 0 || (fu - v_d) % 2 != 0) continue;
                    Point f(fx, fy);
                    int gx = (fu + ev) / 2, gy = (fu - ev) / 2;
                    if ((fu + ev) % 2 != 0 || (fu - ev) % 2 != 0) continue;
                    Point g(gx, gy);
                    if (!inside(g) || dot[g.x][g.y]) continue;
                    if (!check_segment_no_dots(g, f)) continue;
                    if (!check_segment_no_dots(f, d)) continue;
                    if (!check_segment_no_dots(d, e)) continue;
                    if (!check_segment_no_dots(e, g)) continue;
                    if (!check_segment_no_overlap(g, f)) continue;
                    if (!check_segment_no_overlap(f, d)) continue;
                    if (!check_segment_no_overlap(d, e)) continue;
                    if (!check_segment_no_overlap(e, g)) continue;
                    candidates.emplace_back(g, f, d, e, weight(g));
                    if (candidates.size() >= MAX_CANDIDATES) break;
                }
                if (candidates.size() >= MAX_CANDIDATES) break;
            }
            if (candidates.size() >= MAX_CANDIDATES) break;

            // ----- v pairs (same v) -----
            int v = d.x - d.y;
            u = d.x + d.y;
            int vidx_v = v + N - 1;
            int low_u2 = u - MAX_SIDE * 2;
            int high_u2 = u + MAX_SIDE * 2;
            auto it_u_start2 = lower_bound(by_v[vidx_v].begin(), by_v[vidx_v].end(), low_u2);
            auto it_u_end2 = upper_bound(by_v[vidx_v].begin(), by_v[vidx_v].end(), high_u2);
            for (auto it = it_u_start2; it != it_u_end2; ++it) {
                int eu = *it;
                if (eu == u) continue;
                int ex = (eu + v) / 2, ey = (eu - v) / 2;
                if ((eu + v) % 2 != 0 || (eu - v) % 2 != 0) continue;
                Point e(ex, ey);
                // f: same u as d, different v
                int max_v_diff2 = MAX_SIDE * 2;
                int low_v2 = v - max_v_diff2;
                int high_v2 = v + max_v_diff2;
                auto it_v_start2 = lower_bound(by_u[u].begin(), by_u[u].end(), low_v2);
                auto it_v_end2 = upper_bound(by_u[u].begin(), by_u[u].end(), high_v2);
                for (auto itf = it_v_start2; itf != it_v_end2; ++itf) {
                    int fv = *itf;
                    if (fv == v) continue;
                    int fx = (u + fv) / 2, fy = (u - fv) / 2;
                    if ((u + fv) % 2 != 0 || (u - fv) % 2 != 0) continue;
                    Point f(fx, fy);
                    int gx = (eu + fv) / 2, gy = (eu - fv) / 2;
                    if ((eu + fv) % 2 != 0 || (eu - fv) % 2 !=