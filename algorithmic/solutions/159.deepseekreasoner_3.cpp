#include <iostream>
#include <vector>
#include <queue>
#include <unordered_map>
#include <unordered_set>
#include <algorithm>
#include <cmath>
#include <cassert>

using namespace std;

typedef pair<int, int> Point;

struct Candidate {
    int weight;
    Point p1; // new point
    Point p2, p3, p4; // existing points
    // for priority queue (max-heap)
    bool operator<(const Candidate& other) const {
        return weight < other.weight;
    }
};

// Helper to hash a point
struct PointHash {
    size_t operator()(const Point& p) const {
        return p.first * 100 + p.second;
    }
};

// Helper to compare points
bool operator==(const Point& a, const Point& b) {
    return a.first == b.first && a.second == b.second;
}

// Global variables
int N, M;
double c; // center coordinate
vector<vector<bool>> occ; // occupancy grid
vector<vector<int>> w; // weight grid
vector<Point> occ_list; // list of occupied points

// For quick lookups
unordered_map<int, vector<int>> same_x; // x -> list of y
unordered_map<int, vector<int>> same_y; // y -> list of x

// Drawn segments: for each orientation, map from line identifier to intervals.
// For horizontal: key = y, interval = (x1, x2) with x1 < x2
// For vertical: key = x, interval = (y1, y2) with y1 < y2
// For diagonal slope 1: key = c = y - x, interval = (x1, x2) with x1 < x2
// For diagonal slope -1: key = c = y + x, interval = (x1, x2) with x1 < x2
unordered_map<int, vector<pair<int, int>>> horiz, vert, diag1, diag2;

// Priority queue for candidates
priority_queue<Candidate> cand_pq;

// To avoid duplicate candidates, we store signatures of candidates already pushed.
// Signature: (p1, sorted set of p2,p3,p4). We'll use a string representation.
unordered_set<string> cand_seen;

// For output
vector<Candidate> operations;

// Helper functions
inline bool in_bounds(int x, int y) {
    return 0 <= x && x < N && 0 <= y && y < N;
}

// Check if a segment (excluding endpoints) contains any occupied point.
bool segment_clear(const Point& p, const Point& q) {
    int dx = q.first - p.first;
    int dy = q.second - p.second;
    if (dx == 0) { // vertical
        int x = p.first;
        int y1 = min(p.second, q.second);
        int y2 = max(p.second, q.second);
        for (int y = y1 + 1; y < y2; ++y) {
            if (occ[x][y]) return false;
        }
    } else if (dy == 0) { // horizontal
        int y = p.second;
        int x1 = min(p.first, q.first);
        int x2 = max(p.first, q.first);
        for (int x = x1 + 1; x < x2; ++x) {
            if (occ[x][y]) return false;
        }
    } else if (abs(dx) == abs(dy)) { // diagonal
        int stepx = (dx > 0) ? 1 : -1;
        int stepy = (dy > 0) ? 1 : -1;
        int steps = abs(dx);
        for (int i = 1; i < steps; ++i) {
            int x = p.first + i * stepx;
            int y = p.second + i * stepy;
            if (occ[x][y]) return false;
        }
    } else {
        // Not a valid segment for our rectangles
        return false;
    }
    return true;
}

// Check if a new segment overlaps with any existing segment of same orientation.
bool segment_no_overlap(const Point& p, const Point& q) {
    int x1 = p.first, y1 = p.second;
    int x2 = q.first, y2 = q.second;
    // Ensure p is left/bottom for consistent interval representation.
    if (x1 == x2 && y1 > y2) swap(y1, y2);
    if (y1 == y2 && x1 > x2) swap(x1, x2);

    if (x1 == x2) { // vertical
        int x = x1;
        int y_min = y1, y_max = y2;
        auto it = vert.find(x);
        if (it != vert.end()) {
            for (const auto& iv : it->second) {
                int l = iv.first, r = iv.second;
                if (max(l, y_min) < min(r, y_max)) return false;
            }
        }
    } else if (y1 == y2) { // horizontal
        int y = y1;
        int x_min = x1, x_max = x2;
        auto it = horiz.find(y);
        if (it != horiz.end()) {
            for (const auto& iv : it->second) {
                int l = iv.first, r = iv.second;
                if (max(l, x_min) < min(r, x_max)) return false;
            }
        }
    } else if (y2 - y1 == x2 - x1) { // diagonal slope 1: y-x constant
        int c = y1 - x1;
        int x_min = min(x1, x2), x_max = max(x1, x2);
        auto it = diag1.find(c);
        if (it != diag1.end()) {
            for (const auto& iv : it->second) {
                int l = iv.first, r = iv.second;
                if (max(l, x_min) < min(r, x_max)) return false;
            }
        }
    } else if (y2 - y1 == -(x2 - x1)) { // diagonal slope -1: y+x constant
        int c = y1 + x1;
        int x_min = min(x1, x2), x_max = max(x1, x2);
        auto it = diag2.find(c);
        if (it != diag2.end()) {
            for (const auto& iv : it->second) {
                int l = iv.first, r = iv.second;
                if (max(l, x_min) < min(r, x_max)) return false;
            }
        }
    }
    return true;
}

// Add a segment to the data structures.
void add_segment(const Point& p, const Point& q) {
    int x1 = p.first, y1 = p.second;
    int x2 = q.first, y2 = q.second;
    if (x1 == x2 && y1 > y2) swap(y1, y2);
    if (y1 == y2 && x1 > x2) swap(x1, x2);

    if (x1 == x2) { // vertical
        vert[x1].push_back({y1, y2});
    } else if (y1 == y2) { // horizontal
        horiz[y1].push_back({x1, x2});
    } else if (y2 - y1 == x2 - x1) { // diagonal slope 1
        int c = y1 - x1;
        diag1[c].push_back({min(x1,x2), max(x1,x2)});
    } else if (y2 - y1 == -(x2 - x1)) { // diagonal slope -1
        int c = y1 + x1;
        diag2[c].push_back({min(x1,x2), max(x1,x2)});
    }
}

// Compute the fourth point for axis-aligned rectangle from three points.
// Returns true if the three points form an L-shape (two share x, two share y).
bool axis_aligned_fourth(const Point& a, const Point& b, const Point& c, Point& d) {
    // Check if two share x and two share y.
    vector<int> xs = {a.first, b.first, c.first};
    vector<int> ys = {a.second, b.second, c.second};
    sort(xs.begin(), xs.end());
    sort(ys.begin(), ys.end());
    if (xs[0] == xs[1] && xs[1] != xs[2] && ys[0] == ys[1] && ys[1] != ys[2]) {
        // Two distinct x's and two distinct y's.
        int x1 = xs[0], x2 = xs[2];
        int y1 = ys[0], y2 = ys[2];
        // Determine which corner is missing.
        vector<Point> corners = {{x1,y1}, {x1,y2}, {x2,y1}, {x2,y2}};
        vector<bool> present(4, false);
        for (int i=0; i<4; ++i) {
            if (corners[i] == a || corners[i] == b || corners[i] == c) {
                present[i] = true;
            }
        }
        int missing = -1;
        for (int i=0; i<4; ++i) if (!present[i]) missing = i;
        if (missing == -1) return false; // all present? shouldn't happen.
        d = corners[missing];
        return true;
    }
    return false;
}

// Compute the fourth point for rotated rectangle from three points, assuming one is the right angle.
// Returns true if a valid rotated rectangle is found.
bool rotated_fourth(const Point& a, const Point& b, const Point& c, Point& d) {
    // Try each permutation: a as right angle, then b, then c.
    vector<Point> pts = {a, b, c};
    for (int i=0; i<3; ++i) {
        Point A = pts[i];
        Point B = pts[(i+1)%3];
        Point C = pts[(i+2)%3];
        int dx1 = B.first - A.first;
        int dy1 = B.second - A.second;
        int dx2 = C.first - A.first;
        int dy2 = C.second - A.second;
        if (abs(dx1) != abs(dy1) || abs(dx2) != abs(dy2)) continue;
        if (dx1*dx2 + dy1*dy2 != 0) continue;
        // Compute D = B + C - A
        d = {B.first + dx2, B.second + dy2};
        return true;
    }
    return false;
}

// Generate a signature for a candidate to avoid duplicates.
string cand_signature(const Point& p1, const Point& p2, const Point& p3, const Point& p4) {
    vector<Point> others = {p2, p3, p4};
    sort(others.begin(), others.end());
    string s = to_string(p1.first) + "," + to_string(p1.second);
    for (auto& p : others) {
        s += "|" + to_string(p.first) + "," + to_string(p.second);
    }
    return s;
}

// Evaluate a candidate rectangle defined by three existing points and a missing point.
// If valid, push into priority queue.
void consider_candidate(const Point& p1, const Point& p2, const Point& p3, const Point& p4) {
    // p1 is the missing point (to be placed), p2,p3,p4 are occupied.
    if (!in_bounds(p1.first, p1.second)) return;
    if (occ[p1.first][p1.second]) return; // already occupied
    // Check condition 2: no other dots on perimeter.
    if (!segment_clear(p1, p2)) return;
    if (!segment_clear(p2, p3)) return;
    if (!segment_clear(p3, p4)) return;
    if (!segment_clear(p4, p1)) return;
    // Check condition 3: no overlapping segments.
    if (!segment_no_overlap(p1, p2)) return;
    if (!segment_no_overlap(p2, p3)) return;
    if (!segment_no_overlap(p3, p4)) return;
    if (!segment_no_overlap(p4, p1)) return;

    // Create candidate
    Candidate cand;
    cand.p1 = p1;
    cand.p2 = p2; cand.p3 = p3; cand.p4 = p4;
    cand.weight = w[p1.first][p1.second];

    string sig = cand_signature(p1, p2, p3, p4);
    if (cand_seen.count(sig)) return;
    cand_seen.insert(sig);

    cand_pq.push(cand);
}

// Given three points that are three corners of a rectangle, find the missing corner and call consider_candidate.
void consider_triple(const Point& a, const Point& b, const Point& c) {
    // Try axis-aligned
    Point d;
    if (axis_aligned_fourth(a, b, c, d)) {
        consider_candidate(d, a, b, c);
    }
    // Try rotated
    if (rotated_fourth(a, b, c, d)) {
        consider_candidate(d, a, b, c);
    }
}

// After placing a new point, generate new candidates involving it.
void generate_new_candidates(const Point& new_pt) {
    // Limit search to points within Manhattan distance 10.
    const int MAX_DIST = 10;
    // Iterate over all occupied points except new_pt.
    for (const Point& a : occ_list) {
        if (a == new_pt) continue;
        if (abs(a.first - new_pt.first) + abs(a.second - new_pt.second) > MAX_DIST) continue;
        for (const Point& b : occ_list) {
            if (b == new_pt || b == a) continue;
            if (abs(b.first - new_pt.first) + abs(b.second - new_pt.second) > MAX_DIST) continue;
            // Consider triple (new_pt, a, b)
            consider_triple(new_pt, a, b);
        }
    }
}

// Determine the order of points for output: p1 (new), then p2,p3,p4 such that p1-p2-p3-p4 forms rectangle.
void order_points(Point p1, Point p2, Point p3, Point p4, Point& out_p2, Point& out_p3, Point& out_p4) {
    // Among p2,p3,p4, find the two that are adjacent to p1 (vectors perpendicular) and the opposite.
    vector<Point> others = {p2, p3, p4};
    vector<pair<Point, Point>> vecs; // vector from p1 to point
    for (auto& p : others) {
        vecs.push_back({p, {p.first - p1.first, p.second - p1.second}});
    }
    // Find two vectors that are perpendicular.
    for (int i=0; i<3; ++i) {
        for (int j=i+1; j<3; ++j) {
            int dx1 = vecs[i].second.first, dy1 = vecs[i].second.second;
            int dx2 = vecs[j].second.first, dy2 = vecs[j].second.second;
            if (dx1*dx2 + dy1*dy2 == 0) {
                // These are the sides.
                Point side1 = vecs[i].first;
                Point side2 = vecs[j].first;
                Point opposite = vecs[3-i-j].first; // the remaining point
                // Check that side1 + side2 - p1 == opposite? Actually opposite should be p1 + (side1-p1) + (side2-p1).
                if (opposite.first == p1.first + dx1 + dx2 && opposite.second == p1.second + dy1 + dy2) {
                    out_p2 = side1;
                    out_p3 = opposite;
                    out_p4 = side2;
                    return;
                } else {
                    // Maybe order reversed.
                    out_p2 = side2;
                    out_p3 = opposite;
                    out_p4 = side1;
                    return;
                }
            }
        }
    }
    // If not found (should not happen for valid rectangle), just keep original order.
    out_p2 = p2;
    out_p3 = p3;
    out_p4 = p4;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    // Read input
    cin >> N >> M;
    occ.assign(N, vector<bool>(N, false));
    w.assign(N, vector<int>(N, 0));
    c = (N-1)/2.0;
    for (int i=0; i<N; ++i) {
        for (int j=0; j<N; ++j) {
            w[i][j] = (i-c)*(i-c) + (j-c)*(j-c) + 1; // weight
        }
    }
    for (int i=0; i<M; ++i) {
        int x, y;
        cin >> x >> y;
        occ[x][y] = true;
        occ_list.push_back({x, y});
        same_x[x].push_back(y);
        same_y[y].push_back(x);
    }

    // Initial candidate generation: all triples of occupied points.
    int O = occ_list.size();
    for (int i=0; i<O; ++i) {
        for (int j=i+1; j<O; ++j) {
            for (int k=j+1; k<O; ++k) {
                consider_triple(occ_list[i], occ_list[j], occ_list[k]);
            }
        }
    }

    // Main loop
    while (!cand_pq.empty()) {
        Candidate cand = cand_pq.top();
        cand_pq.pop();
        Point p1 = cand.p1;
        if (occ[p1.first][p1.second]) continue; // already occupied
        // Re-check conditions (segments may have been added)
        if (!segment_no_overlap(p1, cand.p2) ||
            !segment_no_overlap(cand.p2, cand.p3) ||
            !segment_no_overlap(cand.p3, cand.p4) ||
            !segment_no_overlap(cand.p4, p1)) {
            continue;
        }
        if (!segment_clear(p1, cand.p2) ||
            !segment_clear(cand.p2, cand.p3) ||
            !segment_clear(cand.p3, cand.p4) ||
            !segment_clear(cand.p4, p1)) {
            continue;
        }
        // Valid rectangle found.
        // Order points correctly.
        Point p2, p3, p4;
        order_points(p1, cand.p2, cand.p3, cand.p4, p2, p3, p4);
        operations.push_back({cand.weight, p1, p2, p3, p4});

        // Update state
        occ[p1.first][p1.second] = true;
        occ_list.push_back(p1);
        same_x[p1.first].push_back(p1.second);
        same_y[p1.second].push_back(p1.first);

        // Add segments
        add_segment(p1, p2);
        add_segment(p2, p3);
        add_segment(p3, p4);
        add_segment(p4, p1);

        // Generate new candidates involving p1
        generate_new_candidates(p1);
    }

    // Output
    cout << operations.size() << '\n';
    for (const auto& op : operations) {
        cout << op.p1.first << ' ' << op.p1.second << ' '
             << op.p2.first << ' ' << op.p2.second << ' '
             << op.p3.first << ' ' << op.p3.second << ' '
             << op.p4.first << ' ' << op.p4.second << '\n';
    }

    return 0;
}