#include <bits/stdc++.h>
using namespace std;

struct FastScanner {
    static inline int gc() { return getchar_unlocked(); }

    template <class T>
    bool readInt(T &out) {
        int c;
        do {
            c = gc();
            if (c == EOF) return false;
        } while (c <= ' ');

        T sign = 1;
        if (c == '-') { sign = -1; c = gc(); }
        T x = 0;
        while (c > ' ') {
            if (c < '0' || c > '9') break;
            x = x * 10 + (c - '0');
            c = gc();
        }
        out = x * sign;
        return true;
    }

    bool readDouble(double &out) {
        int c;
        do {
            c = gc();
            if (c == EOF) return false;
        } while (c <= ' ');

        int sign = 1;
        if (c == '-') { sign = -1; c = gc(); }

        double x = 0.0;
        while (c >= '0' && c <= '9') {
            x = x * 10.0 + (c - '0');
            c = gc();
        }

        if (c == '.') {
            c = gc();
            double base = 0.1;
            while (c >= '0' && c <= '9') {
                x += (c - '0') * base;
                base *= 0.1;
                c = gc();
            }
        }

        if (c == 'e' || c == 'E') {
            c = gc();
            int esign = 1;
            if (c == '-') { esign = -1; c = gc(); }
            else if (c == '+') { c = gc(); }
            int e = 0;
            while (c >= '0' && c <= '9') {
                e = e * 10 + (c - '0');
                c = gc();
            }
            x *= pow(10.0, esign * e);
        }

        out = x * sign;
        return true;
    }
};

static inline uint32_t morton2D_10bit(uint32_t x, uint32_t y) {
    uint32_t c = 0;
    for (uint32_t b = 0; b < 10; b++) {
        c |= ((x >> b) & 1u) << (2u * b);
        c |= ((y >> b) & 1u) << (2u * b + 1u);
    }
    return c;
}

struct Node {
    float minx, miny, maxx, maxy;
    int left, right;
};

struct BVH {
    int N = 0;
    int base = 0;
    vector<Node> nodes;
    vector<float> ax, ay, bx, by, len2;
    mutable vector<int> st;

    static inline double distPointAABB2(double px, double py, const Node &nd) {
        double dx = 0.0;
        if (px < nd.minx) dx = (double)nd.minx - px;
        else if (px > nd.maxx) dx = px - (double)nd.maxx;
        double dy = 0.0;
        if (py < nd.miny) dy = (double)nd.miny - py;
        else if (py > nd.maxy) dy = py - (double)nd.maxy;
        return dx * dx + dy * dy;
    }

    inline double distPointSeg2(int si, double px, double py) const {
        double x1 = ax[si], y1 = ay[si];
        double x2 = bx[si], y2 = by[si];
        double vx = x2 - x1, vy = y2 - y1;
        double wx = px - x1, wy = py - y1;
        double l2 = (double)len2[si];
        if (l2 <= 0.0) return wx * wx + wy * wy;
        double c1 = vx * wx + vy * wy;
        if (c1 <= 0.0) return wx * wx + wy * wy;
        if (c1 >= l2) {
            double dx = px - x2, dy = py - y2;
            return dx * dx + dy * dy;
        }
        double t = c1 / l2;
        double projx = x1 + t * vx, projy = y1 + t * vy;
        double dx = px - projx, dy = py - projy;
        return dx * dx + dy * dy;
    }

    bool anyWithin(double px, double py, double r2) const {
        if (N <= 0) return false;
        st.clear();
        st.push_back(0);
        while (!st.empty()) {
            int idx = st.back();
            st.pop_back();
            const Node &nd = nodes[idx];
            if (distPointAABB2(px, py, nd) > r2) continue;

            if (idx >= base) {
                int si = idx - base;
                if (distPointSeg2(si, px, py) <= r2) return true;
            } else {
                int l = nd.left, r = nd.right;
                const Node &nl = nodes[l];
                const Node &nr = nodes[r];
                double dl = distPointAABB2(px, py, nl);
                double dr = distPointAABB2(px, py, nr);
                if (dl < dr) {
                    st.push_back(r);
                    st.push_back(l);
                } else {
                    st.push_back(l);
                    st.push_back(r);
                }
            }
        }
        return false;
    }
};

static inline void radixSortByCode(vector<uint32_t> &code, vector<uint32_t> &order) {
    size_t n = order.size();
    vector<uint32_t> tmp(order.size());
    for (int pass = 0; pass < 4; pass++) {
        uint32_t shift = pass * 8u;
        uint32_t cnt[256] = {};
        for (size_t i = 0; i < n; i++) cnt[(code[order[i]] >> shift) & 255u]++;
        uint32_t sum = 0;
        for (int i = 0; i < 256; i++) {
            uint32_t c = cnt[i];
            cnt[i] = sum;
            sum += c;
        }
        for (size_t i = 0; i < n; i++) {
            uint32_t id = order[i];
            tmp[cnt[(code[id] >> shift) & 255u]++] = id;
        }
        order.swap(tmp);
    }
}

struct Cell {
    double cx, cy, h;
    int depth;
};

int main() {
    FastScanner fs;

    int n;
    if (!fs.readInt(n)) return 0;
    vector<float> X(n), Y(n);
    double minX = 1e300, minY = 1e300, maxX = -1e300, maxY = -1e300;
    for (int i = 0; i < n; i++) {
        double xd, yd;
        fs.readDouble(xd);
        fs.readDouble(yd);
        X[i] = (float)xd;
        Y[i] = (float)yd;
        minX = min(minX, xd);
        minY = min(minY, yd);
        maxX = max(maxX, xd);
        maxY = max(maxY, yd);
    }

    int m;
    fs.readInt(m);

    if (m <= 0 || n <= 0) {
        double r, p1, p2, p3, p4;
        fs.readDouble(r);
        fs.readDouble(p1); fs.readDouble(p2); fs.readDouble(p3); fs.readDouble(p4);
        printf("%.10f\n", 0.0);
        return 0;
    }

    vector<uint16_t> ea(m), eb(m);
    vector<uint32_t> code(m);

    double denomX = maxX - minX;
    double denomY = maxY - minY;
    if (denomX == 0.0) denomX = 1.0;
    if (denomY == 0.0) denomY = 1.0;

    for (int i = 0; i < m; i++) {
        int a, b;
        fs.readInt(a); fs.readInt(b);
        --a; --b;
        if (a < 0) a = 0;
        if (b < 0) b = 0;
        if (a >= n) a = n - 1;
        if (b >= n) b = n - 1;
        ea[i] = (uint16_t)a;
        eb[i] = (uint16_t)b;

        double cx = 0.5 * ((double)X[a] + (double)X[b]);
        double cy = 0.5 * ((double)Y[a] + (double)Y[b]);
        double tx = (cx - minX) / denomX;
        double ty = (cy - minY) / denomY;
        if (tx < 0) tx = 0; if (tx > 1) tx = 1;
        if (ty < 0) ty = 0; if (ty > 1) ty = 1;
        uint32_t xi = (uint32_t)min(1023.0, max(0.0, tx * 1023.999));
        uint32_t yi = (uint32_t)min(1023.0, max(0.0, ty * 1023.999));
        code[i] = morton2D_10bit(xi, yi);
    }

    double r;
    fs.readDouble(r);
    double p1, p2, p3, p4;
    fs.readDouble(p1); fs.readDouble(p2); fs.readDouble(p3); fs.readDouble(p4);

    vector<uint32_t> order(m);
    for (uint32_t i = 0; i < (uint32_t)m; i++) order[i] = i;
    radixSortByCode(code, order);

    BVH bvh;
    bvh.N = m;
    bvh.base = bvh.N - 1;
    int nodesCount = 2 * bvh.N - 1;
    bvh.nodes.assign(nodesCount, Node{});
    bvh.ax.resize(m);
    bvh.ay.resize(m);
    bvh.bx.resize(m);
    bvh.by.resize(m);
    bvh.len2.resize(m);

    vector<uint32_t> codesSorted(m);
    for (int i = 0; i < m; i++) {
        uint32_t id = order[i];
        int a = ea[id], b = eb[id];
        float ax = X[a], ay = Y[a], bx = X[b], by = Y[b];
        bvh.ax[i] = ax; bvh.ay[i] = ay; bvh.bx[i] = bx; bvh.by[i] = by;
        float dx = bx - ax, dy = by - ay;
        bvh.len2[i] = dx * dx + dy * dy;
        codesSorted[i] = code[id];

        int leaf = bvh.base + i;
        bvh.nodes[leaf].minx = min(ax, bx);
        bvh.nodes[leaf].miny = min(ay, by);
        bvh.nodes[leaf].maxx = max(ax, bx);
        bvh.nodes[leaf].maxy = max(ay, by);
        bvh.nodes[leaf].left = -1;
        bvh.nodes[leaf].right = -1;
    }

    // Free input arrays early
    vector<uint16_t>().swap(ea);
    vector<uint16_t>().swap(eb);
    vector<uint32_t>().swap(code);
    vector<uint32_t>().swap(order);

    // Build LBVH (Karras)
    if (bvh.N >= 2) {
        vector<int> parent(nodesCount, -1);
        auto delta = [&](int i, int j) -> int {
            if (j < 0 || j >= bvh.N) return -1;
            uint32_t a = codesSorted[i];
            uint32_t b = codesSorted[j];
            if (a == b) {
                uint32_t x = (uint32_t)(i ^ j);
                if (x == 0) return 64;
                return 32 + __builtin_clz(x);
            }
            return __builtin_clz(a ^ b);
        };

        for (int i = 0; i < bvh.N - 1; i++) {
            int deltaNext = delta(i, i + 1);
            int deltaPrev = delta(i, i - 1);
            int d = (deltaNext - deltaPrev) >= 0 ? 1 : -1;

            int deltaMin = delta(i, i - d);

            int lmax = 2;
            while (delta(i, i + lmax * d) > deltaMin) lmax <<= 1;

            int l = 0;
            for (int t = lmax >> 1; t >= 1; t >>= 1) {
                if (delta(i, i + (l + t) * d) > deltaMin) l += t;
            }

            int j = i + l * d;
            int first = min(i, j);
            int last = max(i, j);

            int commonPrefix = delta(first, last);
            int split = first;
            int step = last - first;

            while (step > 1) {
                int half = (step + 1) >> 1;
                int newSplit = split + half;
                if (newSplit < last && delta(first, newSplit) > commonPrefix) split = newSplit;
                step = half;
            }

            int leftChild = (split == first) ? (bvh.base + split) : split;
            int rightChild = (split + 1 == last) ? (bvh.base + split + 1) : (split + 1);

            bvh.nodes[i].left = leftChild;
            bvh.nodes[i].right = rightChild;

            parent[leftChild] = i;
            parent[rightChild] = i;
        }

        // Bottom-up AABB construction
        const float INF = 1e30f;
        vector<int> pending(bvh.N - 1, 2);
        for (int i = 0; i < bvh.N - 1; i++) {
            bvh.nodes[i].minx = INF;
            bvh.nodes[i].miny = INF;
            bvh.nodes[i].maxx = -INF;
            bvh.nodes[i].maxy = -INF;
        }
        for (int i = 0; i < bvh.N; i++) {
            int child = bvh.base + i;
            int p = parent[child];
            while (p != -1) {
                Node &pn = bvh.nodes[p];
                const Node &cn = bvh.nodes[child];
                pn.minx = min(pn.minx, cn.minx);
                pn.miny = min(pn.miny, cn.miny);
                pn.maxx = max(pn.maxx, cn.maxx);
                pn.maxy = max(pn.maxy, cn.maxy);

                if (--pending[p] == 0) {
                    child = p;
                    p = parent[child];
                } else {
                    break;
                }
            }
        }
    } else {
        // N == 1 : root is leaf already has AABB
        bvh.nodes[0].left = -1;
        bvh.nodes[0].right = -1;
    }

    vector<uint32_t>().swap(codesSorted);

    bvh.st.reserve(2048);

    // Compute bounding square
    double bbMinX = minX - r, bbMaxX = maxX + r;
    double bbMinY = minY - r, bbMaxY = maxY + r;
    double w = bbMaxX - bbMinX;
    double h = bbMaxY - bbMinY;
    double sz = max(w, h);
    double cx0 = 0.5 * (bbMinX + bbMaxX);
    double cy0 = 0.5 * (bbMinY + bbMaxY);

    double rootH = 0.5 * sz;
    const double SQRT2 = 1.4142135623730950488;

    // Adaptive quadtree
    double r2 = r * r;
    double minH = max(1e-3, r * 0.005); // heuristic
    int maxDepth = 24;

    vector<Cell> q;
    q.reserve(1 << 20);
    q.push_back({cx0, cy0, rootH, 0});

    double area = 0.0;

    auto estimateCell = [&](double ccx, double ccy, double hh) -> double {
        double size = 2.0 * hh;
        double xmin = ccx - hh;
        double ymin = ccy - hh;

        double denom = max(r, 1e-6);
        int target = (int)ceil(2.5 * size / denom);
        target = max(64, min(4096, target));
        int k = (int)ceil(sqrt((double)target));
        k = max(8, min(64, k));
        int tot = k * k;

        int inside = 0;
        double invk = 1.0 / k;
        for (int i = 0; i < k; i++) {
            double x = xmin + (i + 0.5) * size * invk;
            for (int j = 0; j < k; j++) {
                double y = ymin + (j + 0.5) * size * invk;
                if (bvh.anyWithin(x, y, r2)) inside++;
            }
        }
        return (double)inside / (double)tot;
    };

    while (!q.empty()) {
        Cell c = q.back();
        q.pop_back();

        double halfdiag = c.h * SQRT2;

        // definite inside?
        double rin = r - halfdiag;
        if (rin >= 0.0) {
            double rin2 = rin * rin;
            if (bvh.anyWithin(c.cx, c.cy, rin2)) {
                double s = 2.0 * c.h;
                area += s * s;
                continue;
            }
        }

        // definite outside?
        double rout = r + halfdiag;
        double rout2 = rout * rout;
        if (!bvh.anyWithin(c.cx, c.cy, rout2)) {
            continue;
        }

        if (c.h <= minH || c.depth >= maxDepth) {
            double frac = estimateCell(c.cx, c.cy, c.h);
            double s = 2.0 * c.h;
            area += frac * s * s;
            continue;
        }

        double nh = 0.5 * c.h;
        int nd = c.depth + 1;
        q.push_back({c.cx - nh, c.cy - nh, nh, nd});
        q.push_back({c.cx - nh, c.cy + nh, nh, nd});
        q.push_back({c.cx + nh, c.cy - nh, nh, nd});
        q.push_back({c.cx + nh, c.cy + nh, nh, nd});
    }

    printf("%.10f\n", area);
    return 0;
}