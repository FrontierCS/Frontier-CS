#include <bits/stdc++.h>
using namespace std;

struct FastScanner {
    static constexpr size_t BUFSIZE = 1 << 20;
    unsigned char buf[BUFSIZE];
    size_t idx = 0, size = 0;

    inline unsigned char getch() {
        if (idx >= size) {
            size = fread(buf, 1, BUFSIZE, stdin);
            idx = 0;
            if (!size) return 0;
        }
        return buf[idx++];
    }

    inline bool skipBlanks() {
        unsigned char c;
        do {
            c = getch();
            if (!c) return false;
        } while (c <= ' ');
        idx--;
        return true;
    }

    template <class T>
    bool readInt(T &out) {
        if (!skipBlanks()) return false;
        unsigned char c = getch();
        int sign = 1;
        if (c == '-') { sign = -1; c = getch(); }
        long long val = 0;
        while (c > ' ') {
            if (c < '0' || c > '9') break;
            val = val * 10 + (c - '0');
            c = getch();
        }
        out = (T)(val * sign);
        return true;
    }

    bool readDouble(double &out) {
        if (!skipBlanks()) return false;
        unsigned char c = getch();
        int sign = 1;
        if (c == '-') { sign = -1; c = getch(); }

        double val = 0.0;
        while (c >= '0' && c <= '9') {
            val = val * 10.0 + (c - '0');
            c = getch();
        }
        if (c == '.') {
            c = getch();
            double p = 0.1;
            while (c >= '0' && c <= '9') {
                val += (c - '0') * p;
                p *= 0.1;
                c = getch();
            }
        }
        int expSign = 1, expVal = 0;
        if (c == 'e' || c == 'E') {
            c = getch();
            if (c == '-') { expSign = -1; c = getch(); }
            else if (c == '+') { c = getch(); }
            while (c >= '0' && c <= '9') {
                expVal = expVal * 10 + (c - '0');
                c = getch();
            }
        }
        if (expVal) val *= pow(10.0, expSign * expVal);
        out = sign * val;
        return true;
    }
};

struct PointF {
    float x, y;
};

struct Segment {
    float ax, ay, bx, by;
    float minx, miny, maxx, maxy;
    float cx, cy;
};

struct Node {
    float minx, miny, maxx, maxy;
    int left, right;
    int start, count; // leaf range in order[]
};

static inline float dist2PointAABB(float px, float py, const Node &n) {
    float dx = 0.0f, dy = 0.0f;
    if (px < n.minx) dx = n.minx - px;
    else if (px > n.maxx) dx = px - n.maxx;
    if (py < n.miny) dy = n.miny - py;
    else if (py > n.maxy) dy = py - n.maxy;
    return dx * dx + dy * dy;
}

static inline float dist2PointSegment(float px, float py, const Segment &s) {
    float abx = s.bx - s.ax, aby = s.by - s.ay;
    float apx = px - s.ax, apy = py - s.ay;
    float denom = abx * abx + aby * aby;
    float t = 0.0f;
    if (denom > 1e-30f) {
        t = (apx * abx + apy * aby) / denom;
        if (t < 0.0f) t = 0.0f;
        else if (t > 1.0f) t = 1.0f;
    }
    float cx = s.ax + t * abx, cy = s.ay + t * aby;
    float dx = px - cx, dy = py - cy;
    return dx * dx + dy * dy;
}

struct BVH {
    vector<Segment> *segs = nullptr;
    vector<int> order;
    vector<Node> nodes;
    int root = -1;
    int leafSize = 8;

    int build(int l, int r) {
        int cnt = r - l;
        if (cnt <= leafSize) {
            Node nd;
            nd.left = nd.right = -1;
            nd.start = l; nd.count = cnt;
            float minx = numeric_limits<float>::infinity();
            float miny = numeric_limits<float>::infinity();
            float maxx = -numeric_limits<float>::infinity();
            float maxy = -numeric_limits<float>::infinity();
            for (int i = l; i < r; i++) {
                const Segment &s = (*segs)[order[i]];
                minx = min(minx, s.minx);
                miny = min(miny, s.miny);
                maxx = max(maxx, s.maxx);
                maxy = max(maxy, s.maxy);
            }
            nd.minx = minx; nd.miny = miny; nd.maxx = maxx; nd.maxy = maxy;
            nodes.push_back(nd);
            return (int)nodes.size() - 1;
        }

        float mincx = numeric_limits<float>::infinity();
        float mincy = numeric_limits<float>::infinity();
        float maxcx = -numeric_limits<float>::infinity();
        float maxcy = -numeric_limits<float>::infinity();
        for (int i = l; i < r; i++) {
            const Segment &s = (*segs)[order[i]];
            mincx = min(mincx, s.cx);
            mincy = min(mincy, s.cy);
            maxcx = max(maxcx, s.cx);
            maxcy = max(maxcy, s.cy);
        }
        int axis = (maxcx - mincx) >= (maxcy - mincy) ? 0 : 1;
        int mid = (l + r) >> 1;

        if (axis == 0) {
            nth_element(order.begin() + l, order.begin() + mid, order.begin() + r,
                        [&](int i, int j) { return (*segs)[i].cx < (*segs)[j].cx; });
        } else {
            nth_element(order.begin() + l, order.begin() + mid, order.begin() + r,
                        [&](int i, int j) { return (*segs)[i].cy < (*segs)[j].cy; });
        }

        int left = build(l, mid);
        int right = build(mid, r);

        Node nd;
        nd.left = left; nd.right = right;
        nd.start = 0; nd.count = 0;
        nd.minx = min(nodes[left].minx, nodes[right].minx);
        nd.miny = min(nodes[left].miny, nodes[right].miny);
        nd.maxx = max(nodes[left].maxx, nodes[right].maxx);
        nd.maxy = max(nodes[left].maxy, nodes[right].maxy);
        nodes.push_back(nd);
        return (int)nodes.size() - 1;
    }

    void init(vector<Segment> &segments, int leafSz = 8) {
        segs = &segments;
        leafSize = leafSz;
        int m = (int)segments.size();
        order.resize(m);
        iota(order.begin(), order.end(), 0);
        nodes.clear();
        nodes.reserve((size_t)(2.0 * m / max(1, leafSize) + 16));
        if (m > 0) root = build(0, m);
        else root = -1;
    }

    long long queryCnt = 0;

    inline float minDist2(float px, float py) {
        queryCnt++;
        if (root < 0) return numeric_limits<float>::infinity();
        float best = 1e30f;
        int st[128];
        int top = 0;
        st[top++] = root;
        while (top) {
            int ni = st[--top];
            const Node &nd = nodes[ni];
            float db = dist2PointAABB(px, py, nd);
            if (db >= best) continue;
            if (nd.left < 0) {
                int base = nd.start;
                for (int k = 0; k < nd.count; k++) {
                    const Segment &s = (*segs)[order[base + k]];
                    float d2 = dist2PointSegment(px, py, s);
                    if (d2 < best) best = d2;
                }
            } else {
                int l = nd.left, r = nd.right;
                float dl = dist2PointAABB(px, py, nodes[l]);
                float dr = dist2PointAABB(px, py, nodes[r]);
                if (dl < dr) {
                    if (dr < best) st[top++] = r;
                    if (dl < best) st[top++] = l;
                } else {
                    if (dl < best) st[top++] = l;
                    if (dr < best) st[top++] = r;
                }
            }
        }
        return best;
    }
};

struct Cell {
    double x, y, s;
};

int main() {
    FastScanner fs;

    int n;
    if (!fs.readInt(n)) return 0;
    vector<PointF> pts(n);
    for (int i = 0; i < n; i++) {
        double x, y;
        fs.readDouble(x);
        fs.readDouble(y);
        pts[i] = PointF{(float)x, (float)y};
    }

    int m;
    fs.readInt(m);

    double r_d;
    vector<pair<int,int>> edges;
    vector<Segment> segs;
    segs.reserve(max(0, m));

    float minX = numeric_limits<float>::infinity();
    float minY = numeric_limits<float>::infinity();
    float maxX = -numeric_limits<float>::infinity();
    float maxY = -numeric_limits<float>::infinity();

    edges.reserve(min(m, 10));

    // Read edges first; r comes later
    vector<pair<int,int>> tmpEdges;
    tmpEdges.reserve(m);
    for (int i = 0; i < m; i++) {
        int a, b;
        fs.readInt(a);
        fs.readInt(b);
        tmpEdges.emplace_back(a - 1, b - 1);
    }

    fs.readDouble(r_d);
    float r = (float)r_d;
    float r2 = r * r;

    // read scoring params (must be read)
    double p1, p2, p3, p4;
    fs.readDouble(p1); fs.readDouble(p2); fs.readDouble(p3); fs.readDouble(p4);

    if (m <= 0) {
        printf("%.10f\n", 0.0);
        return 0;
    }

    if (m == 1) {
        auto [a, b] = tmpEdges[0];
        double dx = (double)pts[a].x - (double)pts[b].x;
        double dy = (double)pts[a].y - (double)pts[b].y;
        double L = sqrt(dx * dx + dy * dy);
        double area = 2.0 * r_d * L + acos(-1.0) * r_d * r_d;
        printf("%.10f\n", area);
        return 0;
    }

    segs.resize(m);
    for (int i = 0; i < m; i++) {
        int a = tmpEdges[i].first;
        int b = tmpEdges[i].second;
        float ax = pts[a].x, ay = pts[a].y;
        float bx = pts[b].x, by = pts[b].y;
        Segment s;
        s.ax = ax; s.ay = ay; s.bx = bx; s.by = by;
        s.minx = min(ax, bx); s.miny = min(ay, by);
        s.maxx = max(ax, bx); s.maxy = max(ay, by);
        s.cx = 0.5f * (ax + bx);
        s.cy = 0.5f * (ay + by);
        segs[i] = s;
        minX = min(minX, s.minx);
        minY = min(minY, s.miny);
        maxX = max(maxX, s.maxx);
        maxY = max(maxY, s.maxy);
    }

    minX -= r; minY -= r; maxX += r; maxY += r;

    BVH bvh;
    bvh.init(segs, 8);

    double width = (double)maxX - (double)minX;
    double height = (double)maxY - (double)minY;
    double size = max(width, height);
    double x0 = ((double)minX + (double)maxX - size) * 0.5;
    double y0 = ((double)minY + (double)maxY - size) * 0.5;

    // Adaptive parameters
    double minSize = max(0.0015, min(0.02, r_d / 150.0));
    const long long QUERY_BUDGET = 60000000LL; // soft cap
    const double SQRT2_HALF = 0.7071067811865475244;

    auto inside = [&](float px, float py) -> bool {
        return bvh.minDist2(px, py) <= r2;
    };

    auto estimateFraction = [&](double x, double y, double s) -> double {
        if (bvh.queryCnt > QUERY_BUDGET) {
            float cx = (float)(x + 0.5 * s);
            float cy = (float)(y + 0.5 * s);
            return inside(cx, cy) ? 1.0 : 0.0;
        }
        // 3x3 stratified sampling
        int cntIn = 0;
        constexpr int K = 3;
        for (int i = 0; i < K; i++) {
            double fx = (i + 0.5) / K;
            float px = (float)(x + fx * s);
            for (int j = 0; j < K; j++) {
                double fy = (j + 0.5) / K;
                float py = (float)(y + fy * s);
                if (inside(px, py)) cntIn++;
            }
        }
        return (double)cntIn / (K * K);
    };

    vector<Cell> st;
    st.reserve(1 << 20);
    st.push_back({x0, y0, size});

    long double area = 0.0L;

    while (!st.empty()) {
        Cell c = st.back();
        st.pop_back();

        double s = c.s;
        double cx = c.x + 0.5 * s;
        double cy = c.y + 0.5 * s;
        double rad = s * SQRT2_HALF;

        float d2 = bvh.minDist2((float)cx, (float)cy);

        double rin = r_d - rad;
        if (rin >= 0.0) {
            double rin2 = rin * rin;
            if ((double)d2 <= rin2) {
                area += (long double)(s * s);
                continue;
            }
        }
        double rout = r_d + rad;
        double rout2 = rout * rout;
        if ((double)d2 > rout2) continue;

        if (s <= minSize || bvh.queryCnt > QUERY_BUDGET) {
            double frac = estimateFraction(c.x, c.y, s);
            area += (long double)(s * s * frac);
            continue;
        }

        double h = 0.5 * s;
        st.push_back({c.x, c.y, h});
        st.push_back({c.x + h, c.y, h});
        st.push_back({c.x, c.y + h, h});
        st.push_back({c.x + h, c.y + h, h});
    }

    printf("%.10f\n", (double)area);
    return 0;
}