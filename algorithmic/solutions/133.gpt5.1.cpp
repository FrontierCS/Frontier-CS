#include <bits/stdc++.h>
using namespace std;

struct Segment {
    double x1, y1, x2, y2;
    double dx, dy;
    double len2;
    double cx, cy;
    double halfLen;
};

static inline double dist2_point_segment(double px, double py, const Segment &s) {
    double vx = px - s.x1;
    double vy = py - s.y1;
    double t = (vx * s.dx + vy * s.dy) / s.len2;
    if (t < 0.0) t = 0.0;
    else if (t > 1.0) t = 1.0;
    double wx = s.x1 + t * s.dx - px;
    double wy = s.y1 + t * s.dy - py;
    return wx * wx + wy * wy;
}

struct Pt { double x, y; };

static inline double cross(const Pt &a, const Pt &b, const Pt &c) {
    return (b.x - a.x) * (c.y - a.y) - (b.y - a.y) * (c.x - a.x);
}

static inline bool onSegment(const Pt &a, const Pt &b, const Pt &c) {
    const double eps = 1e-9;
    return c.x >= min(a.x, b.x) - eps && c.x <= max(a.x, b.x) + eps &&
           c.y >= min(a.y, b.y) - eps && c.y <= max(a.y, b.y) + eps &&
           fabs(cross(a, b, c)) <= eps;
}

static inline bool segmentsIntersect(const Pt &a, const Pt &b, const Pt &c, const Pt &d) {
    const double eps = 1e-9;
    double c1 = cross(a, b, c);
    double c2 = cross(a, b, d);
    double c3 = cross(c, d, a);
    double c4 = cross(c, d, b);

    if (((c1 > eps && c2 < -eps) || (c1 < -eps && c2 > eps)) &&
        ((c3 > eps && c4 < -eps) || (c3 < -eps && c4 > eps))) return true;

    if (fabs(c1) <= eps && onSegment(a, b, c)) return true;
    if (fabs(c2) <= eps && onSegment(a, b, d)) return true;
    if (fabs(c3) <= eps && onSegment(c, d, a)) return true;
    if (fabs(c4) <= eps && onSegment(c, d, b)) return true;

    return false;
}

static inline double minDist2Segments(const Segment &s1, const Segment &s2) {
    double d2 = dist2_point_segment(s1.x1, s1.y1, s2);
    double tmp = dist2_point_segment(s1.x2, s1.y2, s2);
    if (tmp < d2) d2 = tmp;
    tmp = dist2_point_segment(s2.x1, s2.y1, s1);
    if (tmp < d2) d2 = tmp;
    tmp = dist2_point_segment(s2.x2, s2.y2, s1);
    if (tmp < d2) d2 = tmp;
    return d2;
}

static inline bool segmentsTubeOverlap(const Segment &s1, const Segment &s2, double /*r*/, double limit2) {
    Pt a{ s1.x1, s1.y1 };
    Pt b{ s1.x2, s1.y2 };
    Pt c{ s2.x1, s2.y1 };
    Pt d{ s2.x2, s2.y2 };
    if (segmentsIntersect(a, b, c, d)) return true;
    double d2 = minDist2Segments(s1, s2);
    return d2 < limit2 - 1e-9;
}

// KD-tree node
struct KDNode {
    int left, right;
    int axis;  // -1 = leaf
    int l, r;  // index range in g_segIdx for leaf
    double minx, maxx, miny, maxy;
    double maxHalfLen;
    double thresh2;
};

vector<Segment> g_segs;
vector<int> g_segIdx;
vector<KDNode> g_nodes;
double g_r, g_r2;
double g_tubeMinX, g_tubeMaxX, g_tubeMinY, g_tubeMaxY;

int buildKD(int l, int r) {
    KDNode node;
    node.left = node.right = -1;
    node.l = l;
    node.r = r;

    double minx = 1e100, maxx = -1e100;
    double miny = 1e100, maxy = -1e100;
    double hi_max = 0.0;

    for (int i = l; i < r; ++i) {
        const Segment &s = g_segs[g_segIdx[i]];
        if (s.cx < minx) minx = s.cx;
        if (s.cx > maxx) maxx = s.cx;
        if (s.cy < miny) miny = s.cy;
        if (s.cy > maxy) maxy = s.cy;
        if (s.halfLen > hi_max) hi_max = s.halfLen;
    }

    node.minx = minx;
    node.maxx = maxx;
    node.miny = miny;
    node.maxy = maxy;
    node.maxHalfLen = hi_max;
    double thr = hi_max + g_r;
    node.thresh2 = thr * thr;

    int id = (int)g_nodes.size();
    g_nodes.push_back(node);

    int cnt = r - l;
    const int leafCap = 16;
    if (cnt <= leafCap) {
        g_nodes[id].axis = -1;
        return id;
    }

    double rangeX = maxx - minx;
    double rangeY = maxy - miny;
    int axis = (rangeX >= rangeY) ? 0 : 1;
    g_nodes[id].axis = axis;

    int mid = (l + r) / 2;
    if (axis == 0) {
        nth_element(g_segIdx.begin() + l, g_segIdx.begin() + mid, g_segIdx.begin() + r,
                    [](int a, int b) { return g_segs[a].cx < g_segs[b].cx; });
    } else {
        nth_element(g_segIdx.begin() + l, g_segIdx.begin() + mid, g_segIdx.begin() + r,
                    [](int a, int b) { return g_segs[a].cy < g_segs[b].cy; });
    }

    int leftChild = buildKD(l, mid);
    int rightChild = buildKD(mid, r);
    g_nodes[id].left = leftChild;
    g_nodes[id].right = rightChild;
    return id;
}

static inline double dist2_point_box(double px, double py, const KDNode &node) {
    double dx = 0.0;
    if (px < node.minx) dx = node.minx - px;
    else if (px > node.maxx) dx = px - node.maxx;
    double dy = 0.0;
    if (py < node.miny) dy = node.miny - py;
    else if (py > node.maxy) dy = py - node.maxy;
    return dx * dx + dy * dy;
}

bool pointInside(double px, double py) {
    if (px < g_tubeMinX || px > g_tubeMaxX || py < g_tubeMinY || py > g_tubeMaxY)
        return false;
    if (g_segs.empty()) return false;

    const KDNode &root = g_nodes[0];
    if (dist2_point_box(px, py, root) > root.thresh2)
        return false;

    int stack[64];
    int sp = 0;
    stack[sp++] = 0;

    while (sp) {
        int idx = stack[--sp];
        const KDNode &node = g_nodes[idx];

        if (node.axis == -1) {
            for (int i = node.l; i < node.r; ++i) {
                const Segment &s = g_segs[g_segIdx[i]];
                double d2 = dist2_point_segment(px, py, s);
                if (d2 <= g_r2 + 1e-12) return true;
            }
        } else {
            int left = node.left;
            int right = node.right;
            bool okL = false, okR = false;
            double d2L = 0.0, d2R = 0.0;

            if (left != -1) {
                const KDNode &ln = g_nodes[left];
                d2L = dist2_point_box(px, py, ln);
                if (d2L <= ln.thresh2) okL = true;
            }
            if (right != -1) {
                const KDNode &rn = g_nodes[right];
                d2R = dist2_point_box(px, py, rn);
                if (d2R <= rn.thresh2) okR = true;
            }

            if (okL && okR) {
                if (d2L < d2R) {
                    stack[sp++] = right;
                    stack[sp++] = left;
                } else {
                    stack[sp++] = left;
                    stack[sp++] = right;
                }
            } else if (okL) {
                stack[sp++] = left;
            } else if (okR) {
                stack[sp++] = right;
            }
        }
    }
    return false;
}

// Quadtree integration
double g_area;
double q_rootMinX, q_rootMinY, q_rootMaxX, q_rootMaxY;
int q_maxDepth;

void dfsCell(double x0, double y0, double x1, double y1, int depth) {
    if (x1 <= g_tubeMinX || x0 >= g_tubeMaxX || y1 <= g_tubeMinY || y0 >= g_tubeMaxY)
        return;

    bool s0 = pointInside(x0, y0);
    bool s1 = pointInside(x0, y1);
    bool s2 = pointInside(x1, y0);
    bool s3 = pointInside(x1, y1);
    double xm = 0.5 * (x0 + x1);
    double ym = 0.5 * (y0 + y1);
    bool s4 = pointInside(xm, ym);

    int in0 = (int)s0 + (int)s1 + (int)s2 + (int)s3 + (int)s4;
    if (in0 == 5) {
        g_area += (x1 - x0) * (y1 - y0);
        return;
    }
    if (in0 == 0) return;

    if (depth >= q_maxDepth) {
        const int GRID = 4;
        int insideCnt = in0;
        double dx = (x1 - x0) / GRID;
        double dy = (y1 - y0) / GRID;
        for (int ix = 0; ix < GRID; ++ix) {
            double px = x0 + (ix + 0.5) * dx;
            for (int iy = 0; iy < GRID; ++iy) {
                double py = y0 + (iy + 0.5) * dy;
                if (pointInside(px, py)) insideCnt++;
            }
        }
        int totalSamples = 5 + GRID * GRID;
        g_area += (double)insideCnt / totalSamples * (x1 - x0) * (y1 - y0);
        return;
    }

    double mx = 0.5 * (x0 + x1);
    double my = 0.5 * (y0 + y1);
    dfsCell(x0, y0, mx, my, depth + 1);
    dfsCell(mx, y0, x1, my, depth + 1);
    dfsCell(x0, my, mx, y1, depth + 1);
    dfsCell(mx, my, x1, y1, depth + 1);
}

struct Cand {
    double len2;
    double x1, y1, x2, y2;
};

struct CandCmp {
    bool operator()(const Cand &a, const Cand &b) const {
        return a.len2 < b.len2;  // max-heap by len2
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;
    vector<double> px(n), py(n);
    for (int i = 0; i < n; ++i) cin >> px[i] >> py[i];

    int m;
    cin >> m;

    const double PI = acos(-1.0);

    if (m == 0) {
        double r;
        cin >> r;
        double p1, p2, p3, p4;
        cin >> p1 >> p2 >> p3 >> p4;
        cout.setf(ios::fixed);
        cout << setprecision(7) << 0.0 << "\n";
        return 0;
    }

    if (m == 1) {
        int a, b;
        cin >> a >> b;
        double r;
        cin >> r;
        double p1, p2, p3, p4;
        cin >> p1 >> p2 >> p3 >> p4;
        double dx = px[a - 1] - px[b - 1];
        double dy = py[a - 1] - py[b - 1];
        double L = sqrt(dx * dx + dy * dy);
        double area = 2.0 * r * L + PI * r * r;
        cout.setf(ios::fixed);
        cout << setprecision(7) << area << "\n";
        return 0;
    }

    const int K_MAX = 200000;
    int K_limit = min(m, K_MAX);
    priority_queue<Cand, vector<Cand>, CandCmp> pq;

    for (int i = 0; i < m; ++i) {
        int a, b;
        cin >> a >> b;
        double x1 = px[a - 1];
        double y1 = py[a - 1];
        double x2 = px[b - 1];
        double y2 = py[b - 1];
        double dx = x2 - x1;
        double dy = y2 - y1;
        double len2 = dx * dx + dy * dy;
        Cand c{len2, x1, y1, x2, y2};
        if (K_limit <= 0) continue;
        if ((int)pq.size() < K_limit) pq.push(c);
        else if (len2 < pq.top().len2) {
            pq.pop();
            pq.push(c);
        }
    }

    double r;
    cin >> r;
    double p1, p2, p3, p4;
    cin >> p1 >> p2 >> p3 >> p4;

    g_r = r;
    g_r2 = r * r;

    g_segs.clear();
    g_segs.reserve(pq.size());
    while (!pq.empty()) {
        Cand c = pq.top();
        pq.pop();
        Segment s;
        s.x1 = c.x1;
        s.y1 = c.y1;
        s.x2 = c.x2;
        s.y2 = c.y2;
        s.dx = s.x2 - s.x1;
        s.dy = s.y2 - s.y1;
        s.len2 = c.len2;
        s.cx = 0.5 * (s.x1 + s.x2);
        s.cy = 0.5 * (s.y1 + s.y2);
        s.halfLen = 0.5 * sqrt(c.len2);
        g_segs.push_back(s);
    }

    size_t usedCount = g_segs.size();
    bool truncated = (usedCount < (size_t)m);

    if (usedCount == 0) {
        cout.setf(ios::fixed);
        cout << setprecision(7) << 0.0 << "\n";
        return 0;
    }

    if (!truncated && usedCount <= 200) {
        vector<double> lens(usedCount);
        for (size_t i = 0; i < usedCount; ++i)
            lens[i] = sqrt(g_segs[i].len2);
        double limit2 = 4.0 * g_r2;
        bool overlap = false;
        for (size_t i = 0; i < usedCount && !overlap; ++i) {
            for (size_t j = i + 1; j < usedCount; ++j) {
                if (segmentsTubeOverlap(g_segs[i], g_segs[j], g_r, limit2)) {
                    overlap = true;
                    break;
                }
            }
        }
        if (!overlap) {
            double area = usedCount * (PI * g_r2);
            for (size_t i = 0; i < usedCount; ++i)
                area += 2.0 * g_r * lens[i];
            cout.setf(ios::fixed);
            cout << setprecision(7) << area << "\n";
            return 0;
        }
    }

    double minx = 1e100, maxx = -1e100;
    double miny = 1e100, maxy = -1e100;
    for (const Segment &s : g_segs) {
        double lx = min(s.x1, s.x2);
        double rx = max(s.x1, s.x2);
        double ly = min(s.y1, s.y2);
        double ry = max(s.y1, s.y2);
        if (lx < minx) minx = lx;
        if (rx > maxx) maxx = rx;
        if (ly < miny) miny = ly;
        if (ry > maxy) maxy = ry;
    }
    g_tubeMinX = minx - g_r;
    g_tubeMaxX = maxx + g_r;
    g_tubeMinY = miny - g_r;
    g_tubeMaxY = maxy + g_r;

    int N = (int)g_segs.size();
    g_segIdx.resize(N);
    for (int i = 0; i < N; ++i) g_segIdx[i] = i;
    g_nodes.clear();
    g_nodes.reserve(2 * N);
    buildKD(0, N);

    double Lx = g_tubeMaxX - g_tubeMinX;
    double Ly = g_tubeMaxY - g_tubeMinY;
    double L = max(Lx, Ly);
    q_rootMinX = g_tubeMinX;
    q_rootMinY = g_tubeMinY;
    if (Lx < L) {
        double pad = (L - Lx) * 0.5;
        q_rootMinX -= pad;
    }
    if (Ly < L) {
        double pad = (L - Ly) * 0.5;
        q_rootMinY -= pad;
    }
    q_rootMaxX = q_rootMinX + L;
    q_rootMaxY = q_rootMinY + L;

    double targetLeafSize = 0.25;
    int maxDepthLimit = 11;
    q_maxDepth = 0;
    while (q_maxDepth < maxDepthLimit && (L / (1 << q_maxDepth)) > targetLeafSize)
        ++q_maxDepth;

    g_area = 0.0;
    dfsCell(q_rootMinX, q_rootMinY, q_rootMaxX, q_rootMaxY, 0);

    cout.setf(ios::fixed);
    cout << setprecision(7) << g_area << "\n";
    return 0;
}