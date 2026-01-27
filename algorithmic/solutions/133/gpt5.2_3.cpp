#include <bits/stdc++.h>
using namespace std;

struct FastScanner {
    static constexpr size_t BUFSIZE = 1 << 20;
    size_t idx = 0, size = 0;
    char buf[BUFSIZE];

    inline char getch() {
        if (idx >= size) {
            size = fread(buf, 1, BUFSIZE, stdin);
            idx = 0;
            if (size == 0) return 0;
        }
        return buf[idx++];
    }

    inline void skipSpaces() {
        char c;
        while ((c = getch()) && isspace((unsigned char)c)) {}
        if (c) idx--;
    }

    template <class T>
    bool readInt(T &out) {
        skipSpaces();
        char c = getch();
        if (!c) return false;
        T sign = 1;
        if (c == '-') { sign = -1; c = getch(); }
        T x = 0;
        while (c && isdigit((unsigned char)c)) {
            x = x * 10 + (c - '0');
            c = getch();
        }
        if (c) idx--;
        out = x * sign;
        return true;
    }

    bool readDouble(double &out) {
        skipSpaces();
        char c = getch();
        if (!c) return false;

        int sign = 1;
        if (c == '-') { sign = -1; c = getch(); }
        else if (c == '+') { c = getch(); }

        double x = 0.0;
        while (c && isdigit((unsigned char)c)) {
            x = x * 10.0 + (c - '0');
            c = getch();
        }

        if (c == '.') {
            double p = 1.0;
            c = getch();
            while (c && isdigit((unsigned char)c)) {
                p *= 0.1;
                x += (c - '0') * p;
                c = getch();
            }
        }

        if (c == 'e' || c == 'E') {
            c = getch();
            int esign = 1;
            if (c == '-') { esign = -1; c = getch(); }
            else if (c == '+') { c = getch(); }
            int e = 0;
            while (c && isdigit((unsigned char)c)) {
                e = e * 10 + (c - '0');
                c = getch();
            }
            x *= pow(10.0, esign * e);
        }

        if (c) idx--;
        out = x * sign;
        return true;
    }
};

struct Seg {
    float ax, ay, bx, by;
    float dx, dy;
    float invLen2; // 0 if degenerate
    float minx, maxx, miny, maxy;
    float cx, cy;
};

struct Node {
    float minx, maxx, miny, maxy;
    int left = -1, right = -1;
    int start = 0, count = 0; // leaf if count>0
};

static inline double clamp01(double t) {
    if (t < 0.0) return 0.0;
    if (t > 1.0) return 1.0;
    return t;
}

static inline double dist2PointAABB(double px, double py, float minx, float maxx, float miny, float maxy) {
    double dx = 0.0, dy = 0.0;
    if (px < (double)minx) dx = (double)minx - px;
    else if (px > (double)maxx) dx = px - (double)maxx;
    if (py < (double)miny) dy = (double)miny - py;
    else if (py > (double)maxy) dy = py - (double)maxy;
    return dx * dx + dy * dy;
}

static inline double dist2AABBAABB(double ax0, double ax1, double ay0, double ay1,
                                  float bx0, float bx1, float by0, float by1) {
    double dx = 0.0, dy = 0.0;
    if (ax1 < (double)bx0) dx = (double)bx0 - ax1;
    else if (ax0 > (double)bx1) dx = ax0 - (double)bx1;
    if (ay1 < (double)by0) dy = (double)by0 - ay1;
    else if (ay0 > (double)by1) dy = ay0 - (double)by1;
    return dx * dx + dy * dy;
}

static inline double dist2PointSeg(double px, double py, const Seg &s) {
    double ax = (double)s.ax, ay = (double)s.ay;
    double vx = (double)s.dx, vy = (double)s.dy;
    double inv = (double)s.invLen2;
    if (inv == 0.0) {
        double dx = px - ax, dy = py - ay;
        return dx * dx + dy * dy;
    }
    double t = ((px - ax) * vx + (py - ay) * vy) * inv;
    t = clamp01(t);
    double cx = ax + t * vx;
    double cy = ay + t * vy;
    double dx = px - cx, dy = py - cy;
    return dx * dx + dy * dy;
}

static inline bool segmentIntersectsAABB(double ax, double ay, double bx, double by,
                                        double x0, double x1, double y0, double y1) {
    double dx = bx - ax, dy = by - ay;
    double t0 = 0.0, t1 = 1.0;

    auto clip = [&](double p, double q) -> bool {
        if (p == 0.0) return q >= 0.0;
        double r = q / p;
        if (p < 0.0) {
            if (r > t1) return false;
            if (r > t0) t0 = r;
        } else {
            if (r < t0) return false;
            if (r < t1) t1 = r;
        }
        return true;
    };

    if (!clip(-dx, ax - x0)) return false;
    if (!clip( dx, x1 - ax)) return false;
    if (!clip(-dy, ay - y0)) return false;
    if (!clip( dy, y1 - ay)) return false;
    return t0 <= t1;
}

static inline double dist2PointRect(double px, double py, double x0, double x1, double y0, double y1) {
    double dx = 0.0, dy = 0.0;
    if (px < x0) dx = x0 - px;
    else if (px > x1) dx = px - x1;
    if (py < y0) dy = y0 - py;
    else if (py > y1) dy = py - y1;
    return dx * dx + dy * dy;
}

static inline double dist2SegRect(const Seg &s, double x0, double x1, double y0, double y1) {
    double ax = (double)s.ax, ay = (double)s.ay;
    double bx = (double)s.bx, by = (double)s.by;

    if (segmentIntersectsAABB(ax, ay, bx, by, x0, x1, y0, y1)) return 0.0;

    double best = dist2PointRect(ax, ay, x0, x1, y0, y1);
    best = min(best, dist2PointRect(bx, by, x0, x1, y0, y1));

    // check rectangle corners to segment (enough for convex polygon edge case)
    best = min(best, dist2PointSeg(x0, y0, s));
    best = min(best, dist2PointSeg(x0, y1, s));
    best = min(best, dist2PointSeg(x1, y0, s));
    best = min(best, dist2PointSeg(x1, y1, s));
    return best;
}

struct BVH {
    vector<Seg> segs;
    vector<Node> nodes;
    int root = -1;
    int leafSize = 8;

    int build(int l, int r) {
        int idx = (int)nodes.size();
        nodes.push_back(Node{});

        float minx = numeric_limits<float>::infinity();
        float miny = numeric_limits<float>::infinity();
        float maxx = -numeric_limits<float>::infinity();
        float maxy = -numeric_limits<float>::infinity();
        float cminx = numeric_limits<float>::infinity();
        float cminy = numeric_limits<float>::infinity();
        float cmaxx = -numeric_limits<float>::infinity();
        float cmaxy = -numeric_limits<float>::infinity();

        for (int i = l; i < r; i++) {
            const Seg &s = segs[i];
            minx = min(minx, s.minx);
            miny = min(miny, s.miny);
            maxx = max(maxx, s.maxx);
            maxy = max(maxy, s.maxy);
            cminx = min(cminx, s.cx);
            cminy = min(cminy, s.cy);
            cmaxx = max(cmaxx, s.cx);
            cmaxy = max(cmaxy, s.cy);
        }

        nodes[idx].minx = minx; nodes[idx].maxx = maxx;
        nodes[idx].miny = miny; nodes[idx].maxy = maxy;

        int cnt = r - l;
        if (cnt <= leafSize) {
            nodes[idx].start = l;
            nodes[idx].count = cnt;
            nodes[idx].left = nodes[idx].right = -1;
            return idx;
        }

        int axis = ((cmaxx - cminx) > (cmaxy - cminy)) ? 0 : 1;
        int mid = (l + r) >> 1;
        if (axis == 0) {
            nth_element(segs.begin() + l, segs.begin() + mid, segs.begin() + r,
                        [](const Seg &a, const Seg &b) { return a.cx < b.cx; });
        } else {
            nth_element(segs.begin() + l, segs.begin() + mid, segs.begin() + r,
                        [](const Seg &a, const Seg &b) { return a.cy < b.cy; });
        }

        nodes[idx].left = build(l, mid);
        nodes[idx].right = build(mid, r);
        nodes[idx].count = 0;
        nodes[idx].start = 0;
        return idx;
    }

    void build() {
        nodes.clear();
        nodes.reserve(segs.size() / leafSize * 2 + 8);
        if (segs.empty()) { root = -1; return; }
        root = build(0, (int)segs.size());
    }

    bool existsWithin(double px, double py, double rad) const {
        if (root < 0) return false;
        double rad2 = rad * rad;

        thread_local vector<int> st;
        st.clear();
        st.push_back(root);

        while (!st.empty()) {
            int ni = st.back();
            st.pop_back();
            const Node &nd = nodes[ni];
            if (dist2PointAABB(px, py, nd.minx, nd.maxx, nd.miny, nd.maxy) > rad2) continue;

            if (nd.count > 0) {
                int e = nd.start + nd.count;
                for (int i = nd.start; i < e; i++) {
                    if (dist2PointSeg(px, py, segs[i]) <= rad2) return true;
                }
            } else {
                st.push_back(nd.left);
                st.push_back(nd.right);
            }
        }
        return false;
    }

    bool existsNearRect(double x0, double x1, double y0, double y1, double rad) const {
        if (root < 0) return false;
        double rad2 = rad * rad;

        thread_local vector<int> st;
        st.clear();
        st.push_back(root);

        while (!st.empty()) {
            int ni = st.back();
            st.pop_back();
            const Node &nd = nodes[ni];
            if (dist2AABBAABB(x0, x1, y0, y1, nd.minx, nd.maxx, nd.miny, nd.maxy) > rad2) continue;

            if (nd.count > 0) {
                int e = nd.start + nd.count;
                for (int i = nd.start; i < e; i++) {
                    if (dist2SegRect(segs[i], x0, x1, y0, y1) <= rad2) return true;
                }
            } else {
                st.push_back(nd.left);
                st.push_back(nd.right);
            }
        }
        return false;
    }
};

struct Cell {
    double x, y, s;
};

int main() {
    FastScanner fs;

    int n;
    if (!fs.readInt(n)) return 0;

    vector<double> px(n + 1), py(n + 1);
    for (int i = 1; i <= n; i++) {
        double x, y;
        fs.readDouble(x);
        fs.readDouble(y);
        px[i] = x; py[i] = y;
    }

    int m;
    fs.readInt(m);

    BVH bvh;
    bvh.segs.reserve((size_t)m);

    double usedMinX = 1e300, usedMaxX = -1e300, usedMinY = 1e300, usedMaxY = -1e300;

    for (int i = 0; i < m; i++) {
        int a, b;
        fs.readInt(a);
        fs.readInt(b);
        double ax = px[a], ay = py[a];
        double bx = px[b], by = py[b];

        Seg s;
        s.ax = (float)ax; s.ay = (float)ay;
        s.bx = (float)bx; s.by = (float)by;
        double dx = bx - ax, dy = by - ay;
        s.dx = (float)dx; s.dy = (float)dy;
        double len2 = dx * dx + dy * dy;
        s.invLen2 = (len2 > 0.0) ? (float)(1.0 / len2) : 0.0f;

        s.minx = min(s.ax, s.bx); s.maxx = max(s.ax, s.bx);
        s.miny = min(s.ay, s.by); s.maxy = max(s.ay, s.by);
        s.cx = (s.ax + s.bx) * 0.5f;
        s.cy = (s.ay + s.by) * 0.5f;

        usedMinX = min(usedMinX, min(ax, bx));
        usedMaxX = max(usedMaxX, max(ax, bx));
        usedMinY = min(usedMinY, min(ay, by));
        usedMaxY = max(usedMaxY, max(ay, by));

        bvh.segs.push_back(s);
    }

    double r;
    fs.readDouble(r);

    // read p1..p4 (ignored for computing)
    double p1=0, p2=0, p3=0, p4=0;
    fs.readDouble(p1);
    fs.readDouble(p2);
    fs.readDouble(p3);
    fs.readDouble(p4);

    if (m == 0 || bvh.segs.empty()) {
        printf("%.10f\n", 0.0);
        return 0;
    }

    bvh.leafSize = 8;
    bvh.build();

    double minx = usedMinX - r, maxx = usedMaxX + r;
    double miny = usedMinY - r, maxy = usedMaxY + r;

    double cx0 = (minx + maxx) * 0.5;
    double cy0 = (miny + maxy) * 0.5;
    double side = max(maxx - minx, maxy - miny);
    // expand slightly to avoid borderline misses
    side *= 1.0000005;

    double x0 = cx0 - side * 0.5;
    double y0 = cy0 - side * 0.5;

    const double sqrt2 = sqrt(2.0);

    double minSize = max(5e-4, min(0.02, r / 40.0));
    // also cap minimum so we don't explode too much if r is extremely tiny
    minSize = max(minSize, 2e-4);

    vector<Cell> st;
    st.reserve(1 << 20);
    st.push_back(Cell{x0, y0, side});

    double area = 0.0;

    auto isInsidePoint = [&](double x, double y) -> bool {
        return bvh.existsWithin(x, y, r);
    };

    while (!st.empty()) {
        Cell c = st.back();
        st.pop_back();

        double x1 = c.x + c.s;
        double y1 = c.y + c.s;

        // outside test (more informative for large cells than center-based)
        if (!bvh.existsNearRect(c.x, x1, c.y, y1, r)) continue;

        double ccx = c.x + c.s * 0.5;
        double ccy = c.y + c.s * 0.5;
        double d = c.s * sqrt2 * 0.5;

        // safe inside test (Lipschitz)
        double rin = r - d;
        if (rin >= 0.0 && bvh.existsWithin(ccx, ccy, rin)) {
            area += c.s * c.s;
            continue;
        }

        // heuristic: if center+corners are all inside, accept
        if (c.s > minSize * 4.0) {
            if (isInsidePoint(ccx, ccy) &&
                isInsidePoint(c.x, c.y) &&
                isInsidePoint(c.x, y1) &&
                isInsidePoint(x1, c.y) &&
                isInsidePoint(x1, y1)) {
                area += c.s * c.s;
                continue;
            }
        }

        if (c.s <= minSize) {
            // 4 subsamples (centers of quadrants)
            double q = c.s * 0.25;
            int inside = 0;
            inside += (int)isInsidePoint(c.x + q,     c.y + q);
            inside += (int)isInsidePoint(c.x + q,     c.y + 3.0 * q);
            inside += (int)isInsidePoint(c.x + 3.0*q, c.y + q);
            inside += (int)isInsidePoint(c.x + 3.0*q, c.y + 3.0 * q);
            area += (double)inside * 0.25 * c.s * c.s;
            continue;
        }

        double hs = c.s * 0.5;
        st.push_back(Cell{c.x,      c.y,      hs});
        st.push_back(Cell{c.x + hs, c.y,      hs});
        st.push_back(Cell{c.x,      c.y + hs, hs});
        st.push_back(Cell{c.x + hs, c.y + hs, hs});
    }

    printf("%.10f\n", area);
    return 0;
}