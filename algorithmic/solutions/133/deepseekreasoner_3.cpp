#include <bits/stdc++.h>
using namespace std;

const int N_SAMPLES = 20000000; // 20 million samples
const int LEAF_SIZE = 16;       // leaf size for BVH

struct Point {
    double x, y;
};

struct Segment {
    int i, j;          // endpoint indices
    double x1, y1, x2, y2;
    double dx, dy, len_sq;
    double min_x, max_x, min_y, max_y; // extended bounding box
};

vector<Point> pts;
vector<Segment> segs;
double r, r_sqr;

// BVH Node
struct Node {
    double min_x, max_x, min_y, max_y;
    vector<int> seg_indices; // for leaf
    Node *left, *right;
    Node() : left(nullptr), right(nullptr) {}
    ~Node() {
        delete left;
        delete right;
    }
};

// Compute squared distance from point (px,py) to segment s
inline bool point_segment_distance_squared(const Segment& s, double px, double py) {
    if (s.len_sq == 0.0) { // degenerate segment (both endpoints coincide)
        double dx = px - s.x1;
        double dy = py - s.y1;
        return dx*dx + dy*dy <= r_sqr;
    }
    double t = ((px - s.x1)*s.dx + (py - s.y1)*s.dy) / s.len_sq;
    if (t < 0.0) t = 0.0;
    else if (t > 1.0) t = 1.0;
    double proj_x = s.x1 + t * s.dx;
    double proj_y = s.y1 + t * s.dy;
    double dx = px - proj_x;
    double dy = py - proj_y;
    return dx*dx + dy*dy <= r_sqr;
}

// Build BVH recursively on a list of segment indices
Node* build_bvh(vector<int>& indices, int start, int end) {
    Node* node = new Node();
    // compute bounding box of these segments
    double min_x = 1e100, max_x = -1e100, min_y = 1e100, max_y = -1e100;
    for (int i = start; i < end; ++i) {
        const Segment& s = segs[indices[i]];
        min_x = min(min_x, s.min_x);
        max_x = max(max_x, s.max_x);
        min_y = min(min_y, s.min_y);
        max_y = max(max_y, s.max_y);
    }
    node->min_x = min_x; node->max_x = max_x;
    node->min_y = min_y; node->max_y = max_y;

    if (end - start <= LEAF_SIZE) {
        // leaf node
        node->seg_indices.assign(indices.begin()+start, indices.begin()+end);
        return node;
    }

    // choose split axis: the one with larger span of midpoints
    double mid_x_sum = 0.0, mid_y_sum = 0.0;
    for (int i = start; i < end; ++i) {
        const Segment& s = segs[indices[i]];
        mid_x_sum += (s.x1 + s.x2) * 0.5;
        mid_y_sum += (s.y1 + s.y2) * 0.5;
    }
    double mid_x_avg = mid_x_sum / (end-start);
    double mid_y_avg = mid_y_sum / (end-start);
    double var_x = 0.0, var_y = 0.0;
    for (int i = start; i < end; ++i) {
        const Segment& s = segs[indices[i]];
        double mid_x = (s.x1 + s.x2) * 0.5;
        double mid_y = (s.y1 + s.y2) * 0.5;
        var_x += (mid_x - mid_x_avg) * (mid_x - mid_x_avg);
        var_y += (mid_y - mid_y_avg) * (mid_y - mid_y_avg);
    }
    bool split_by_x = (var_x >= var_y);

    // sort indices by the chosen coordinate of the midpoint
    if (split_by_x) {
        sort(indices.begin()+start, indices.begin()+end,
             [](int a, int b) {
                 return (segs[a].x1 + segs[a].x2) < (segs[b].x1 + segs[b].x2);
             });
    } else {
        sort(indices.begin()+start, indices.begin()+end,
             [](int a, int b) {
                 return (segs[a].y1 + segs[a].y2) < (segs[b].y1 + segs[b].y2);
             });
    }

    int mid = (start + end) / 2;
    node->left = build_bvh(indices, start, mid);
    node->right = build_bvh(indices, mid, end);
    return node;
}

// Query BVH: return true if point (px,py) is within distance r of any segment in the subtree
bool query_bvh(Node* node, double px, double py) {
    // minimum squared distance from point to node's bounding box
    double dx = 0.0;
    if (px < node->min_x) dx = node->min_x - px;
    else if (px > node->max_x) dx = px - node->max_x;
    double dy = 0.0;
    if (py < node->min_y) dy = node->min_y - py;
    else if (py > node->max_y) dy = py - node->max_y;
    double d2 = dx*dx + dy*dy;
    if (d2 > r_sqr) return false;

    if (node->left == nullptr) { // leaf
        for (int idx : node->seg_indices) {
            if (point_segment_distance_squared(segs[idx], px, py))
                return true;
        }
        return false;
    }
    return query_bvh(node->left, px, py) || query_bvh(node->right, px, py);
}

int main() {
    // fast I/O
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    cout << fixed << setprecision(7);

    int n;
    cin >> n;
    pts.resize(n);
    double min_x = 1e100, max_x = -1e100, min_y = 1e100, max_y = -1e100;
    for (int i = 0; i < n; ++i) {
        cin >> pts[i].x >> pts[i].y;
        min_x = min(min_x, pts[i].x);
        max_x = max(max_x, pts[i].x);
        min_y = min(min_y, pts[i].y);
        max_y = max(max_y, pts[i].y);
    }

    int m;
    cin >> m;
    segs.resize(m);
    for (int i = 0; i < m; ++i) {
        int a, b;
        cin >> a >> b;
        a--; b--;
        segs[i].i = a; segs[i].j = b;
        segs[i].x1 = pts[a].x; segs[i].y1 = pts[a].y;
        segs[i].x2 = pts[b].x; segs[i].y2 = pts[b].y;
        segs[i].dx = segs[i].x2 - segs[i].x1;
        segs[i].dy = segs[i].y2 - segs[i].y1;
        segs[i].len_sq = segs[i].dx*segs[i].dx + segs[i].dy*segs[i].dy;
    }

    cin >> r;
    double p1, p2, p3, p4;
    cin >> p1 >> p2 >> p3 >> p4; // p2 and p4 are ignored

    if (m == 0) {
        cout << "0.0000000\n";
        return 0;
    }

    r_sqr = r * r;

    // compute extended bounding boxes for each segment
    for (int i = 0; i < m; ++i) {
        Segment& s = segs[i];
        s.min_x = min(s.x1, s.x2) - r;
        s.max_x = max(s.x1, s.x2) + r;
        s.min_y = min(s.y1, s.y2) - r;
        s.max_y = max(s.y1, s.y2) + r;
    }

    // build BVH
    vector<int> seg_indices(m);
    iota(seg_indices.begin(), seg_indices.end(), 0);
    Node* root = build_bvh(seg_indices, 0, m);

    // overall bounding box for sampling (extend by r)
    double box_min_x = min_x - r;
    double box_max_x = max_x + r;
    double box_min_y = min_y - r;
    double box_max_y = max_y + r;
    double box_width = box_max_x - box_min_x;
    double box_height = box_max_y - box_min_y;
    double box_area = box_width * box_height;

    // random number generation
    mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());
    uniform_real_distribution<double> dist_x(box_min_x, box_max_x);
    uniform_real_distribution<double> dist_y(box_min_y, box_max_y);

    int hits = 0;
    for (int i = 0; i < N_SAMPLES; ++i) {
        double x = dist_x(rng);
        double y = dist_y(rng);
        if (query_bvh(root, x, y)) {
            hits++;
        }
    }

    double estimated_area = (double)hits / N_SAMPLES * box_area;
    cout << estimated_area << '\n';

    delete root;
    return 0;
}