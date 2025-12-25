#include <iostream>
#include <vector>
#include <array>
#include <queue>
#include <algorithm>
#include <tuple>
#include <cassert>
#include <bitset>

using namespace std;

const int MAX_N = 61;

int N, M;
vector<vector<bool>> dot;
vector<vector<int>> weight;
int c;

// Data structures for dots
vector<uint64_t> row_mask;  // bit x set if dot at (x,y)
vector<uint64_t> col_mask;  // bit y set if dot at (x,y)
vector<vector<int>> rows;   // sorted x per row
vector<vector<int>> cols;   // sorted y per column
vector<vector<int>> diag1;  // sorted x per diagonal d = x-y, index d+offset
vector<vector<int>> diag2;  // sorted x per diagonal s = x+y
int d_offset;

// Data structures for drawn edges
vector<vector<pair<int,int>>> horiz_edges; // for each y, list of (x1,x2) with x1<x2
vector<vector<pair<int,int>>> vert_edges;  // for each x, list of (y1,y2)
vector<vector<pair<int,int>>> diag1_edges; // for each d (index d+offset), list of (x1,x2)
vector<vector<pair<int,int>>> diag2_edges; // for each s, list of (x1,x2)

vector<array<array<int,2>,4>> operations; // stored operations

// Helper functions
inline bool in_grid(int x, int y) {
    return 0 <= x && x < N && 0 <= y && y < N;
}

// Check if interval [a,b] (a<b) overlaps with any interval in 'intervals'
bool overlaps(const vector<pair<int,int>>& intervals, int a, int b) {
    if (a > b) swap(a, b);
    for (const auto& [c, d] : intervals) {
        if (max(a, c) < min(b, d)) return true;
    }
    return false;
}

void add_interval(vector<pair<int,int>>& intervals, int a, int b) {
    if (a > b) swap(a, b);
    intervals.emplace_back(a, b);
}

// Check if row y has a dot between x1 and x2 (exclusive)
bool row_has_dot_between(int y, int x1, int x2) {
    if (x1 > x2) swap(x1, x2);
    if (x2 - x1 <= 1) return false;
    uint64_t mask = ((1ULL << x2) - 1) ^ ((1ULL << (x1+1)) - 1);
    return (row_mask[y] & mask) != 0;
}

// Check if column x has a dot between y1 and y2 (exclusive)
bool col_has_dot_between(int x, int y1, int y2) {
    if (y1 > y2) swap(y1, y2);
    if (y2 - y1 <= 1) return false;
    uint64_t mask = ((1ULL << y2) - 1) ^ ((1ULL << (y1+1)) - 1);
    return (col_mask[x] & mask) != 0;
}

// Find a valid rectangle that places a new dot at (x,y)
vector<array<int,2>> find_rectangle(int x, int y) {
    // ---------- Axis-aligned rectangles ----------
    const vector<int>& row_dots = rows[y];
    const vector<int>& col_dots = cols[x];
    for (int x2 : row_dots) {
        if (x2 == x) continue;
        uint64_t mask_x2 = col_mask[x2];
        for (int y4 : col_dots) {
            if (y4 == y) continue;
            if (!(mask_x2 & (1ULL << y4))) continue;
            // Found three dots: (x2,y), (x2,y4), (x,y4)
            int minx = min(x, x2);
            int maxx = max(x, x2);
            int miny = min(y, y4);
            int maxy = max(y, y4);
            // Check perimeter dots
            if (row_has_dot_between(miny, minx, maxx)) continue;
            if (row_has_dot_between(maxy, minx, maxx)) continue;
            if (col_has_dot_between(minx, miny, maxy)) continue;
            if (col_has_dot_between(maxx, miny, maxy)) continue;
            // Check edges overlap
            if (overlaps(horiz_edges[y], minx, maxx)) continue;
            if (overlaps(vert_edges[x2], miny, maxy)) continue;
            if (overlaps(horiz_edges[y4], minx, maxx)) continue;
            if (overlaps(vert_edges[x], miny, maxy)) continue;
            // Valid rectangle
            return {{x, y}, {x2, y}, {x2, y4}, {x, y4}};
        }
    }

    // ---------- 45-degree rectangles ----------
    int d1 = x - y;
    int s2 = x + y;
    const vector<int>& diag1_list = diag1[d1 + d_offset];
    const vector<int>& diag2_list = diag2[s2];
    for (int x2 : diag1_list) {
        if (x2 == x) continue;
        int a = x2 - x;
        int y2 = y + a;  // because on same diagonal x-y = d1
        if (!in_grid(x2, y2)) continue;
        for (int x4 : diag2_list) {
            if (x4 == x) continue;
            int b = x4 - x;
            int y4 = s2 - x4;
            if (!in_grid(x4, y4)) continue;
            int x3 = x2 + b;
            int y3 = y2 - b;
            if (!in_grid(x3, y3)) continue;
            if (!dot[x3][y3]) continue;
            // Check perimeter dots on the four edges
            bool ok = true;
            // Edge p1-p2
            int step_a = (a > 0) ? 1 : -1;
            for (int t = step_a; t != a; t += step_a) {
                int xt = x + t;
                int yt = y + t;
                if (dot[xt][yt]) { ok = false; break; }
            }
            if (!ok) continue;
            // Edge p2-p3
            int step_b = (b > 0) ? 1 : -1;
            for (int t = step_b; t != b; t += step_b) {
                int xt = x2 + t;
                int yt = y2 - t;
                if (dot[xt][yt]) { ok = false; break; }
            }
            if (!ok) continue;
            // Edge p3-p4
            for (int t = step_a; abs(t) < abs(a); t += step_a) {
                int xt = x4 + t;
                int yt = y4 + t;
                if (dot[xt][yt]) { ok = false; break; }
            }
            if (!ok) continue;
            // Edge p4-p1
            for (int t = step_b; abs(t) < abs(b); t += step_b) {
                int xt = x + t;
                int yt = y - t;
                if (dot[xt][yt]) { ok = false; break; }
            }
            if (!ok) continue;
            // Check edges overlap
            // p1-p2 on diag1
            if (overlaps(diag1_edges[d1 + d_offset], min(x, x2), max(x, x2))) continue;
            // p2-p3 on diag2 with s = x2+y2
            int s2p = x2 + y2;
            if (overlaps(diag2_edges[s2p], min(x2, x3), max(x2, x3))) continue;
            // p3-p4 on diag1 with d' = x3-y3
            int d1p = x3 - y3;
            if (overlaps(diag1_edges[d1p + d_offset], min(x3, x4), max(x3, x4))) continue;
            // p4-p1 on diag2 with s = x+y
            if (overlaps(diag2_edges[s2], min(x, x4), max(x, x4))) continue;
            // Valid rectangle
            return {{x, y}, {x2, y2}, {x3, y3}, {x4, y4}};
        }
    }
    return {};
}

// Add a rectangle and update all data structures
void add_rectangle(const vector<array<int,2>>& rect) {
    int x = rect[0][0], y = rect[0][1];
    dot[x][y] = true;
    // Update row_mask and rows
    row_mask[y] |= (1ULL << x);
    auto it = lower_bound(rows[y].begin(), rows[y].end(), x);
    rows[y].insert(it, x);
    // Update col_mask and cols
    col_mask[x] |= (1ULL << y);
    it = lower_bound(cols[x].begin(), cols[x].end(), y);
    cols[x].insert(it, y);
    // Update diag1
    int d1 = x - y;
    auto& d1list = diag1[d1 + d_offset];
    it = lower_bound(d1list.begin(), d1list.end(), x);
    d1list.insert(it, x);
    // Update diag2
    int s2 = x + y;
    auto& d2list = diag2[s2];
    it = lower_bound(d2list.begin(), d2list.end(), x);
    d2list.insert(it, x);

    // Add edges
    for (int i = 0; i < 4; ++i) {
        int j = (i+1) % 4;
        int x1 = rect[i][0], y1 = rect[i][1];
        int x2 = rect[j][0], y2 = rect[j][1];
        if (x1 == x2) { // vertical edge
            add_interval(vert_edges[x1], y1, y2);
        } else if (y1 == y2) { // horizontal edge
            add_interval(horiz_edges[y1], x1, x2);
        } else if (abs(x1 - x2) == abs(y1 - y2)) {
            if (x1 - y1 == x2 - y2) { // slope 1
                int d = x1 - y1;
                add_interval(diag1_edges[d + d_offset], x1, x2);
            } else { // slope -1
                int s = x1 + y1;
                add_interval(diag2_edges[s], x1, x2);
            }
        }
    }
}

// Push all empty points that share row/col/diag with (px,py) into the priority queue
void push_neighbors(int px, int py, priority_queue<tuple<int,int,int>>& pq) {
    // row py
    for (int nx = 0; nx < N; ++nx) {
        if (!dot[nx][py]) {
            pq.emplace(weight[nx][py], nx, py);
        }
    }
    // column px
    for (int ny = 0; ny < N; ++ny) {
        if (!dot[px][ny]) {
            pq.emplace(weight[px][ny], px, ny);
        }
    }
    // diag1: px-py
    int d1 = px - py;
    for (int xd = max(0, d1); xd < min(N, N+d1); ++xd) {
        int yd = xd - d1;
        if (!dot[xd][yd]) {
            pq.emplace(weight[xd][yd], xd, yd);
        }
    }
    // diag2: px+py
    int s2 = px + py;
    for (int xd = max(0, s2 - (N-1)); xd < min(N, s2+1); ++xd) {
        int yd = s2 - xd;
        if (!dot[xd][yd]) {
            pq.emplace(weight[xd][yd], xd, yd);
        }
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    cin >> N >> M;
    c = (N-1)/2;

    // Initialize data structures
    dot.assign(N, vector<bool>(N, false));
    weight.assign(N, vector<int>(N, 0));
    row_mask.assign(N, 0);
    col_mask.assign(N, 0);
    rows.resize(N);
    cols.resize(N);
    d_offset = N-1;
    diag1.resize(2*N-1);
    diag2.resize(2*N-1);
    horiz_edges.resize(N);
    vert_edges.resize(N);
    diag1_edges.resize(2*N-1);
    diag2_edges.resize(2*N-1);

    // Precompute weights
    for (int x = 0; x < N; ++x) {
        for (int y = 0; y < N; ++y) {
            int dx = x - c;
            int dy = y - c;
            weight[x][y] = dx*dx + dy*dy + 1;
        }
    }

    // Read initial dots
    for (int i = 0; i < M; ++i) {
        int x, y;
        cin >> x >> y;
        dot[x][y] = true;
        row_mask[y] |= (1ULL << x);
        col_mask[x] |= (1ULL << y);
        rows[y].push_back(x);
        cols[x].push_back(y);
        int d1 = x - y;
        diag1[d1 + d_offset].push_back(x);
        int s2 = x + y;
        diag2[s2].push_back(x);
    }
    // Sort the lists
    for (int i = 0; i < N; ++i) {
        sort(rows[i].begin(), rows[i].end());
        sort(cols[i].begin(), cols[i].end());
    }
    for (int i = 0; i < 2*N-1; ++i) {
        sort(diag1[i].begin(), diag1[i].end());
        sort(diag2[i].begin(), diag2[i].end());
    }

    // Priority queue: max-heap by weight
    priority_queue<tuple<int,int,int>> pq; // (weight, x, y)
    for (int x = 0; x < N; ++x) {
        for (int y = 0; y < N; ++y) {
            if (!dot[x][y]) {
                pq.emplace(weight[x][y], x, y);
            }
        }
    }

    // Main loop
    while (!pq.empty()) {
        auto [w, x, y] = pq.top();
        pq.pop();
        if (dot[x][y]) continue; // already a dot
        auto rect = find_rectangle(x, y);
        if (rect.empty()) continue;
        operations.push_back({rect[0], rect[1], rect[2], rect[3]});
        add_rectangle(rect);
        // Push neighbors of all four corners
        for (const auto& p : rect) {
            push_neighbors(p[0], p[1], pq);
        }
    }

    // Output
    cout << operations.size() << '\n';
    for (const auto& op : operations) {
        for (int i = 0; i < 4; ++i) {
            cout << op[i][0] << ' ' << op[i][1];
            if (i < 3) cout << ' ';
        }
        cout << '\n';
    }

    return 0;
}