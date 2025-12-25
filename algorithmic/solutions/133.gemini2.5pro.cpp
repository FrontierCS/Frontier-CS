#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <iomanip>
#include <set>

const long double PI = acosl(-1.0L);
const long double EPS = 1e-12;

struct Point {
    long double x, y;
};

Point operator+(Point a, Point b) { return {a.x + b.x, a.y + b.y}; }
Point operator-(Point a, Point b) { return {a.x - b.x, a.y - b.y}; }
Point operator*(Point a, long double s) { return {a.x * s, a.y * s}; }
Point operator/(Point a, long double s) { return {a.x / s, a.y / s}; }
long double dot(Point a, Point b) { return a.x * b.x + a.y * b.y; }
long double cross(Point a, Point b) { return a.x * b.y - a.y * b.x; }
long double norm_sq(Point a) { return dot(a, a); }
long double norm(Point a) { return sqrtl(norm_sq(a)); }
Point normalize(Point a) { long double l = norm(a); return l > EPS ? a / l : Point{0,0}; }
Point rotate(Point a, long double angle) {
    long double c = cosl(angle), s = sinl(angle);
    return {a.x * c - a.y * s, a.x * s + a.y * c};
}

long double rot_angle;
Point transform(Point p) { return rotate(p, rot_angle); }

struct Circle { Point c; long double r; };
struct Segment { Point p1, p2; };

enum CurveType { ARC, LINE };

struct Curve {
    CurveType type;
    Point center; long double r; // For ARC
    Point p1, p2, vec;           // For LINE
    long double x_min, x_max;
    int sign; // +1 for upper, -1 for lower

    long double y(long double x) const {
        if (type == ARC) {
            long double dx = x - center.x;
            long double dy_sq = r * r - dx * dx;
            return center.y + sign * sqrtl(std::max(0.0L, dy_sq));
        } else {
            return p1.y + (x - p1.x) * vec.y / vec.x;
        }
    }

    long double integral(long double x) const {
        if (type == ARC) {
            long double dx = x - center.x;
            if (std::abs(dx) > r) dx = std::copysign(r, dx);
            return center.y * x + sign * (dx * sqrtl(std::max(0.0L, r * r - dx * dx)) + r * r * asinl(dx / r)) / 2.0L;
        } else {
            long double m = vec.y / vec.x;
            long double b = p1.y - m * p1.x;
            return m * x * x / 2.0L + b * x;
        }
    }
    
    long double get_area(long double x1, long double x2) const {
        return integral(x2) - integral(x1);
    }
};

std::vector<Curve> curves;
long double current_x;

struct CurveCmp {
    bool operator()(int i, int j) const {
        long double yi = curves[i].y(current_x);
        long double yj = curves[j].y(current_x);
        if (std::abs(yi - yj) > EPS) {
            return yi < yj;
        }
        long double dx = EPS * 100;
        yi = curves[i].y(current_x + dx);
        yj = curves[j].y(current_x + dx);
        return yi < yj;
    }
};

std::vector<Point> intersect_circle_circle(Circle c1, Circle c2) {
    std::vector<Point> res;
    long double d_sq = norm_sq(c1.c - c2.c);
    if (d_sq < EPS*EPS) return res;
    long double d = sqrtl(d_sq);
    if (d > c1.r + c2.r + EPS || d < std::abs(c1.r - c2.r) - EPS) return res;

    long double a = (d_sq + c1.r * c1.r - c2.r * c2.r) / (2 * d);
    long double h = sqrtl(std::max(0.0L, c1.r * c1.r - a * a));
    Point v = (c2.c - c1.c) / d;
    Point mid = c1.c + v * a;
    
    res.push_back(mid + rotate(v, PI / 2) * h);
    if (h > EPS) res.push_back(mid - rotate(v, PI / 2) * h);
    return res;
}

std::vector<Point> intersect_line_circle(Point p1, Point p2, Circle c) {
    std::vector<Point> res;
    Point p1_c = p1 - c.c;
    Point p2_c = p2 - c.c;
    Point vec = p2_c - p1_c;
    long double a = norm_sq(vec);
    long double b = 2 * dot(p1_c, vec);
    long double C = norm_sq(p1_c) - c.r * c.r;
    long double delta = b * b - 4 * a * C;

    if (delta < -EPS) return res;
    if (delta < 0) delta = 0;

    long double t1 = (-b + sqrtl(delta)) / (2 * a);
    long double t2 = (-b - sqrtl(delta)) / (2 * a);
    if (t1 >= -EPS && t1 <= 1 + EPS) res.push_back(p1 + (p2 - p1) * t1);
    if (std::abs(t1 - t2) > EPS && t2 >= -EPS && t2 <= 1 + EPS) res.push_back(p1 + (p2 - p1) * t2);
    return res;
}

std::vector<Point> intersect(const Curve& c1, const Curve& c2) {
    if (c1.type == ARC && c2.type == ARC) {
        return intersect_circle_circle({c1.center, c1.r}, {c2.center, c2.r});
    }
    if (c1.type == LINE && c2.type == LINE) {
        std::vector<Point> res;
        if (std::abs(cross(c1.vec, c2.vec)) < EPS) return res;
        long double t = cross(c2.p1 - c1.p1, c2.vec) / cross(c1.vec, c2.vec);
        res.push_back(c1.p1 + c1.vec * t);
        return res;
    }
    const Curve *line_c = &c1, *arc_c = &c2;
    if(c1.type == ARC) std::swap(line_c, arc_c);
    return intersect_line_circle(line_c->p1, line_c->p2, {arc_c->center, arc_c->r});
}

struct Event {
    long double x;
    int type; // +1 start, -1 end, 0 intersection
    int c1_idx, c2_idx;

    bool operator<(const Event& other) const {
        if (std::abs(x - other.x) > EPS) return x < other.x;
        return type > other.type;
    }
};

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n;
    std::cin >> n;
    std::vector<Point> points(n);
    for (int i = 0; i < n; ++i) std::cin >> points[i].x >> points[i].y;

    int m;
    std::cin >> m;
    std::vector<Segment> segments(m);
    for (int i = 0; i < m; ++i) {
        int u, v;
        std::cin >> u >> v; --u; --v;
        segments[i] = {points[u], points[v]};
    }
    long double r;
    std::cin >> r;
    long double p1, p2, p3, p4;
    std::cin >> p1 >> p2 >> p3 >> p4;

    rot_angle = 0.12345678912345L;
    for (int i = 0; i < n; ++i) points[i] = transform(points[i]);
    for (int i = 0; i < m; ++i) {
        segments[i].p1 = transform(segments[i].p1);
        segments[i].p2 = transform(segments[i].p2);
    }
    
    std::vector<Event> events;
    for (const auto& seg : segments) {
        Point p1 = seg.p1, p2 = seg.p2;
        if (p1.x > p2.x) std::swap(p1, p2);
        if (norm_sq(p1-p2) < EPS*EPS) { // it's a circle
             curves.push_back({ARC, p1, r, {}, {}, p1.x - r, p1.x + r, 1});
             events.push_back({p1.x - r, 1, (int)curves.size() - 1, -1});
             events.push_back({p1.x + r, -1, (int)curves.size() - 1, -1});
             curves.push_back({ARC, p1, r, {}, {}, p1.x - r, p1.x + r, -1});
             events.push_back({p1.x - r, 1, (int)curves.size() - 1, -1});
             events.push_back({p1.x + r, -1, (int)curves.size() - 1, -1});
             continue;
        }

        Point dir = normalize(p2 - p1);
        Point perp = {-dir.y, dir.x};
        Point r_perp = perp * r;

        curves.push_back({ARC, p1, r, {}, {}, p1.x - r, p1.x, 1});
        events.push_back({p1.x - r, 1, (int)curves.size() - 1, -1});
        events.push_back({p1.x, -1, (int)curves.size() - 1, -1});
        curves.push_back({ARC, p1, r, {}, {}, p1.x - r, p1.x, -1});
        events.push_back({p1.x - r, 1, (int)curves.size() - 1, -1});
        events.push_back({p1.x, -1, (int)curves.size() - 1, -1});
        
        curves.push_back({ARC, p2, r, {}, {}, p2.x, p2.x + r, 1});
        events.push_back({p2.x, 1, (int)curves.size() - 1, -1});
        events.push_back({p2.x + r, -1, (int)curves.size() - 1, -1});
        curves.push_back({ARC, p2, r, {}, {}, p2.x, p2.x + r, -1});
        events.push_back({p2.x, 1, (int)curves.size() - 1, -1});
        events.push_back({p2.x + r, -1, (int)curves.size() - 1, -1});
        
        Point l1p1 = p1 + r_perp, l1p2 = p2 + r_perp;
        Point l2p1 = p1 - r_perp, l2p2 = p2 - r_perp;
        curves.push_back({LINE, {}, {}, l1p1, l1p2, l1p2 - l1p1, p1.x, p2.x, (l1p1.y > l2p1.y) ? 1 : -1});
        events.push_back({p1.x, 1, (int)curves.size() - 1, -1});
        events.push_back({p2.x, -1, (int)curves.size() - 1, -1});
        curves.push_back({LINE, {}, {}, l2p1, l2p2, l2p2 - l2p1, p1.x, p2.x, (l2p1.y > l1p1.y) ? 1 : -1});
        events.push_back({p1.x, 1, (int)curves.size() - 1, -1});
        events.push_back({p2.x, -1, (int)curves.size() - 1, -1});
    }

    for (size_t i = 0; i < curves.size(); ++i) {
        for (size_t j = i + 1; j < curves.size(); ++j) {
            std::vector<Point> ips = intersect(curves[i], curves[j]);
            for (const auto& p : ips) {
                long double x_coord = p.x;
                if (x_coord > curves[i].x_min + EPS && x_coord < curves[i].x_max - EPS &&
                    x_coord > curves[j].x_min + EPS && x_coord < curves[j].x_max - EPS) {
                    events.push_back({x_coord, 0, (int)i, (int)j});
                }
            }
        }
    }
    
    std::sort(events.begin(), events.end());

    long double total_area = 0;
    long double last_x = events.empty() ? 0 : events[0].x;

    std::set<int, CurveCmp> active_curves;
    
    for (const auto& event : events) {
        current_x = event.x;
        if (current_x > last_x + EPS) {
            int count = 0;
            if (!active_curves.empty()) {
                auto it = active_curves.begin();
                int last_idx = *it;
                count -= curves[last_idx].sign;
                for (++it; it != active_curves.end(); ++it) {
                    int current_idx = *it;
                    if (count > 0) {
                       total_area += curves[current_idx].get_area(last_x, current_x) - curves[last_idx].get_area(last_x, current_x);
                    }
                    count -= curves[current_idx].sign;
                    last_idx = current_idx;
                }
            }
        }
        
        current_x = event.x; // Set precisely for updates
        last_x = current_x;
        int c1_idx = event.c1_idx;
        int c2_idx = event.c2_idx;

        if (event.type == 1) {
            active_curves.insert(c1_idx);
        } else if (event.type == -1) {
            active_curves.erase(c1_idx);
        } else {
            auto it1 = active_curves.find(c1_idx);
            auto it2 = active_curves.find(c2_idx);
            if (it1 != active_curves.end() && it2 != active_curves.end()) {
                active_curves.erase(it1);
                active_curves.erase(it2);
                active_curves.insert(c1_idx);
                active_curves.insert(c2_idx);
            }
        }
    }

    std::cout << std::fixed << std::setprecision(7) << total_area << std::endl;

    return 0;
}