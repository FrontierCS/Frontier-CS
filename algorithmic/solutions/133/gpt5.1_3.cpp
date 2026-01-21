#include <bits/stdc++.h>
using namespace std;

struct Segment {
    double x1, y1, x2, y2;
};

struct Node {
    double minx, maxx, miny, maxy;
    int l, r;      // [l, r)
    int left, right;
};

const double INF = 1e100;
int LEAF_SIZE = 8;

vector<Segment> segs;
vector<int> idxs;
vector<Node> nodes;
double radius, r2;

inline double distPointSeg2(double px, double py, const Segment &s) {
    double vx = s.x2 - s.x1;
    double vy = s.y2 - s.y1;
    double wx = px - s.x1;
    double wy = py - s.y1;
    double len2 = vx * vx + vy * vy;
    double t;
    if (len2 <= 0.0) {
        t = 0.0;
    } else {
        t = (vx * wx + vy * wy) / len2;
        if (t < 0.0) t = 0.0;
        else if (t > 1.0) t = 1.0;
    }
    double cx = s.x1 + t * vx;
    double cy = s.y1 + t * vy;
    double dx = px - cx;
    double dy = py - cy;
    return dx * dx + dy * dy;
}

inline double boxDist2(const Node &nd, double px, double py) {
    double dx = 0.0, dy = 0.0;
    if (px < nd.minx) dx = nd.minx - px;
    else if (px > nd.maxx) dx = px - nd.maxx;
    if (py < nd.miny) dy = nd.miny - py;
    else if (py > nd.maxy) dy = py - nd.maxy;
    return dx * dx + dy * dy;
}

int build(int l, int r) {
    Node nd;
    nd.l = l;
    nd.r = r;
    nd.left = nd.right = -1;
    double minx = INF, maxx = -INF, miny = INF, maxy = -INF;
    for (int i = l; i < r; ++i) {
        const Segment &s = segs[idxs[i]];
        if (s.x1 < minx) minx = s.x1;
        if (s.x1 > maxx) maxx = s.x1;
        if (s.x2 < minx) minx = s.x2;
        if (s.x2 > maxx) maxx = s.x2;
        if (s.y1 < miny) miny = s.y1;
        if (s.y1 > maxy) maxy = s.y1;
        if (s.y2 < miny) miny = s.y2;
        if (s.y2 > maxy) maxy = s.y2;
    }
    nd.minx = minx;
    nd.maxx = maxx;
    nd.miny = miny;
    nd.maxy = maxy;

    int cur = (int)nodes.size();
    nodes.push_back(nd);

    int cnt = r - l;
    if (cnt <= LEAF_SIZE) return cur;

    double wx = maxx - minx;
    double wy = maxy - miny;
    int dim = (wx > wy) ? 0 : 1;
    int mid = (l + r) >> 1;

    if (dim == 0) {
        nth_element(idxs.begin() + l, idxs.begin() + mid, idxs.begin() + r,
                    [](int a, int b) {
                        double ca = (segs[a].x1 + segs[a].x2) * 0.5;
                        double cb = (segs[b].x1 + segs[b].x2) * 0.5;
                        return ca < cb;
                    });
    } else {
        nth_element(idxs.begin() + l, idxs.begin() + mid, idxs.begin() + r,
                    [](int a, int b) {
                        double ca = (segs[a].y1 + segs[a].y2) * 0.5;
                        double cb = (segs[b].y1 + segs[b].y2) * 0.5;
                        return ca < cb;
                    });
    }

    if (mid == l || mid == r) {
        // All keys effectively equal; treat as leaf
        return cur;
    }

    nodes[cur].left = build(l, mid);
    nodes[cur].right = build(mid, r);
    return cur;
}

bool query(int nodeIdx, double px, double py) {
    const Node &nd = nodes[nodeIdx];
    if (boxDist2(nd, px, py) > r2) return false;

    if (nd.left == -1 && nd.right == -1) {
        for (int i = nd.l; i < nd.r; ++i) {
            const Segment &s = segs[idxs[i]];
            if (distPointSeg2(px, py, s) <= r2) return true;
        }
        return false;
    }

    int left = nodes[nodeIdx].left;
    int right = nodes[nodeIdx].right;

    const Node &ln = nodes[left];
    const Node &rn = nodes[right];

    double dl = boxDist2(ln, px, py);
    double dr = boxDist2(rn, px, py);

    if (dl < dr) {
        if (dl <= r2 && query(left, px, py)) return true;
        if (dr <= r2 && query(right, px, py)) return true;
    } else {
        if (dr <= r2 && query(right, px, py)) return true;
        if (dl <= r2 && query(left, px, py)) return true;
    }
    return false;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    vector<double> xs(n), ys(n);
    for (int i = 0; i < n; ++i) cin >> xs[i] >> ys[i];

    int m;
    cin >> m;

    segs.reserve(m);
    for (int i = 0; i < m; ++i) {
        int a, b;
        cin >> a >> b;
        --a; --b;
        Segment s;
        s.x1 = xs[a];
        s.y1 = ys[a];
        s.x2 = xs[b];
        s.y2 = ys[b];
        segs.push_back(s);
    }

    cin >> radius;
    double p1, p2, p3, p4;
    cin >> p1 >> p2 >> p3 >> p4; // read but unused

    if (m == 0) {
        cout.setf(ios::fixed);
        cout << setprecision(7) << 0.0 << "\n";
        return 0;
    }

    r2 = radius * radius;

    int mActual = (int)segs.size();
    idxs.resize(mActual);
    for (int i = 0; i < mActual; ++i) idxs[i] = i;

    nodes.reserve((size_t)mActual * 2u);
    int root = build(0, mActual);

    double minx = xs[0], maxx = xs[0];
    double miny = ys[0], maxy = ys[0];
    for (int i = 1; i < n; ++i) {
        if (xs[i] < minx) minx = xs[i];
        if (xs[i] > maxx) maxx = xs[i];
        if (ys[i] < miny) miny = ys[i];
        if (ys[i] > maxy) maxy = ys[i];
    }
    minx -= radius;
    maxx += radius;
    miny -= radius;
    maxy += radius;

    double widthX = maxx - minx;
    double widthY = maxy - miny;
    if (widthX <= 0.0) widthX = 2.0 * radius;
    if (widthY <= 0.0) widthY = 2.0 * radius;

    const long long targetCells = 1200000LL;
    double ratio = widthX / widthY;
    if (!(ratio > 0.0)) ratio = 1.0;

    long long Nx = (long long) sqrt((long double)targetCells * ratio);
    if (Nx < 1) Nx = 1;
    if (Nx > 3000) Nx = 3000;
    long long Ny = targetCells / Nx;
    if (Ny < 1) Ny = 1;

    long long totalCells = Nx * Ny;
    double hx = widthX / (double)Nx;
    double hy = widthY / (double)Ny;

    long long inside = 0;
    for (long long ix = 0; ix < Nx; ++ix) {
        double x = minx + (ix + 0.5) * hx;
        for (long long iy = 0; iy < Ny; ++iy) {
            double y = miny + (iy + 0.5) * hy;
            if (query(root, x, y)) ++inside;
        }
    }

    double rectArea = widthX * widthY;
    double area = rectArea * ((long double)inside / (long double)totalCells);

    cout.setf(ios::fixed);
    cout << setprecision(7) << area << "\n";

    return 0;
}