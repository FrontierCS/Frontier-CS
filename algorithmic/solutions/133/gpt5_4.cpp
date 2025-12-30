#include <bits/stdc++.h>
using namespace std;

struct RNG {
    uint64_t s;
    RNG(uint64_t seed = 88172645463393265ull) : s(seed) {}
    inline uint64_t next() {
        s ^= s >> 12;
        s ^= s << 25;
        s ^= s >> 27;
        return s * 2685821657736338717ull;
    }
    inline double uniform01() {
        return (next() >> 11) * (1.0 / 9007199254740992.0); // 2^53
    }
    inline double uniform(double a, double b) {
        return a + (b - a) * uniform01();
    }
};

struct Segment {
    double x0, y0, x1, y1;
    double ux, uy; // unit direction
    double len;
    double area;
    double minx, miny, maxx, maxy;
};

static inline bool containsPoint(const Segment &s, double x, double y, double r2) {
    if (s.len == 0.0) {
        double dx = x - s.x0, dy = y - s.y0;
        return dx*dx + dy*dy <= r2;
    }
    double vx = x - s.x0, vy = y - s.y0;
    double t = vx * s.ux + vy * s.uy;
    if (t <= 0.0) {
        double dx = vx, dy = vy;
        return dx*dx + dy*dy <= r2;
    } else if (t >= s.len) {
        double wx = x - s.x1, wy = y - s.y1;
        return wx*wx + wy*wy <= r2;
    } else {
        double d2 = vx*vx + vy*vy - t*t;
        return d2 <= r2;
    }
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
    vector<pair<int,int>> edges(m);
    for (int i = 0; i < m; ++i) {
        int a,b;
        cin >> a >> b;
        --a; --b;
        edges[i] = {a,b};
    }
    double r;
    cin >> r;
    double p1, p2, p3, p4;
    cin >> p1 >> p2 >> p3 >> p4;
    if (m == 0 || r <= 0) {
        cout.setf(std::ios::fixed); cout << setprecision(7) << 0.0 << "\n";
        return 0;
    }

    vector<Segment> segs;
    segs.reserve(m);
    double minX = 1e100, minY = 1e100, maxX = -1e100, maxY = -1e100;
    double r2 = r * r;
    double totalArea = 0.0;

    for (int i = 0; i < m; ++i) {
        int a = edges[i].first;
        int b = edges[i].second;
        Segment s;
        s.x0 = xs[a]; s.y0 = ys[a]; s.x1 = xs[b]; s.y1 = ys[b];
        double dx = s.x1 - s.x0, dy = s.y1 - s.y0;
        s.len = hypot(dx, dy);
        if (s.len > 0) {
            s.ux = dx / s.len;
            s.uy = dy / s.len;
        } else {
            s.ux = 1.0; s.uy = 0.0;
        }
        s.area = 2.0 * r * s.len + M_PI * r2;
        s.minx = min(s.x0, s.x1) - r;
        s.maxx = max(s.x0, s.x1) + r;
        s.miny = min(s.y0, s.y1) - r;
        s.maxy = max(s.y0, s.y1) + r;
        minX = min(minX, s.minx);
        minY = min(minY, s.miny);
        maxX = max(maxX, s.maxx);
        maxY = max(maxY, s.maxy);
        totalArea += s.area;
        segs.push_back(s);
    }

    if (totalArea == 0.0) {
        cout.setf(std::ios::fixed); cout << setprecision(7) << 0.0 << "\n";
        return 0;
    }

    // Build spatial grid
    double pad = 1e-9;
    minX -= pad; minY -= pad; maxX += pad; maxY += pad;
    double cellSize = max(1.0, min(5.0, r)); // keep cell size reasonable
    double width = maxX - minX, height = maxY - minY;
    int nx = max(1, (int)ceil(width / cellSize));
    int ny = max(1, (int)ceil(height / cellSize));
    double invCell = 1.0 / cellSize;

    vector<int> counts(nx * ny, 0);

    auto clampi = [](int v, int lo, int hi)->int { if (v < lo) return lo; if (v > hi) return hi; return v; };

    for (const auto &s : segs) {
        int ix0 = clampi((int)floor((s.minx - minX) * invCell), 0, nx - 1);
        int ix1 = clampi((int)floor((s.maxx - minX) * invCell), 0, nx - 1);
        int iy0 = clampi((int)floor((s.miny - minY) * invCell), 0, ny - 1);
        int iy1 = clampi((int)floor((s.maxy - minY) * invCell), 0, ny - 1);
        for (int iy = iy0; iy <= iy1; ++iy) {
            int base = iy * nx;
            for (int ix = ix0; ix <= ix1; ++ix) {
                counts[base + ix]++;
            }
        }
    }

    vector<vector<int>> grid(nx * ny);
    for (int i = 0; i < nx * ny; ++i) {
        if (counts[i] > 0) grid[i].reserve(counts[i]);
    }

    for (int id = 0; id < (int)segs.size(); ++id) {
        const auto &s = segs[id];
        int ix0 = clampi((int)floor((s.minx - minX) * invCell), 0, nx - 1);
        int ix1 = clampi((int)floor((s.maxx - minX) * invCell), 0, nx - 1);
        int iy0 = clampi((int)floor((s.miny - minY) * invCell), 0, ny - 1);
        int iy1 = clampi((int)floor((s.maxy - minY) * invCell), 0, ny - 1);
        for (int iy = iy0; iy <= iy1; ++iy) {
            int base = iy * nx;
            for (int ix = ix0; ix <= ix1; ++ix) {
                grid[base + ix].push_back(id);
            }
        }
    }

    // Build cumulative distribution for selecting segments proportional to area
    vector<double> cdf(segs.size() + 1, 0.0);
    for (size_t i = 0; i < segs.size(); ++i) cdf[i + 1] = cdf[i] + segs[i].area;

    // Monte Carlo sampling
    RNG rng((uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count() ^ 0x9E3779B97F4A7C15ull);

    auto now = chrono::steady_clock::now();
    auto tStart = now;
    const double timeBudgetSec = 19.2; // leave some margin
    double elapsed = 0.0;

    const int chunk = 1000;
    long long samples = 0;
    long double accum = 0.0L;

    // Precompute for sampling: for each segment, prob of rectangle
    vector<double> rectProb(segs.size());
    for (size_t i = 0; i < segs.size(); ++i) {
        if (segs[i].area > 0.0) rectProb[i] = (2.0 * r * segs[i].len) / segs[i].area;
        else rectProb[i] = 0.0;
    }

    // Quick function to map coordinate to cell index
    auto cellIndex = [&](double x, double y) -> int {
        int ix = (int)floor((x - minX) * invCell);
        int iy = (int)floor((y - minY) * invCell);
        if (ix < 0) ix = 0; else if (ix >= nx) ix = nx - 1;
        if (iy < 0) iy = 0; else if (iy >= ny) iy = ny - 1;
        return iy * nx + ix;
    };

    // Sampling loop
    while (true) {
        for (int it = 0; it < chunk; ++it) {
            // pick segment by area
            double u = rng.uniform(0.0, totalArea);
            size_t lo = 0, hi = cdf.size() - 1;
            while (lo + 1 < hi) {
                size_t mid = (lo + hi) >> 1;
                if (cdf[mid] <= u) lo = mid;
                else hi = mid;
            }
            size_t idx = lo;
            const Segment &sg = segs[idx];

            // sample point uniformly in capsule
            double px, py;
            if (sg.len == 0.0) {
                double ang = rng.uniform(0.0, 2.0 * M_PI);
                double rad = r * sqrt(rng.uniform01());
                px = sg.x0 + rad * cos(ang);
                py = sg.y0 + rad * sin(ang);
            } else {
                double perp_x = -sg.uy, perp_y = sg.ux;
                double u01 = rng.uniform01();
                if (u01 < rectProb[idx]) {
                    double t = rng.uniform(0.0, sg.len);
                    double d = rng.uniform(-r, r);
                    px = sg.x0 + sg.ux * t + perp_x * d;
                    py = sg.y0 + sg.uy * t + perp_y * d;
                } else {
                    // choose left or right half-disk
                    if (rng.uniform01() < 0.5) {
                        // left half at p0: angles in [pi/2, 3pi/2]
                        double ang = rng.uniform(M_PI * 0.5, M_PI * 1.5);
                        double rad = r * sqrt(rng.uniform01());
                        double cx = sg.x0, cy = sg.y0;
                        double dx = sg.ux * cos(ang) + perp_x * sin(ang);
                        double dy = sg.uy * cos(ang) + perp_y * sin(ang);
                        px = cx + rad * dx;
                        py = cy + rad * dy;
                    } else {
                        // right half at p1: angles in [-pi/2, pi/2]
                        double ang = rng.uniform(-M_PI * 0.5, M_PI * 0.5);
                        double rad = r * sqrt(rng.uniform01());
                        double cx = sg.x1, cy = sg.y1;
                        double dx = sg.ux * cos(ang) + perp_x * sin(ang);
                        double dy = sg.uy * cos(ang) + perp_y * sin(ang);
                        px = cx + rad * dx;
                        py = cy + rad * dy;
                    }
                }
            }

            // compute coverage count k(x)
            int cid = cellIndex(px, py);
            int kcov = 0;
            const vector<int> &lst = grid[cid];
            for (int id : lst) {
                if (containsPoint(segs[id], px, py, r2)) ++kcov;
            }
            if (kcov <= 0) kcov = 1; // numerical safety

            accum += (long double)(totalArea / (double)kcov);
        }
        samples += chunk;
        auto tNow = chrono::steady_clock::now();
        elapsed = chrono::duration<double>(tNow - tStart).count();
        if (elapsed >= timeBudgetSec) break;
    }

    double areaEst = (samples > 0) ? (double)(accum / (long double)samples) : 0.0;
    cout.setf(std::ios::fixed);
    cout << setprecision(7) << areaEst << "\n";
    return 0;
}