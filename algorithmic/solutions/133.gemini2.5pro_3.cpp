#include <iostream>
#include <vector>
#include <cmath>
#include <iomanip>
#include <random>
#include <algorithm>
#include <memory>
#include <chrono>

// Use double for performance, it should be precise enough
using LD = double;

struct Point {
    LD x, y;
};

LD distSq(Point p1, Point p2) {
    return (p1.x - p2.x) * (p1.x - p2.x) + (p1.y - p2.y) * (p1.y - p2.y);
}

LD distToSegmentSq(Point p, Point a, Point b) {
    LD l2 = distSq(a, b);
    if (l2 == 0.0) return distSq(p, a);
    LD t = ((p.x - a.x) * (b.x - a.x) + (p.y - a.y) * (b.y - a.y)) / l2;
    t = std::max((LD)0.0, std::min((LD)1.0, t));
    Point projection = {a.x + t * (b.x - a.x), a.y + t * (b.y - a.y)};
    return distSq(p, projection);
}

struct Segment {
    Point p1, p2;
    LD min_x, max_x, min_y, max_y;

    void compute_bbox() {
        min_x = std::min(p1.x, p2.x);
        max_x = std::max(p1.x, p2.x);
        min_y = std::min(p1.y, p2.y);
        max_y = std::max(p1.y, p2.y);
    }
};

const int QT_MAX_OBJECTS = 32;
const int QT_MAX_LEVEL = 10;

struct QuadTreeNode {
    LD x1, y1, x2, y2;
    std::vector<Segment*> segments;
    std::unique_ptr<QuadTreeNode> children[4];
    int level;

    QuadTreeNode(int pLevel, LD pX1, LD pY1, LD pX2, LD pY2) :
        x1(pX1), y1(pY1), x2(pX2), y2(pY2), level(pLevel) {}

    void split() {
        LD subWidth = (x2 - x1) / 2.0;
        LD subHeight = (y2 - y1) / 2.0;
        LD midX = x1 + subWidth;
        LD midY = y1 + subHeight;

        children[0] = std::make_unique<QuadTreeNode>(level + 1, x1, midY, midX, y2);
        children[1] = std::make_unique<QuadTreeNode>(level + 1, midX, midY, x2, y2);
        children[2] = std::make_unique<QuadTreeNode>(level + 1, x1, y1, midX, midY);
        children[3] = std::make_unique<QuadTreeNode>(level + 1, midX, y1, x2, midY);
    }

    int getIndex(Segment* seg) {
        int index = -1;
        LD midX = x1 + (x2 - x1) / 2.0;
        LD midY = y1 + (y2 - y1) / 2.0;

        bool topQuadrant = (seg->min_y > midY);
        bool bottomQuadrant = (seg->max_y < midY && seg->p1.y < midY && seg->p2.y < midY);

        if (seg->min_x > midX && seg->p1.x > midX && seg->p2.x > midX) {
            if (topQuadrant) index = 1;
            else if (bottomQuadrant) index = 3;
        } else if (seg->max_x < midX && seg->p1.x < midX && seg->p2.x < midX) {
            if (topQuadrant) index = 0;
            else if (bottomQuadrant) index = 2;
        }
        return index;
    }

    void insert(Segment* seg) {
        if (children[0]) {
            int index = getIndex(seg);
            if (index != -1) {
                children[index]->insert(seg);
                return;
            }
        }

        segments.push_back(seg);

        if (segments.size() > QT_MAX_OBJECTS && level < QT_MAX_LEVEL) {
            if (!children[0]) {
                split();
            }
            int i = 0;
            while (i < segments.size()) {
                int index = getIndex(segments[i]);
                if (index != -1) {
                    children[index]->insert(segments[i]);
                    segments[i] = segments.back();
                    segments.pop_back();
                } else {
                    i++;
                }
            }
        }
    }

    void retrieve_colliding(std::vector<Segment*>& return_segments, LD qx1, LD qy1, LD qx2, LD qy2) {
        if (x2 < qx1 || x1 > qx2 || y2 < qy1 || y1 > qy2) {
            return;
        }

        for (Segment* seg : segments) {
            return_segments.push_back(seg);
        }

        if (children[0]) {
            for(int i=0; i<4; ++i) {
                children[i]->retrieve_colliding(return_segments, qx1, qy1, qx2, qy2);
            }
        }
    }
};

void solve() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n;
    std::cin >> n;
    std::vector<Point> points(n);
    LD min_coord_x = 101.0, max_coord_x = -101.0;
    LD min_coord_y = 101.0, max_coord_y = -101.0;
    for (int i = 0; i < n; ++i) {
        std::cin >> points[i].x >> points[i].y;
        min_coord_x = std::min(min_coord_x, points[i].x);
        max_coord_x = std::max(max_coord_x, points[i].x);
        min_coord_y = std::min(min_coord_y, points[i].y);
        max_coord_y = std::max(max_coord_y, points[i].y);
    }

    int m;
    std::cin >> m;
    std::vector<Segment> segments_storage(m);
    for (int i = 0; i < m; ++i) {
        int u, v;
        std::cin >> u >> v;
        --u; --v;
        segments_storage[i] = {points[u], points[v]};
        segments_storage[i].compute_bbox();
    }

    LD r;
    std::cin >> r;
    LD p1, p2, p3, p4;
    std::cin >> p1 >> p2 >> p3 >> p4;

    min_coord_x -= (r + 1.0); max_coord_x += (r + 1.0);
    min_coord_y -= (r + 1.0); max_coord_y += (r + 1.0);

    QuadTreeNode root(0, min_coord_x, min_coord_y, max_coord_x, max_coord_y);
    for (auto& seg : segments_storage) {
        root.insert(&seg);
    }

    long long N = 40000000;
    if (m > 50000) N = 20000000;
    if (m > 200000) N = 10000000;
    if (m > 1000000) N = 5000000;


    long long covered_count = 0;
    std::mt19937 rng(1337);
    std::uniform_real_distribution<LD> distX(min_coord_x, max_coord_x);
    std::uniform_real_distribution<LD> distY(min_coord_y, max_coord_y);

    LD r_sq = r * r;

    std::vector<Segment*> candidates;
    for (long long i = 0; i < N; ++i) {
        Point p = {distX(rng), distY(rng)};
        
        candidates.clear();
        root.retrieve_colliding(candidates, p.x - r, p.y - r, p.x + r, p.y + r);

        bool covered = false;
        for (Segment* seg : candidates) {
            if (p.x >= seg->min_x - r && p.x <= seg->max_x + r &&
                p.y >= seg->min_y - r && p.y <= seg->max_y + r) {
                if (distToSegmentSq(p, seg->p1, seg->p2) <= r_sq) {
                    covered = true;
                    break;
                }
            }
        }
        if (covered) {
            covered_count++;
        }
    }

    LD total_area = (max_coord_x - min_coord_x) * (max_coord_y - min_coord_y);
    LD estimated_area = total_area * covered_count / N;

    std::cout << std::fixed << std::setprecision(7) << estimated_area << std::endl;
}

int main() {
    solve();
    return 0;
}