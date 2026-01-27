#include <bits/stdc++.h>
using namespace std;

struct Segment {
    double x1, y1, x2, y2;
    double vx, vy;
    double invlen2;
    bool isPoint;
};

static uint64_t rng_state = 88172645463325252ull;
inline uint64_t rng64() {
    uint64_t x = rng_state;
    x ^= x >> 12;
    x ^= x << 25;
    x ^= x >> 27;
    rng_state = x;
    return x * 2685821657736338717ull;
}
inline double rand01() {
    return (rng64() >> 11) * (1.0 / 9007199254740992.0);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) {
        return 0;
    }
    vector<double> xs(n), ys(n);
    for (int i = 0; i < n; ++i) {
        cin >> xs[i] >> ys[i];
    }

    int m;
    cin >> m;

    vector<Segment> segs;
    segs.reserve(m);

    double minX = 1e100, maxX = -1e100;
    double minY = 1e100, maxY = -1e100;

    for (int i = 0; i < m; ++i) {
        int a, b;
        cin >> a >> b;
        --a; --b;
        Segment s;
        s.x1 = xs[a];
        s.y1 = ys[a];
        s.x2 = xs[b];
        s.y2 = ys[b];
        s.vx = s.x2 - s.x1;
        s.vy = s.y2 - s.y1;
        double len2 = s.vx * s.vx + s.vy * s.vy;
        if (len2 < 1e-18) {
            s.isPoint = true;
            s.invlen2 = 0.0;
        } else {
            s.isPoint = false;
            s.invlen2 = 1.0 / len2;
        }
        segs.push_back(s);
        double lx = min(s.x1, s.x2);
        double rx = max(s.x1, s.x2);
        double ly = min(s.y1, s.y2);
        double ry = max(s.y1, s.y2);
        if (lx < minX) minX = lx;
        if (rx > maxX) maxX = rx;
        if (ly < minY) minY = ly;
        if (ry > maxY) maxY = ry;
    }

    double r;
    cin >> r;
    double p1, p2, p3, p4;
    cin >> p1 >> p2 >> p3 >> p4; // read but ignore

    if (m == 0) {
        cout.setf(ios::fixed);
        cout << setprecision(7) << 0.0 << '\n';
        return 0;
    }

    double r2 = r * r;

    // expand bounding box by r
    minX -= r;
    maxX += r;
    minY -= r;
    maxY += r;

    // handle degenerate bounding box
    if (maxX <= minX) {
        maxX = minX + 2.0 * r + 1e-6;
    }
    if (maxY <= minY) {
        maxY = minY + 2.0 * r + 1e-6;
    }

    double widthX = maxX - minX;
    double widthY = maxY - minY;
    double areaTotal = widthX * widthY;

    // Monte Carlo sample count based on m
    long long N;
    if (m <= 2000) {
        long long tmp = 40000000LL / max(1, m);
        if (tmp < 20000) tmp = 20000;
        if (tmp > 2000000) tmp = 2000000;
        N = tmp;
    } else {
        long long tmp = 40000000LL / m;
        if (tmp < 1000) tmp = 1000;
        N = tmp;
    }

    long long insideCnt = 0;

    for (long long i = 0; i < N; ++i) {
        double ux = rand01();
        double uy = rand01();
        double px = minX + ux * widthX;
        double py = minY + uy * widthY;

        bool inside = false;

        for (int j = 0; j < m; ++j) {
            const Segment &s = segs[j];
            double dx, dy;
            if (s.isPoint) {
                dx = px - s.x1;
                dy = py - s.y1;
                if (dx * dx + dy * dy <= r2) {
                    inside = true;
                    break;
                }
            } else {
                double apx = px - s.x1;
                double apy = py - s.y1;
                double t = (apx * s.vx + apy * s.vy) * s.invlen2;
                double cx, cy;
                if (t <= 0.0) {
                    cx = s.x1;
                    cy = s.y1;
                } else if (t >= 1.0) {
                    cx = s.x2;
                    cy = s.y2;
                } else {
                    cx = s.x1 + t * s.vx;
                    cy = s.y1 + t * s.vy;
                }
                dx = px - cx;
                dy = py - cy;
                if (dx * dx + dy * dy <= r2) {
                    inside = true;
                    break;
                }
            }
        }

        if (inside) ++insideCnt;
    }

    double areaEst = areaTotal * (double)insideCnt / (double)N;

    cout.setf(ios::fixed);
    cout << setprecision(7) << areaEst << '\n';

    return 0;
}