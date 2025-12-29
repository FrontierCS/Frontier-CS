#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <iomanip>
#include <memory>
#include <limits>

// Use long double for precision
using LD = long double;

struct Point {
    LD x, y;
};

struct Segment {
    Point p1, p2;
};

struct BBox {
    LD x0, y0, x1, y1;
};

// --- Geometry utilities ---

inline LD distSq(Point p1, Point p2) {
    return (p1.x - p2.x) * (p1.x - p2.x) + (p1.y - p2.y) * (p1.y - p2.y);
}

inline LD dot(Point p1, Point p2) {
    return p1.x * p2.x + p1.y * p2.y;
}

Point operator-(Point a, Point b) { return {a.x - b.x, a.y - b.y}; }
Point operator+(Point a, Point b) { return {a.x + b.x, a.y + b.y}; }
Point operator*(LD s, Point a) { return {s * a.x, s * a.y}; }

LD dist_point_segment_sq(Point p, const Segment& s) {
    LD l2 = distSq(s.p1, s.p2);
    if (l2 == 0.0) return distSq(p, s.p1);
    LD t = std::max((LD)0.0, std::min((LD)1.0, dot(p - s.p1, s.p2 - s.p1) / l2));
    Point projection = s.p1 + t * (s.p2 - s.p1);
    return distSq(p, projection);
}

// --- Segment Quadtree ---

const int SEG_QT_MAX_DEPTH = 15;
const int SEG_QT_BUCKET_SIZE = 16;

struct SegQuadTreeNode {
    BBox box;
    std::vector<const Segment*> segments;
    std::unique_ptr<SegQuadTreeNode> children[4];
    bool is_leaf = true;

    SegQuadTreeNode(BBox b) : box(b) {}
};

class SegQuadTree {
public:
    SegQuadTree(BBox box) {
        root = std::make_unique<SegQuadTreeNode>(box);
    }

    void insert(const Segment* seg) {
        insert_recursive(root.get(), seg, 0);
    }

    LD nn_search_sq(Point p) const {
        LD min_dist_sq = std::numeric_limits<LD>::max();
        nn_search_recursive(root.get(), p, min_dist_sq);
        return min_dist_sq;
    }

private:
    std::unique_ptr<SegQuadTreeNode> root;

    int get_quadrant(const BBox& node_box, const Segment* seg) const {
        LD mid_x = (node_box.x0 + node_box.x1) / 2.0;
        LD mid_y = (node_box.y0 + node_box.y1) / 2.0;
        
        bool right1 = seg->p1.x >= mid_x, right2 = seg->p2.x >= mid_x;
        bool top1 = seg->p1.y >= mid_y, top2 = seg->p2.y >= mid_y;

        if (right1 == right2 && top1 == top2) {
            return (right1 ? 1 : 0) + (top1 ? 0 : 2);
        }
        return -1;
    }

    void split(SegQuadTreeNode* node, int depth) {
        LD mid_x = (node->box.x0 + node->box.x1) / 2.0;
        LD mid_y = (node->box.y0 + node->box.y1) / 2.0;
        node->is_leaf = false;
        node->children[0] = std::make_unique<SegQuadTreeNode>(BBox{node->box.x0, mid_y, mid_x, node->box.y1}); // TL
        node->children[1] = std::make_unique<SegQuadTreeNode>(BBox{mid_x, mid_y, node->box.x1, node->box.y1}); // TR
        node->children[2] = std::make_unique<SegQuadTreeNode>(BBox{node->box.x0, node->box.y0, mid_x, mid_y}); // BL
        node->children[3] = std::make_unique<SegQuadTreeNode>(BBox{mid_x, node->box.y0, node->box.x1, mid_y}); // BR
        
        std::vector<const Segment*> old_segments = std::move(node->segments);
        node->segments.clear();
        for (const auto& seg : old_segments) {
            insert_recursive(node, seg, depth);
        }
    }

    void insert_recursive(SegQuadTreeNode* node, const Segment* seg, int depth) {
        if (!node->is_leaf) {
            int quadrant = get_quadrant(node->box, seg);
            if (quadrant != -1) {
                insert_recursive(node->children[quadrant].get(), seg, depth + 1);
                return;
            }
        }
        
        node->segments.push_back(seg);

        if (node->is_leaf && node->segments.size() > SEG_QT_BUCKET_SIZE && depth < SEG_QT_MAX_DEPTH) {
            split(node, depth);
        }
    }
    
    LD dist_point_box_sq(Point p, const BBox& box) const {
        LD dx = 0.0, dy = 0.0;
        if (p.x < box.x0) dx = box.x0 - p.x;
        else if (p.x > box.x1) dx = p.x - box.x1;
        if (p.y < box.y0) dy = box.y0 - p.y;
        else if (p.y > box.y1) dy = p.y - box.y1;
        return dx * dx + dy * dy;
    }

    void nn_search_recursive(const SegQuadTreeNode* node, Point p, LD& min_dist_sq) const {
        if (node == nullptr) return;
        
        if (dist_point_box_sq(p, node->box) >= min_dist_sq) {
            return;
        }

        for (const auto& seg : node->segments) {
            LD d_sq = dist_point_segment_sq(p, *seg);
            if (d_sq < min_dist_sq) {
                min_dist_sq = d_sq;
            }
        }
        
        if (!node->is_leaf) {
            std::vector<int> order = {0, 1, 2, 3};
            std::sort(order.begin(), order.end(), [&](int a, int b){
                return dist_point_box_sq(p, node->children[a]->box) < dist_point_box_sq(p, node->children[b]->box);
            });
            for(int i : order) {
                nn_search_recursive(node->children[i].get(), p, min_dist_sq);
            }
        }
    }
};

// --- Adaptive Integration ---

const int INTEGRATION_MAX_DEPTH = 24;
LD r_global;
LD r_global_sq;
const SegQuadTree* seg_tree_global;

LD calculate_area(const BBox& box, int depth) {
    Point center = {(box.x0 + box.x1) / 2.0, (box.y0 + box.y1) / 2.0};
    LD min_dist_sq = seg_tree_global->nn_search_sq(center);
    LD min_dist = sqrt(min_dist_sq);

    LD box_w = box.x1 - box.x0;
    LD box_h = box.y1 - box.y0;
    LD box_diag = sqrt(box_w * box_w + box_h * box_h) / 2.0;

    if (min_dist + box_diag <= r_global) { // Fully inside
        return box_w * box_h;
    }
    if (min_dist - box_diag > r_global) { // Fully outside
        return 0.0;
    }

    if (depth >= INTEGRATION_MAX_DEPTH) {
        return (min_dist_sq <= r_global_sq) ? (box_w * box_h) : 0.0;
    }

    LD area = 0.0;
    LD mid_x = center.x;
    LD mid_y = center.y;
    area += calculate_area({box.x0, mid_y, mid_x, box.y1}, depth + 1); // Top-left
    area += calculate_area({mid_x, mid_y, box.x1, box.y1}, depth + 1); // Top-right
    area += calculate_area({box.x0, box.y0, mid_x, mid_y}, depth + 1); // Bottom-left
    area += calculate_area({mid_x, box.y0, box.x1, mid_y}, depth + 1); // Bottom-right
    return area;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n;
    std::cin >> n;
    std::vector<Point> points(n);
    LD min_x = std::numeric_limits<LD>::max(), max_x = std::numeric_limits<LD>::lowest();
    LD min_y = std::numeric_limits<LD>::max(), max_y = std::numeric_limits<LD>::lowest();
    for (int i = 0; i < n; ++i) {
        double x, y;
        std::cin >> x >> y;
        points[i] = {(LD)x, (LD)y};
        min_x = std::min(min_x, points[i].x);
        max_x = std::max(max_x, points[i].x);
        min_y = std::min(min_y, points[i].y);
        max_y = std::max(max_y, points[i].y);
    }

    int m;
    std::cin >> m;
    std::vector<Segment> segments(m);
    for (int i = 0; i < m; ++i) {
        int u, v;
        std::cin >> u >> v;
        --u; --v;
        segments[i] = {points[u], points[v]};
    }
    
    double r_double;
    std::cin >> r_double;
    r_global = r_double;
    r_global_sq = r_global * r_global;

    double p1, p2, p3, p4;
    std::cin >> p1 >> p2 >> p3 >> p4;

    if (m == 0) {
        std::cout << std::fixed << std::setprecision(7) << 0.0 << std::endl;
        return 0;
    }

    min_x -= r_global;
    max_x += r_global;
    min_y -= r_global;
    max_y += r_global;
    
    LD side = std::max(max_x - min_x, max_y - min_y);
    LD mid_x = (min_x + max_x) / 2.0;
    LD mid_y = (min_y + max_y) / 2.0;
    BBox root_box = {mid_x - side/2.0, mid_y - side/2.0, mid_x + side/2.0, mid_y + side/2.0};
    
    SegQuadTree seg_tree(root_box);
    for (const auto& seg : segments) {
        seg_tree.insert(&seg);
    }
    seg_tree_global = &seg_tree;

    LD total_area = calculate_area(root_box, 0);

    std::cout << std::fixed << std::setprecision(7) << (double)total_area << std::endl;

    return 0;
}