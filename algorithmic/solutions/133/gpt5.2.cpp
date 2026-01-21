#include <bits/stdc++.h>
using namespace std;

struct FastScanner {
    static constexpr size_t BUFSIZE = 1 << 20;
    char buf[BUFSIZE];
    size_t idx = 0, size = 0;

    inline char read() {
        if (idx >= size) {
            size = fread(buf, 1, BUFSIZE, stdin);
            idx = 0;
            if (size == 0) return 0;
        }
        return buf[idx++];
    }

    inline bool skipBlanks() {
        char c;
        do {
            c = read();
            if (!c) return false;
        } while (c <= ' ');
        idx--;
        return true;
    }

    bool readInt(int &out) {
        if (!skipBlanks()) return false;
        char c = read();
        int sign = 1;
        if (c == '-') { sign = -1; c = read(); }
        int x = 0;
        while (c > ' ') {
            x = x * 10 + (c - '0');
            c = read();
        }
        out = x * sign;
        return true;
    }

    bool readDouble(double &out) {
        if (!skipBlanks()) return false;
        char c = read();
        int sign = 1;
        if (c == '-') { sign = -1; c = read(); }
        double x = 0.0;
        while (c >= '0' && c <= '9') {
            x = x * 10.0 + (c - '0');
            c = read();
        }
        if (c == '.') {
            double p = 1.0;
            c = read();
            while (c >= '0' && c <= '9') {
                p *= 0.1;
                x += (c - '0') * p;
                c = read();
            }
        }
        if (c == 'e' || c == 'E') {
            c = read();
            int esign = 1;
            if (c == '-') { esign = -1; c = read(); }
            else if (c == '+') { c = read(); }
            int e = 0;
            while (c >= '0' && c <= '9') {
                e = e * 10 + (c - '0');
                c = read();
            }
            x *= pow(10.0, esign * e);
        }
        out = x * sign;
        return true;
    }
};

struct Seg {
    float ax, ay, bx, by;
};

struct Node {
    float minx, miny, maxx, maxy;
    int left = -1, right = -1;
    int seg = -1; // >=0 for leaf
};

static inline uint32_t part1by1(uint32_t x) {
    x &= 0x0000ffffu;
    x = (x | (x << 8)) & 0x00FF00FFu;
    x = (x | (x << 4)) & 0x0F0F0F0Fu;
    x = (x | (x << 2)) & 0x33333333u;
    x = (x | (x << 1)) & 0x55555555u;
    return x;
}

static inline uint32_t morton2D_16bit(uint32_t x, uint32_t y) {
    return (part1by1(y) << 1) | part1by1(x);
}

static inline int clz32(uint32_t x) {
    return x ? __builtin_clz(x) : 32;
}

struct BVH {
    vector<Seg> segs;
    vector<uint32_t> keys;
    vector<int> order;
    vector<Node> nodes;
    int root = -1;
    double r2 = 0.0;

    static inline void combine(Node &p, const Node &a, const Node &b) {
        p.minx = min(a.minx, b.minx);
        p.miny = min(a.miny, b.miny);
        p.maxx = max(a.maxx, b.maxx);
        p.maxy = max(a.maxy, b.maxy);
    }

    int findSplit(int first, int last) const {
        uint32_t firstCode = keys[first];
        uint32_t lastCode = keys[last];
        if (firstCode == lastCode) return (first + last) >> 1;

        int commonPrefix = clz32(firstCode ^ lastCode);
        int split = first;
        int step = last - first;
        do {
            step = (step + 1) >> 1;
            int newSplit = split + step;
            if (newSplit < last) {
                uint32_t splitCode = keys[newSplit];
                int splitPrefix = clz32(firstCode ^ splitCode);
                if (splitPrefix > commonPrefix) split = newSplit;
            }
        } while (step > 1);
        return split;
    }

    int buildRange(int l, int r) {
        int idx = (int)nodes.size();
        nodes.push_back(Node{});
        if (l == r) {
            int sid = order[l];
            nodes[idx].seg = sid;
            const Seg &s = segs[sid];
            nodes[idx].minx = min(s.ax, s.bx);
            nodes[idx].miny = min(s.ay, s.by);
            nodes[idx].maxx = max(s.ax, s.bx);
            nodes[idx].maxy = max(s.ay, s.by);
            return idx;
        }

        int split = findSplit(l, r);
        int left = buildRange(l, split);
        int right = buildRange(split + 1, r);
        nodes[idx].left = left;
        nodes[idx].right = right;
        combine(nodes[idx], nodes[left], nodes[right]);
        return idx;
    }

    void radixSortKeys() {
        int m = (int)keys.size();
        vector<uint32_t> tmpK(m);
        vector<int> tmpO(m);
        static vector<int> cnt;
        cnt.assign(1 << 16, 0);

        auto pass = [&](int shift) {
            fill(cnt.begin(), cnt.end(), 0);
            for (int i = 0; i < m; i++) cnt[(keys[i] >> shift) & 0xFFFFu]++;
            int sum = 0;
            for (int i = 0; i < (1 << 16); i++) {
                int c = cnt[i];
                cnt[i] = sum;
                sum += c;
            }
            for (int i = 0; i < m; i++) {
                int b = (keys[i] >> shift) & 0xFFFFu;
                int pos = cnt[b]++;
                tmpK[pos] = keys[i];
                tmpO[pos] = order[i];
            }
            keys.swap(tmpK);
            order.swap(tmpO);
        };

        pass(0);
        pass(16);
    }

    void build(double r) {
        r2 = r * r;
        int m = (int)segs.size();
        keys.resize(m);
        order.resize(m);
        for (int i = 0; i < m; i++) order[i] = i;

        float minx = segs[0].ax, maxx = segs[0].ax;
        float miny = segs[0].ay, maxy = segs[0].ay;
        for (int i = 0; i < m; i++) {
            const Seg &s = segs[i];
            minx = min(minx, min(s.ax, s.bx));
            miny = min(miny, min(s.ay, s.by));
            maxx = max(maxx, max(s.ax, s.bx));
            maxy = max(maxy, max(s.ay, s.by));
        }
        float dx = maxx - minx, dy = maxy - miny;
        if (dx == 0) dx = 1;
        if (dy == 0) dy = 1;

        for (int i = 0; i < m; i++) {
            const Seg &s = segs[i];
            float cx = 0.5f * (s.ax + s.bx);
            float cy = 0.5f * (s.ay + s.by);
            float nx = (cx - minx) / dx;
            float ny = (cy - miny) / dy;
            nx = min(1.0f, max(0.0f, nx));
            ny = min(1.0f, max(0.0f, ny));
            uint32_t qx = (uint32_t)lrintf(nx * 65535.0f);
            uint32_t qy = (uint32_t)lrintf(ny * 65535.0f);
            keys[i] = morton2D_16bit(qx, qy);
        }

        radixSortKeys();

        nodes.clear();
        nodes.reserve(2u * (unsigned)m);
        if (m == 1) {
            root = buildRange(0, 0);
        } else {
            root = buildRange(0, m - 1);
        }
    }

    static inline double distPointAABB2(double px, double py, const Node &n) {
        double dx = 0.0, dy = 0.0;
        if (px < n.minx) dx = (double)n.minx - px;
        else if (px > n.maxx) dx = px - (double)n.maxx;
        if (py < n.miny) dy = (double)n.miny - py;
        else if (py > n.maxy) dy = py - (double)n.maxy;
        return dx * dx + dy * dy;
    }

    static inline double distRectAABB2(float rx0, float ry0, float rx1, float ry1, const Node &n) {
        double dx = 0.0, dy = 0.0;
        if (rx1 < n.minx) dx = (double)n.minx - (double)rx1;
        else if (rx0 > n.maxx) dx = (double)rx0 - (double)n.maxx;
        if (ry1 < n.miny) dy = (double)n.miny - (double)ry1;
        else if (ry0 > n.maxy) dy = (double)ry0 - (double)n.maxy;
        return dx * dx + dy * dy;
    }

    static inline double distPointSeg2(double px, double py, const Seg &s) {
        double ax = s.ax, ay = s.ay, bx = s.bx, by = s.by;
        double vx = bx - ax, vy = by - ay;
        double wx = px - ax, wy = py - ay;
        double denom = vx * vx + vy * vy;
        if (denom <= 0.0) {
            double dx = px - ax, dy = py - ay;
            return dx * dx + dy * dy;
        }
        double t = (wx * vx + wy * vy) / denom;
        if (t < 0.0) t = 0.0;
        else if (t > 1.0) t = 1.0;
        double cx = ax + t * vx;
        double cy = ay + t * vy;
        double dx = px - cx, dy = py - cy;
        return dx * dx + dy * dy;
    }

    bool pointInside(double px, double py, vector<int> &st) const {
        st.clear();
        st.push_back(root);
        while (!st.empty()) {
            int ni = st.back();
            st.pop_back();
            const Node &nd = nodes[ni];
            if (distPointAABB2(px, py, nd) > r2) continue;
            if (nd.seg >= 0) {
                if (distPointSeg2(px, py, segs[nd.seg]) <= r2) return true;
            } else {
                st.push_back(nd.left);
                st.push_back(nd.right);
            }
        }
        return false;
    }

    // Conservative: returns true if rectangle is within distance r of any segment bounding box.
    bool rectMayIntersect(float x0, float y0, float x1, float y1, vector<int> &st) const {
        st.clear();
        st.push_back(root);
        while (!st.empty()) {
            int ni = st.back();
            st.pop_back();
            const Node &nd = nodes[ni];
            if (distRectAABB2(x0, y0, x1, y1, nd) > r2) continue;
            if (nd.seg >= 0) return true;
            st.push_back(nd.left);
            st.push_back(nd.right);
        }
        return false;
    }
};

struct Cell {
    float x0, y0, x1, y1;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    FastScanner fs;

    int n;
    if (!fs.readInt(n)) return 0;
    vector<double> px(n), py(n);
    for (int i = 0; i < n; i++) {
        fs.readDouble(px[i]);
        fs.readDouble(py[i]);
    }

    int m;
    fs.readInt(m);

    BVH bvh;
    bvh.segs.resize(m);

    float minx = 0, miny = 0, maxx = 0, maxy = 0;
    for (int i = 0; i < m; i++) {
        int a, b;
        fs.readInt(a);
        fs.readInt(b);
        --a; --b;
        Seg s;
        s.ax = (float)px[a];
        s.ay = (float)py[a];
        s.bx = (float)px[b];
        s.by = (float)py[b];
        bvh.segs[i] = s;

        float sx0 = min(s.ax, s.bx), sx1 = max(s.ax, s.bx);
        float sy0 = min(s.ay, s.by), sy1 = max(s.ay, s.by);
        if (i == 0) { minx = sx0; maxx = sx1; miny = sy0; maxy = sy1; }
        else {
            minx = min(minx, sx0); maxx = max(maxx, sx1);
            miny = min(miny, sy0); maxy = max(maxy, sy1);
        }
    }

    double r;
    fs.readDouble(r);

    double p1, p2, p3, p4;
    fs.readDouble(p1);
    fs.readDouble(p2);
    fs.readDouble(p3);
    fs.readDouble(p4);

    bvh.build(r);

    float rr = (float)r;
    float bx0 = minx - rr, by0 = miny - rr, bx1 = maxx + rr, by1 = maxy + rr;

    float eps = (float)max(0.001, min(0.05, r / 4.0));

    vector<Cell> stack;
    stack.reserve(1 << 20);
    stack.push_back(Cell{bx0, by0, bx1, by1});

    vector<int> stPoint, stRect;
    stPoint.reserve(2048);
    stRect.reserve(2048);

    double area = 0.0;
    size_t processed = 0;
    const size_t hardLimit = 12000000; // safety cap on processed cells

    while (!stack.empty()) {
        Cell c = stack.back();
        stack.pop_back();
        processed++;
        if (processed > hardLimit) {
            // fallback: coarse estimate remaining cells by 1-sample center
            while (!stack.empty()) {
                Cell d = stack.back();
                stack.pop_back();
                float w = d.x1 - d.x0, h = d.y1 - d.y0;
                if (w <= 0 || h <= 0) continue;
                if (!bvh.rectMayIntersect(d.x0, d.y0, d.x1, d.y1, stRect)) continue;
                double cx = 0.5 * ((double)d.x0 + (double)d.x1);
                double cy = 0.5 * ((double)d.y0 + (double)d.y1);
                if (bvh.pointInside(cx, cy, stPoint)) area += (double)w * (double)h;
            }
            break;
        }

        float w = c.x1 - c.x0, h = c.y1 - c.y0;
        if (w <= 0 || h <= 0) continue;

        if (!bvh.rectMayIntersect(c.x0, c.y0, c.x1, c.y1, stRect)) continue;

        float maxSide = max(w, h);
        if (maxSide <= eps) {
            // leaf: 4x4 samples
            int inside = 0;
            const int S = 16;
            for (int i = 0; i < 4; i++) {
                double sx = (double)c.x0 + (i + 0.5) * (double)w / 4.0;
                for (int j = 0; j < 4; j++) {
                    double sy = (double)c.y0 + (j + 0.5) * (double)h / 4.0;
                    inside += bvh.pointInside(sx, sy, stPoint) ? 1 : 0;
                }
            }
            area += (double)inside * ((double)w * (double)h) / (double)S;
            continue;
        }

        // try full inside with 3x3 samples
        bool allInside = true;
        for (int i = 0; i < 3 && allInside; i++) {
            double sx = (double)c.x0 + (double)i * (double)w / 2.0;
            for (int j = 0; j < 3; j++) {
                double sy = (double)c.y0 + (double)j * (double)h / 2.0;
                if (!bvh.pointInside(sx, sy, stPoint)) { allInside = false; break; }
            }
        }
        if (allInside) {
            area += (double)w * (double)h;
            continue;
        }

        float xm = 0.5f * (c.x0 + c.x1);
        float ym = 0.5f * (c.y0 + c.y1);
        stack.push_back(Cell{c.x0, c.y0, xm, ym});
        stack.push_back(Cell{xm, c.y0, c.x1, ym});
        stack.push_back(Cell{c.x0, ym, xm, c.y1});
        stack.push_back(Cell{xm, ym, c.x1, c.y1});
    }

    cout.setf(std::ios::fixed);
    cout << setprecision(10) << area << "\n";
    return 0;
}