#include <bits/stdc++.h>
using namespace std;

struct FastScanner {
    static constexpr size_t BUFSIZE = 1 << 20;
    size_t idx = 0, size = 0;
    unsigned char buf[BUFSIZE];

    inline unsigned char read() {
        if (idx >= size) {
            size = fread(buf, 1, BUFSIZE, stdin);
            idx = 0;
            if (size == 0) return 0;
        }
        return buf[idx++];
    }

    template <class T>
    bool readInt(T &out) {
        unsigned char c;
        do {
            c = read();
            if (!c) return false;
        } while (c <= ' ');
        int sign = 1;
        if (c == '-') {
            sign = -1;
            c = read();
        }
        long long val = 0;
        while (c > ' ') {
            val = val * 10 + (c - '0');
            c = read();
        }
        out = (T)(val * sign);
        return true;
    }

    bool readDouble(double &out) {
        unsigned char c;
        do {
            c = read();
            if (!c) return false;
        } while (c <= ' ');
        int sign = 1;
        if (c == '-') {
            sign = -1;
            c = read();
        }
        double val = 0.0;
        while (c >= '0' && c <= '9') {
            val = val * 10.0 + (c - '0');
            c = read();
        }
        double frac = 0.0, base = 1.0;
        if (c == '.') {
            c = read();
            while (c >= '0' && c <= '9') {
                frac = frac * 10.0 + (c - '0');
                base *= 10.0;
                c = read();
            }
        }
        double res = val + frac / base;
        if (c == 'e' || c == 'E') {
            c = read();
            int esign = 1;
            if (c == '-') { esign = -1; c = read(); }
            else if (c == '+') { c = read(); }
            int exp = 0;
            while (c >= '0' && c <= '9') {
                exp = exp * 10 + (c - '0');
                c = read();
            }
            res *= pow(10.0, esign * exp);
        }
        out = sign * res;
        return true;
    }
};

static inline uint64_t splitBy1(uint32_t a) {
    uint64_t x = a;
    x = (x | (x << 16)) & 0x0000FFFF0000FFFFULL;
    x = (x | (x << 8))  & 0x00FF00FF00FF00FFULL;
    x = (x | (x << 4))  & 0x0F0F0F0F0F0F0F0FULL;
    x = (x | (x << 2))  & 0x3333333333333333ULL;
    x = (x | (x << 1))  & 0x5555555555555555ULL;
    return x;
}

static inline uint64_t morton2D(uint32_t x, uint32_t y) {
    return splitBy1(x) | (splitBy1(y) << 1);
}

struct BVHNode {
    float minx, miny, maxx, maxy;
    int left;   // -1 for leaf
    int right;  // leaf: segId, internal: right child
};

static inline double dist2_point_aabb(double px, double py, const BVHNode &nd) {
    double dx = 0.0;
    if (px < nd.minx) dx = nd.minx - px;
    else if (px > nd.maxx) dx = px - nd.maxx;
    double dy = 0.0;
    if (py < nd.miny) dy = nd.miny - py;
    else if (py > nd.maxy) dy = py - nd.maxy;
    return dx * dx + dy * dy;
}

static inline double dist2_point_segment(double px, double py, float ax, float ay, float bx, float by) {
    double vx = (double)bx - (double)ax;
    double vy = (double)by - (double)ay;
    double wx = px - (double)ax;
    double wy = py - (double)ay;
    double c2 = vx * vx + vy * vy;
    if (c2 <= 0.0) {
        double dx = px - (double)ax, dy = py - (double)ay;
        return dx * dx + dy * dy;
    }
    double c1 = wx * vx + wy * vy;
    if (c1 <= 0.0) {
        double dx = px - (double)ax, dy = py - (double)ay;
        return dx * dx + dy * dy;
    }
    if (c1 >= c2) {
        double dx = px - (double)bx, dy = py - (double)by;
        return dx * dx + dy * dy;
    }
    double t = c1 / c2;
    double qx = (double)ax + t * vx;
    double qy = (double)ay + t * vy;
    double dx = px - qx, dy = py - qy;
    return dx * dx + dy * dy;
}

struct Solver {
    int n = 0;
    int m = 0;
    vector<float> px, py;
    vector<float> sax, say, sbx, sby;

    vector<BVHNode> nodes;
    int root = -1;

    inline bool covered(double x, double y, double R) const {
        double R2 = R * R;
        int st[128];
        int top = 0;
        st[top++] = root;
        while (top) {
            int idx = st[--top];
            const BVHNode &nd = nodes[idx];
            if (dist2_point_aabb(x, y, nd) > R2) continue;
            if (nd.left < 0) {
                int seg = nd.right;
                if (dist2_point_segment(x, y, sax[seg], say[seg], sbx[seg], sby[seg]) <= R2) return true;
            } else {
                int l = nd.left, r = nd.right;
                double dl = dist2_point_aabb(x, y, nodes[l]);
                double dr = dist2_point_aabb(x, y, nodes[r]);
                if (dl < dr) { st[top++] = r; st[top++] = l; }
                else { st[top++] = l; st[top++] = r; }
            }
        }
        return false;
    }

    void buildBVH() {
        if (m <= 0) return;
        if (m == 1) {
            nodes.resize(1);
            BVHNode &leaf = nodes[0];
            leaf.left = -1;
            leaf.right = 0;
            leaf.minx = min(sax[0], sbx[0]);
            leaf.maxx = max(sax[0], sbx[0]);
            leaf.miny = min(say[0], sby[0]);
            leaf.maxy = max(say[0], sby[0]);
            root = 0;
            return;
        }

        double minCx = 1e300, minCy = 1e300, maxCx = -1e300, maxCy = -1e300;
        for (int i = 0; i < m; i++) {
            double cx = 0.5 * ((double)sax[i] + (double)sbx[i]);
            double cy = 0.5 * ((double)say[i] + (double)sby[i]);
            minCx = min(minCx, cx);
            minCy = min(minCy, cy);
            maxCx = max(maxCx, cx);
            maxCy = max(maxCy, cy);
        }
        double dx = maxCx - minCx;
        double dy = maxCy - minCy;
        if (dx <= 0) dx = 1.0;
        if (dy <= 0) dy = 1.0;

        static constexpr int BITS = 21;
        static constexpr uint32_t GRID = (1u << BITS) - 1;
        static constexpr int IDBITS = 22;

        struct KeySeg { uint64_t key; int seg; };
        vector<KeySeg> order;
        order.resize(m);
        for (int i = 0; i < m; i++) {
            double cx = 0.5 * ((double)sax[i] + (double)sbx[i]);
            double cy = 0.5 * ((double)say[i] + (double)sby[i]);
            double ux = (cx - minCx) / dx;
            double uy = (cy - minCy) / dy;
            if (ux < 0) ux = 0; if (ux > 1) ux = 1;
            if (uy < 0) uy = 0; if (uy > 1) uy = 1;
            uint32_t xi = (uint32_t)min<double>(GRID, floor(ux * GRID + 0.5));
            uint32_t yi = (uint32_t)min<double>(GRID, floor(uy * GRID + 0.5));
            uint64_t mcode = morton2D(xi, yi);
            uint64_t key = (mcode << IDBITS) | (uint64_t)i; // unique
            order[i] = { key, i };
        }
        sort(order.begin(), order.end(), [](const KeySeg &a, const KeySeg &b) {
            return a.key < b.key;
        });

        vector<uint64_t> keys(m);
        vector<int> segSorted(m);
        for (int i = 0; i < m; i++) {
            keys[i] = order[i].key;
            segSorted[i] = order[i].seg;
        }
        order.clear();
        order.shrink_to_fit();

        int internalCnt = m - 1;
        int leafOffset = internalCnt;
        int totalNodes = internalCnt + m;
        nodes.resize(totalNodes);
        vector<int> parent(totalNodes, -1);

        // leaves
        for (int i = 0; i < m; i++) {
            int leafIdx = leafOffset + i;
            int seg = segSorted[i];
            BVHNode &leaf = nodes[leafIdx];
            leaf.left = -1;
            leaf.right = seg;
            float ax = sax[seg], ay = say[seg], bx = sbx[seg], by = sby[seg];
            leaf.minx = min(ax, bx);
            leaf.maxx = max(ax, bx);
            leaf.miny = min(ay, by);
            leaf.maxy = max(ay, by);
        }
        segSorted.clear();
        segSorted.shrink_to_fit();

        auto delta = [&](int i, int j) -> int {
            if (j < 0 || j >= m) return -1;
            if (i == j) return 64;
            uint64_t x = keys[i] ^ keys[j];
            return __builtin_clzll(x);
        };

        auto findSplit = [&](int first, int last) -> int {
            int common = delta(first, last);
            int split = first;
            int step = last - first;
            do {
                step = (step + 1) >> 1;
                int newSplit = split + step;
                if (newSplit < last) {
                    int c = delta(first, newSplit);
                    if (c > common) split = newSplit;
                }
            } while (step > 1);
            return split;
        };

        // internal nodes
        for (int i = 0; i < internalCnt; i++) {
            int d = (delta(i, i + 1) > delta(i, i - 1)) ? 1 : -1;
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

            int split = findSplit(first, last);

            int leftChild = (split == first) ? (leafOffset + split) : split;
            int rightChild = (split + 1 == last) ? (leafOffset + (split + 1)) : (split + 1);

            BVHNode &nd = nodes[i];
            nd.left = leftChild;
            nd.right = rightChild;

            parent[leftChild] = i;
            parent[rightChild] = i;
        }

        // find root
        root = -1;
        for (int i = 0; i < internalCnt; i++) {
            if (parent[i] == -1) { root = i; break; }
        }
        if (root == -1) root = 0;

        // bottom-up bbox
        vector<int> cnt(internalCnt, 0);
        for (int li = 0; li < m; li++) {
            int nodeIdx = leafOffset + li;
            int p = parent[nodeIdx];
            while (p != -1) {
                int c = ++cnt[p];
                if (c == 2) {
                    int lc = nodes[p].left;
                    int rc = nodes[p].right;
                    BVHNode &nd = nodes[p];
                    const BVHNode &L = nodes[lc];
                    const BVHNode &R = nodes[rc];
                    nd.minx = min(L.minx, R.minx);
                    nd.miny = min(L.miny, R.miny);
                    nd.maxx = max(L.maxx, R.maxx);
                    nd.maxy = max(L.maxy, R.maxy);
                    p = parent[p];
                } else {
                    break;
                }
            }
        }

        keys.clear();
        keys.shrink_to_fit();
        parent.clear();
        parent.shrink_to_fit();
        cnt.clear();
        cnt.shrink_to_fit();
    }
};

struct Rect {
    double x0, x1, y0, y1;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    FastScanner fs;
    Solver solver;

    if (!fs.readInt(solver.n)) return 0;
    solver.px.resize(solver.n);
    solver.py.resize(solver.n);
    for (int i = 0; i < solver.n; i++) {
        double x, y;
        fs.readDouble(x);
        fs.readDouble(y);
        solver.px[i] = (float)x;
        solver.py[i] = (float)y;
    }

    fs.readInt(solver.m);
    solver.m = max(0, solver.m);
    solver.sax.resize(solver.m);
    solver.say.resize(solver.m);
    solver.sbx.resize(solver.m);
    solver.sby.resize(solver.m);

    double minX = 1e300, minY = 1e300, maxX = -1e300, maxY = -1e300;

    for (int i = 0; i < solver.m; i++) {
        int a, b;
        fs.readInt(a);
        fs.readInt(b);
        --a; --b;
        float ax = solver.px[a], ay = solver.py[a];
        float bx = solver.px[b], by = solver.py[b];
        solver.sax[i] = ax; solver.say[i] = ay;
        solver.sbx[i] = bx; solver.sby[i] = by;
        minX = min<double>(minX, min((double)ax, (double)bx));
        maxX = max<double>(maxX, max((double)ax, (double)bx));
        minY = min<double>(minY, min((double)ay, (double)by));
        maxY = max<double>(maxY, max((double)ay, (double)by));
    }

    double r;
    fs.readDouble(r);
    double p1, p2, p3, p4;
    fs.readDouble(p1); fs.readDouble(p2); fs.readDouble(p3); fs.readDouble(p4);

    const double PI = acos(-1.0);

    if (solver.m == 0) {
        printf("%.10f\n", 0.0);
        return 0;
    }

    if (solver.m == 1) {
        double dx = (double)solver.sax[0] - (double)solver.sbx[0];
        double dy = (double)solver.say[0] - (double)solver.sby[0];
        double len = hypot(dx, dy);
        double ans = 2.0 * r * len + PI * r * r;
        printf("%.10f\n", ans);
        return 0;
    }

    solver.buildBVH();

    // integration bbox (tight)
    minX -= r; maxX += r;
    minY -= r; maxY += r;
    minX -= 1e-9; maxX += 1e-9;
    minY -= 1e-9; maxY += 1e-9;

    Rect rootRect{minX, maxX, minY, maxY};

    double minS = min(0.1, max(0.01, r / 50.0));
    long long splitBudget = 3000000; // max subdivisions

    vector<Rect> st;
    st.reserve(256);
    st.push_back(rootRect);

    double area = 0.0;
    while (!st.empty()) {
        Rect rc = st.back();
        st.pop_back();

        double w = rc.x1 - rc.x0;
        double h = rc.y1 - rc.y0;
        if (w <= 0 || h <= 0) continue;

        double cx = 0.5 * (rc.x0 + rc.x1);
        double cy = 0.5 * (rc.y0 + rc.y1);
        double halfDiag = 0.5 * hypot(w, h);

        double R_out = r + halfDiag;
        if (!solver.covered(cx, cy, R_out)) continue;

        if (r > halfDiag) {
            double R_in = r - halfDiag;
            if (solver.covered(cx, cy, R_in)) {
                area += w * h;
                continue;
            }
        }

        if (max(w, h) <= minS || splitBudget <= 0) {
            // 9-point sampling
            double xm = cx, ym = cy;
            int cnt = 0;
            cnt += solver.covered(rc.x0, rc.y0, r);
            cnt += solver.covered(rc.x1, rc.y0, r);
            cnt += solver.covered(rc.x0, rc.y1, r);
            cnt += solver.covered(rc.x1, rc.y1, r);
            cnt += solver.covered(xm, rc.y0, r);
            cnt += solver.covered(xm, rc.y1, r);
            cnt += solver.covered(rc.x0, ym, r);
            cnt += solver.covered(rc.x1, ym, r);
            cnt += solver.covered(xm, ym, r);
            area += (w * h) * ((double)cnt / 9.0);
            continue;
        }

        // subdivide into 4
        splitBudget--;
        double mx = cx;
        double my = cy;

        // push in an order that keeps stack small (DFS)
        st.push_back(Rect{mx, rc.x1, my, rc.y1});
        st.push_back(Rect{rc.x0, mx, my, rc.y1});
        st.push_back(Rect{mx, rc.x1, rc.y0, my});
        st.push_back(Rect{rc.x0, mx, rc.y0, my});
    }

    printf("%.10f\n", area);
    return 0;
}