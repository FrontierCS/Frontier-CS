#include <iostream>
#include <vector>
#include <algorithm>
#include <cmath>
#include <cfloat>
#include <cstring>

using namespace std;

const double INF = 1e100;
const double EPS = 1e-9;
const int LEAF_SIZE = 10;
const int MAX_DEPTH = 20;

struct Point {
    double x, y;
    Point() {}
    Point(double x_, double y_) : x(x_), y(y_) {}
};

struct Segment {
    Point a, b;
    double minx, miny, maxx, maxy;  // expanded bounding box
};

vector<Point> pts;
vector<Segment> segs;
double r;

// ----- geometry utilities -----

double dot(const Point& a, const Point& b) {
    return a.x * b.x + a.y * b.y;
}

double cross(const Point& a, const Point& b) {
    return a.x * b.y - a.y * b.x;
}

double dist2(const Point& a, const Point& b) {
    double dx = a.x - b.x, dy = a.y - b.y;
    return dx*dx + dy*dy;
}

double distPointToPoint(const Point& a, const Point& b) {
    return sqrt(dist2(a,b));
}

bool onSegment(const Point& p, const Point& q, const Point& r) {
    return q.x <= max(p.x, r.x) + EPS && q.x >= min(p.x, r.x) - EPS &&
           q.y <= max(p.y, r.y) + EPS && q.y >= min(p.y, r.y) - EPS;
}

int orientation(const Point& p, const Point& q, const Point& r) {
    double val = (q.y - p.y) * (r.x - q.x) - (q.x - p.x) * (r.y - q.y);
    if (fabs(val) < EPS) return 0;
    return (val > 0) ? 1 : 2;
}

bool segmentsIntersect(const Point& p1, const Point& q1,
                       const Point& p2, const Point& q2) {
    int o1 = orientation(p1, q1, p2);
    int o2 = orientation(p1, q1, q2);
    int o3 = orientation(p2, q2, p1);
    int o4 = orientation(p2, q2, q1);
    if (o1 != o2 && o3 != o4) return true;
    if (o1 == 0 && onSegment(p1, p2, q1)) return true;
    if (o2 == 0 && onSegment(p1, q2, q1)) return true;
    if (o3 == 0 && onSegment(p2, p1, q2)) return true;
    if (o4 == 0 && onSegment(p2, q1, q2)) return true;
    return false;
}

double distPointToSegment(const Point& p, const Segment& s) {
    const Point& a = s.a, b = s.b;
    double l2 = dist2(a, b);
    if (l2 == 0) return distPointToPoint(p, a);
    double t = dot({p.x - a.x, p.y - a.y}, {b.x - a.x, b.y - a.y}) / l2;
    if (t < 0) return distPointToPoint(p, a);
    if (t > 1) return distPointToPoint(p, b);
    Point proj = {a.x + t * (b.x - a.x), a.y + t * (b.y - a.y)};
    return distPointToPoint(p, proj);
}

double distSegmentToSegment(const Segment& s1, const Segment& s2) {
    if (segmentsIntersect(s1.a, s1.b, s2.a, s2.b)) return 0.0;
    double d1 = distPointToSegment(s1.a, s2);
    double d2 = distPointToSegment(s1.b, s2);
    double d3 = distPointToSegment(s2.a, s1);
    double d4 = distPointToSegment(s2.b, s1);
    return min(min(d1, d2), min(d3, d4));
}

double distSegmentToRectangle(const Segment& seg,
                              double x1, double y1,
                              double x2, double y2) {
    // Check if segment endpoint inside rectangle
    if ((seg.a.x >= x1 - EPS && seg.a.x <= x2 + EPS &&
         seg.a.y >= y1 - EPS && seg.a.y <= y2 + EPS) ||
        (seg.b.x >= x1 - EPS && seg.b.x <= x2 + EPS &&
         seg.b.y >= y1 - EPS && seg.b.y <= y2 + EPS)) {
        return 0.0;
    }
    // Rectangle edges as segments
    Segment edges[4] = {
        { {x1, y1}, {x2, y1} },
        { {x2, y1}, {x2, y2} },
        { {x2, y2}, {x1, y2} },
        { {x1, y2}, {x1, y1} }
    };
    // Check intersection with each edge
    for (int i = 0; i < 4; ++i) {
        if (segmentsIntersect(seg.a, seg.b, edges[i].a, edges[i].b))
            return 0.0;
    }
    double min_d = INF;
    for (int i = 0; i < 4; ++i) {
        double d = distSegmentToSegment(seg, edges[i]);
        if (d < min_d) min_d = d;
    }
    return min_d;
}

// ----- distance between axis-aligned boxes -----

double distPointToBox(double x, double y,
                      double bx1, double by1, double bx2, double by2) {
    if (x < bx1) {
        if (y < by1) return hypot(bx1 - x, by1 - y);
        else if (y > by2) return hypot(bx1 - x, y - by2);
        else return bx1 - x;
    } else if (x > bx2) {
        if (y < by1) return hypot(x - bx2, by1 - y);
        else if (y > by2) return hypot(x - bx2, y - by2);
        else return x - bx2;
    } else {
        if (y < by1) return by1 - y;
        else if (y > by2) return y - by2;
        else return 0.0;
    }
}

double distRectToBox(double x1, double y1, double x2, double y2,
                     double bx1, double by1, double bx2, double by2) {
    if (x2 < bx1) { // left
        if (y2 < by1) return hypot(bx1 - x2, by1 - y2);
        else if (y1 > by2) return hypot(bx1 - x2, y1 - by2);
        else return bx1 - x2;
    } else if (x1 > bx2) { // right
        if (y2 < by1) return hypot(x1 - bx2, by1 - y2);
        else if (y1 > by2) return hypot(x1 - bx2, y1 - by2);
        else return x1 - bx2;
    } else { // x overlap
        if (y2 < by1) return by1 - y2;
        else if (y1 > by2) return y1 - by2;
        else return 0.0;
    }
}

// ----- KD-tree -----

struct KDNode {
    double minx, miny, maxx, maxy;
    KDNode *left, *right;
    vector<int> segs; // indices in segs
    KDNode() : left(nullptr), right(nullptr) {}
};

KDNode* buildKDTree(vector<int>& seg_ids, int depth) {
    if (seg_ids.empty()) return nullptr;
    KDNode* node = new KDNode();
    // compute bounding box
    node->minx = segs[seg_ids[0]].minx;
    node->miny = segs[seg_ids[0]].miny;
    node->maxx = segs[seg_ids[0]].maxx;
    node->maxy = segs[seg_ids[0]].maxy;
    for (int id : seg_ids) {
        const Segment& s = segs[id];
        node->minx = min(node->minx, s.minx);
        node->miny = min(node->miny, s.miny);
        node->maxx = max(node->maxx, s.maxx);
        node->maxy = max(node->maxy, s.maxy);
    }
    if ((int)seg_ids.size() <= LEAF_SIZE) {
        node->segs = seg_ids;
        return node;
    }
    // choose split dimension
    int dim = depth % 2; // 0 for x, 1 for y
    // compute median of centers
    vector<double> vals;
    for (int id : seg_ids) {
        const Segment& s = segs[id];
        double center = (dim == 0) ? (s.minx + s.maxx) / 2 : (s.miny + s.maxy) / 2;
        vals.push_back(center);
    }
    auto mid_it = vals.begin() + vals.size() / 2;
    nth_element(vals.begin(), mid_it, vals.end());
    double median = *mid_it;
    vector<int> left_ids, right_ids;
    for (int id : seg_ids) {
        const Segment& s = segs[id];
        double center = (dim == 0) ? (s.minx + s.maxx) / 2 : (s.miny + s.maxy) / 2;
        if (center <= median)
            left_ids.push_back(id);
        else
            right_ids.push_back(id);
    }
    // to avoid infinite recursion, ensure both non-empty
    if (left_ids.empty() || right_ids.empty()) {
        node->segs = seg_ids;
        return node;
    }
    node->left = buildKDTree(left_ids, depth+1);
    node->right = buildKDTree(right_ids, depth+1);
    return node;
}

void queryRect(KDNode* node, double x1, double y1, double x2, double y2, double& best) {
    if (!node) return;
    double d_box = distRectToBox(x1, y1, x2, y2,
                                 node->minx, node->miny,
                                 node->maxx, node->maxy);
    if (d_box >= best) return;
    if (node->left) {
        queryRect(node->left, x1, y1, x2, y2, best);
        queryRect(node->right, x1, y1, x2, y2, best);
    } else {
        for (int id : node->segs) {
            double d = distSegmentToRectangle(segs[id], x1, y1, x2, y2);
            if (d < best) best = d;
            if (best == 0.0) return;
        }
    }
}

void queryPoint(KDNode* node, double x, double y, double& best) {
    if (!node) return;
    double d_box = distPointToBox(x, y,
                                  node->minx, node->miny,
                                  node->maxx, node->maxy);
    if (d_box >= best) return;
    if (node->left) {
        queryPoint(node->left, x, y, best);
        queryPoint(node->right, x, y, best);
    } else {
        for (int id : node->segs) {
            double d = distPointToSegment(Point(x,y), segs[id]);
            if (d < best) best = d;
            if (best == 0.0) return;
        }
    }
}

// ----- recursive area computation -----

double computeArea(double x1, double y1, double x2, double y2, int depth, KDNode* root) {
    double area = (x2 - x1) * (y2 - y1);
    if (area < 1e-12) {
        // very small cell: check center
        double cx = (x1 + x2) / 2, cy = (y1 + y2) / 2;
        double d = INF;
        queryPoint(root, cx, cy, d);
        return (d <= r) ? area : 0.0;
    }
    if (depth >= MAX_DEPTH) {
        // depth limit: approximate by center
        double cx = (x1 + x2) / 2, cy = (y1 + y2) / 2;
        double d = INF;
        queryPoint(root, cx, cy, d);
        return (d <= r) ? area : 0.0;
    }
    double min_dist = INF;
    queryRect(root, x1, y1, x2, y2, min_dist);
    if (min_dist > r) return 0.0;
    Point corners[4] = { {x1,y1}, {x2,y1}, {x1,y2}, {x2,y2} };
    double d_corner[4];
    for (int i = 0; i < 4; ++i) {
        d_corner[i] = INF;
        queryPoint(root, corners[i].x, corners[i].y, d_corner[i]);
    }
    double max_corner_dist = 0.0;
    for (int i = 0; i < 4; ++i)
        max_corner_dist = max(max_corner_dist, d_corner[i]);
    double diag = hypot(x2 - x1, y2 - y1);
    if (max_corner_dist + diag <= r) return area;
    // subdivide
    double mx = (x1 + x2) / 2, my = (y1 + y2) / 2;
    double total = 0.0;
    total += computeArea(x1, y1, mx, my, depth+1, root);
    total += computeArea(mx, y1, x2, my, depth+1, root);
    total += computeArea(x1, my, mx, y2, depth+1, root);
    total += computeArea(mx, my, x2, y2, depth+1, root);
    return total;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);

    int n;
    cin >> n;
    pts.resize(n);
    for (int i = 0; i < n; ++i)
        cin >> pts[i].x >> pts[i].y;

    int m;
    cin >> m;
    segs.resize(m);
    for (int i = 0; i < m; ++i) {
        int a, b;
        cin >> a >> b;
        --a; --b;
        segs[i].a = pts[a];
        segs[i].b = pts[b];
        // expanded bounding box
        double x1 = min(segs[i].a.x, segs[i].b.x);
        double x2 = max(segs[i].a.x, segs[i].b.x);
        double y1 = min(segs[i].a.y, segs[i].b.y);
        double y2 = max(segs[i].a.y, segs[i].b.y);
        segs[i].minx = x1 - r;
        segs[i].maxx = x2 + r;
        segs[i].miny = y1 - r;
        segs[i].maxy = y2 + r;
    }

    cin >> r;
    // Update expanded bounding boxes with the now known r
    for (int i = 0; i < m; ++i) {
        double x1 = min(segs[i].a.x, segs[i].b.x);
        double x2 = max(segs[i].a.x, segs[i].b.x);
        double y1 = min(segs[i].a.y, segs[i].b.y);
        double y2 = max(segs[i].a.y, segs[i].b.y);
        segs[i].minx = x1 - r;
        segs[i].maxx = x2 + r;
        segs[i].miny = y1 - r;
        segs[i].maxy = y2 + r;
    }

    double p1, p2, p3, p4;
    cin >> p1 >> p2 >> p3 >> p4; // only used for scoring

    if (m == 0) {
        cout << "0.0\n";
        return 0;
    }

    // Build KD-tree
    vector<int> seg_ids(m);
    for (int i = 0; i < m; ++i) seg_ids[i] = i;
    KDNode* root = buildKDTree(seg_ids, 0);

    // Compute global bounding box (points expanded by r)
    double xmin = pts[0].x, xmax = pts[0].x, ymin = pts[0].y, ymax = pts[0].y;
    for (int i = 1; i < n; ++i) {
        xmin = min(xmin, pts[i].x);
        xmax = max(xmax, pts[i].x);
        ymin = min(ymin, pts[i].y);
        ymax = max(ymax, pts[i].y);
    }
    xmin -= r; xmax += r;
    ymin -= r; ymax += r;

    double area = computeArea(xmin, ymin, xmax, ymax, 0, root);

    cout.precision(10);
    cout << fixed << area << endl;

    // Note: KD-tree memory not freed for brevity.
    return 0;
}