#include <iostream>
#include <vector>
#include <algorithm>
#include <utility>
#include <set>
#include <cmath>

using namespace std;

int N, M;
int c;
vector<vector<bool>> dot;
vector<vector<int>> weight;
vector<pair<int,int>> empty_pts;

// Edge intervals: for each line, list of intervals (closed)
vector<vector<pair<int,int>>> horz; // index by y
vector<vector<pair<int,int>>> vert; // index by x
vector<vector<pair<int,int>>> diag1; // index by (x-y) + (N-1)
vector<vector<pair<int,int>>> diag2; // index by (x+y)

bool inside(int x, int y) {
    return x >= 0 && x < N && y >= 0 && y < N;
}

int compute_weight(int x, int y) {
    int dx = x - c;
    int dy = y - c;
    return dx*dx + dy*dy + 1;
}

// Helper to check if an interval [a,b] overlaps with any interval in 'intervals' with positive length
bool has_overlap(const vector<pair<int,int>>& intervals, int a, int b) {
    for (auto [c, d] : intervals) {
        if (min(b, d) - max(a, c) >= 1) return true;
    }
    return false;
}

// Check overlap for horizontal edge at y, x in [a,b]
bool check_overlap_horizontal(int y, int a, int b) {
    return has_overlap(horz[y], a, b);
}

// Check overlap for vertical edge at x, y in [a,b]
bool check_overlap_vertical(int x, int a, int b) {
    return has_overlap(vert[x], a, b);
}

// Check overlap for diagonal with slope 1 (x-y = const), parameter x in [a,b]
bool check_overlap_diag1(int id, int a, int b) {
    return has_overlap(diag1[id], a, b);
}

// Check overlap for diagonal with slope -1 (x+y = const), parameter x in [a,b]
bool check_overlap_diag2(int id, int a, int b) {
    return has_overlap(diag2[id], a, b);
}

// Add an edge to the used structures
void add_edge(int x1, int y1, int x2, int y2) {
    if (x1 == x2) { // vertical
        int a = min(y1, y2), b = max(y1, y2);
        vert[x1].push_back({a, b});
    } else if (y1 == y2) { // horizontal
        int a = min(x1, x2), b = max(x1, x2);
        horz[y1].push_back({a, b});
    } else if (x1 - y1 == x2 - y2) { // slope 1
        int id = (x1 - y1) + (N-1);
        int a = min(x1, x2), b = max(x1, x2);
        diag1[id].push_back({a, b});
    } else if (x1 + y1 == x2 + y2) { // slope -1
        int id = x1 + y1;
        int a = min(x1, x2), b = max(x1, x2);
        diag2[id].push_back({a, b});
    }
}

// Check condition 2 for a horizontal edge
bool check_edge_dots_horizontal(int x1, int y1, int x2, int y2,
                                const set<pair<int,int>>& exist_set) {
    int a = min(x1, x2), b = max(x1, x2);
    for (int x = a; x <= b; ++x) {
        if (dot[x][y1] && exist_set.find({x, y1}) == exist_set.end())
            return false;
    }
    return true;
}

// Check condition 2 for a vertical edge
bool check_edge_dots_vertical(int x1, int y1, int x2, int y2,
                              const set<pair<int,int>>& exist_set) {
    int a = min(y1, y2), b = max(y1, y2);
    for (int y = a; y <= b; ++y) {
        if (dot[x1][y] && exist_set.find({x1, y}) == exist_set.end())
            return false;
    }
    return true;
}

// Check condition 2 for a diagonal edge with slope 1
bool check_edge_dots_diag1(int x1, int y1, int x2, int y2,
                           const set<pair<int,int>>& exist_set) {
    int step = x2 - x1;
    int dir = (step > 0) ? 1 : -1;
    for (int t = 0; t != step + dir; t += dir) {
        int x = x1 + t;
        int y = y1 + t;
        if (dot[x][y] && exist_set.find({x, y}) == exist_set.end())
            return false;
    }
    return true;
}

// Check condition 2 for a diagonal edge with slope -1
bool check_edge_dots_diag2(int x1, int y1, int x2, int y2,
                           const set<pair<int,int>>& exist_set) {
    int step = x2 - x1;
    int dir = (step > 0) ? 1 : -1;
    for (int t = 0; t != step + dir; t += dir) {
        int x = x1 + t;
        int y = y1 - t;
        if (dot[x][y] && exist_set.find({x, y}) == exist_set.end())
            return false;
    }
    return true;
}

// Validate an axis-aligned rectangle
bool check_axis_aligned(int x, int y, int dx, int dy,
                        const vector<pair<int,int>>& existing) {
    set<pair<int,int>> exist_set(existing.begin(), existing.end());

    // Edge A-B: (x,y) to (x+dx,y)
    int x1 = x, y1 = y, x2 = x+dx, y2 = y;
    if (!check_edge_dots_horizontal(x1, y1, x2, y2, exist_set)) return false;
    if (check_overlap_horizontal(y1, min(x1, x2), max(x1, x2))) return false;

    // Edge B-C: (x+dx,y) to (x+dx,y+dy)
    x1 = x+dx, y1 = y; x2 = x+dx, y2 = y+dy;
    if (!check_edge_dots_vertical(x1, y1, x2, y2, exist_set)) return false;
    if (check_overlap_vertical(x1, min(y1, y2), max(y1, y2))) return false;

    // Edge C-D: (x+dx,y+dy) to (x,y+dy)
    x1 = x+dx, y1 = y+dy; x2 = x, y2 = y+dy;
    if (!check_edge_dots_horizontal(x1, y1, x2, y2, exist_set)) return false;
    if (check_overlap_horizontal(y1, min(x1, x2), max(x1, x2))) return false;

    // Edge D-A: (x,y+dy) to (x,y)
    x1 = x, y1 = y+dy; x2 = x, y2 = y;
    if (!check_edge_dots_vertical(x1, y1, x2, y2, exist_set)) return false;
    if (check_overlap_vertical(x1, min(y1, y2), max(y1, y2))) return false;

    return true;
}

// Validate a 45-degree rotated rectangle
bool check_45(int x, int y, int d, int e,
              const vector<pair<int,int>>& existing) {
    set<pair<int,int>> exist_set(existing.begin(), existing.end());

    // Edge A-B: (x,y) to (x+d,y+d)
    int x1 = x, y1 = y, x2 = x+d, y2 = y+d;
    if (!check_edge_dots_diag1(x1, y1, x2, y2, exist_set)) return false;
    int id1 = (x1 - y1) + (N-1);
    if (check_overlap_diag1(id1, min(x1, x2), max(x1, x2))) return false;

    // Edge B-C: (x+d,y+d) to (x+d+e,y+d-e)
    x1 = x+d, y1 = y+d; x2 = x+d+e, y2 = y+d-e;
    if (!check_edge_dots_diag2(x1, y1, x2, y2, exist_set)) return false;
    int id2 = x1 + y1;
    if (check_overlap_diag2(id2, min(x1, x2), max(x1, x2))) return false;

    // Edge C-D: (x+d+e,y+d-e) to (x+e,y-e)
    x1 = x+d+e, y1 = y+d-e; x2 = x+e, y2 = y-e;
    if (!check_edge_dots_diag1(x1, y1, x2, y2, exist_set)) return false;
    id1 = (x1 - y1) + (N-1);
    if (check_overlap_diag1(id1, min(x1, x2), max(x1, x2))) return false;

    // Edge D-A: (x+e,y-e) to (x,y)
    x1 = x+e, y1 = y-e; x2 = x, y2 = y;
    if (!check_edge_dots_diag2(x1, y1, x2, y2, exist_set)) return false;
    id2 = x1 + y1;
    if (check_overlap_diag2(id2, min(x1, x2), max(x1, x2))) return false;

    return true;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    // Input
    cin >> N >> M;
    dot.assign(N, vector<bool>(N, false));
    for (int i = 0; i < M; ++i) {
        int x, y;
        cin >> x >> y;
        dot[x][y] = true;
    }

    // Precompute center and weights
    c = (N-1) / 2;
    weight.assign(N, vector<int>(N));
    for (int x = 0; x < N; ++x) {
        for (int y = 0; y < N; ++y) {
            weight[x][y] = compute_weight(x, y);
        }
    }

    // Initialize empty points (excluding initial dots)
    for (int x = 0; x < N; ++x) {
        for (int y = 0; y < N; ++y) {
            if (!dot[x][y]) {
                empty_pts.emplace_back(x, y);
            }
        }
    }
    // Sort empty points by weight descending
    sort(empty_pts.begin(), empty_pts.end(),
         [](const pair<int,int>& a, const pair<int,int>& b) {
             return compute_weight(a.first, a.second) > compute_weight(b.first, b.second);
         });

    // Initialize edge structures
    horz.resize(N);
    vert.resize(N);
    diag1.resize(2 * N - 1);
    diag2.resize(2 * N - 1);

    vector<vector<int>> operations; // each operation: 8 coordinates

    int L = 1;
    const int MAX_L = 20;

    while (true) {
        bool found = false;
        for (size_t idx = 0; idx < empty_pts.size(); ++idx) {
            int x = empty_pts[idx].first;
            int y = empty_pts[idx].second;

            // Try axis-aligned rectangles
            for (int dx = -L; dx <= L && !found; ++dx) {
                if (dx == 0) continue;
                for (int dy = -L; dy <= L && !found; ++dy) {
                    if (dy == 0) continue;
                    int x1 = x + dx, y1 = y;
                    int x2 = x, y2 = y + dy;
                    int x3 = x + dx, y3 = y + dy;
                    if (!inside(x1, y1) || !inside(x2, y2) || !inside(x3, y3)) continue;
                    if (!dot[x1][y1] || !dot[x2][y2] || !dot[x3][y3]) continue;

                    vector<pair<int,int>> existing = {{x1, y1}, {x2, y2}, {x3, y3}};
                    if (check_axis_aligned(x, y, dx, dy, existing)) {
                        // Found a valid rectangle
                        // Output order: new point, then (x+dx,y), (x+dx,y+dy), (x,y+dy)
                        operations.push_back({x, y, x1, y1, x3, y3, x2, y2});
                        dot[x][y] = true;
                        // Update edges
                        add_edge(x, y, x1, y1);
                        add_edge(x1, y1, x3, y3);
                        add_edge(x3, y3, x2, y2);
                        add_edge(x2, y2, x, y);
                        // Remove from empty_pts
                        swap(empty_pts[idx], empty_pts.back());
                        empty_pts.pop_back();
                        found = true;
                        break;
                    }
                }
            }

            if (found) break;

            // Try 45-degree rectangles
            for (int d = -L; d <= L && !found; ++d) {
                if (d == 0) continue;
                for (int e = -L; e <= L && !found; ++e) {
                    if (e == 0) continue;
                    int x1 = x + d, y1 = y + d;
                    int x2 = x + e, y2 = y - e;
                    int x3 = x + d + e, y3 = y + d - e;
                    if (!inside(x1, y1) || !inside(x2, y2) || !inside(x3, y3)) continue;
                    if (!dot[x1][y1] || !dot[x2][y2] || !dot[x3][y3]) continue;

                    vector<pair<int,int>> existing = {{x1, y1}, {x2, y2}, {x3, y3}};
                    if (check_45(x, y, d, e, existing)) {
                        // Found a valid rectangle
                        // Output order: new point, then (x+d,y+d), (x+d+e,y+d-e), (x+e,y-e)
                        operations.push_back({x, y, x1, y1, x3, y3, x2, y2});
                        dot[x][y] = true;
                        // Update edges
                        add_edge(x, y, x1, y1);
                        add_edge(x1, y1, x3, y3);
                        add_edge(x3, y3, x2, y2);
                        add_edge(x2, y2, x, y);
                        // Remove from empty_pts
                        swap(empty_pts[idx], empty_pts.back());
                        empty_pts.pop_back();
                        found = true;
                        break;
                    }
                }
            }

            if (found) break;
        }

        if (!found) {
            L++;
            if (L > MAX_L) break;
        }
    }

    // Output
    cout << operations.size() << "\n";
    for (auto& op : operations) {
        for (int i = 0; i < 8; ++i) {
            if (i) cout << " ";
            cout << op[i];
        }
        cout << "\n";
    }

    return 0;
}