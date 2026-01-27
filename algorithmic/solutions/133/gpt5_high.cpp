#include <bits/stdc++.h>
using namespace std;

struct FastRNG {
    uint64_t x;
    FastRNG(uint64_t seed=88172645463393265ull) : x(seed) {}
    inline uint64_t nextU64() {
        x ^= x >> 12;
        x ^= x << 25;
        x ^= x >> 27;
        return x * 2685821657736338717ull;
    }
    inline double nextDouble() {
        // 53-bit precision
        return (nextU64() >> 11) * (1.0 / 9007199254740992.0);
    }
};

struct Segment {
    double ax, ay, bx, by;
    double dx, dy, len2, invlen2;
    double bbx0, bbx1, bby0, bby1; // bounding box of capsule (segment expanded by r)
};

static inline bool pointNearSegment(double px, double py, const Segment& s, double r2) {
    double vx = px - s.ax;
    double vy = py - s.ay;
    if (s.len2 <= 1e-20) {
        double dx = px - s.ax, dy = py - s.ay;
        return dx*dx + dy*dy <= r2;
    }
    double t = (vx * s.dx + vy * s.dy) * s.invlen2;
    if (t < 0.0) t = 0.0;
    else if (t > 1.0) t = 1.0;
    double nx = s.ax + t * s.dx;
    double ny = s.ay + t * s.dy;
    double ddx = px - nx, ddy = py - ny;
    return ddx*ddx + ddy*ddy <= r2;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n;
    if (!(cin >> n)) {
        return 0;
    }
    vector<pair<double,double>> pts(n+1);
    for (int i = 1; i <= n; ++i) {
        double xi, yi;
        cin >> xi >> yi;
        pts[i] = {xi, yi};
    }
    int m;
    cin >> m;
    vector<pair<int,int>> edges;
    edges.reserve(m);
    for (int i = 0; i < m; ++i) {
        int a,b;
        cin >> a >> b;
        edges.emplace_back(a,b);
    }
    double r;
    cin >> r;
    double p1,p2,p3,p4;
    cin >> p1 >> p2 >> p3 >> p4; // read but not used

    if (m == 0) {
        cout.setf(std::ios::fixed); cout << setprecision(7) << 0.0 << "\n";
        return 0;
    }

    vector<Segment> segs;
    segs.reserve(m);

    double xmin = 1e100, ymin = 1e100, xmax = -1e100, ymax = -1e100;
    for (auto &e : edges) {
        auto A = pts[e.first];
        auto B = pts[e.second];
        double ax = A.first, ay = A.second;
        double bx = B.first, by = B.second;
        double dx = bx - ax, dy = by - ay;
        double len2 = dx*dx + dy*dy;
        double invlen2 = (len2 <= 1e-20) ? 0.0 : 1.0 / len2;
        Segment s;
        s.ax = ax; s.ay = ay; s.bx = bx; s.by = by;
        s.dx = dx; s.dy = dy; s.len2 = len2; s.invlen2 = invlen2;
        double bbx0 = min(ax, bx) - r, bbx1 = max(ax, bx) + r;
        double bby0 = min(ay, by) - r, bby1 = max(ay, by) + r;
        s.bbx0 = bbx0; s.bbx1 = bbx1; s.bby0 = bby0; s.bby1 = bby1;
        xmin = min(xmin, bbx0);
        xmax = max(xmax, bbx1);
        ymin = min(ymin, bby0);
        ymax = max(ymax, bby1);
        segs.push_back(s);
    }

    // If no area due to zero radius (shouldn't happen per constraints), print 0
    if (r <= 0) {
        cout.setf(std::ios::fixed); cout << setprecision(7) << 0.0 << "\n";
        return 0;
    }

    double width = xmax - xmin;
    double height = ymax - ymin;
    if (width <= 0 || height <= 0) {
        cout.setf(std::ios::fixed); cout << setprecision(7) << 0.0 << "\n";
        return 0;
    }
    double areaBB = width * height;
    double r2 = r * r;

    // Build spatial grid index
    // Target number of cells
    const int NcellsTarget = 60000; // balance memory/time
    double ratio = width / height;
    if (ratio <= 0) ratio = 1.0;
    int Nx = (int)max(1.0, floor(sqrt((double)NcellsTarget * ratio)));
    int Ny = (int)max(1.0, floor((double)NcellsTarget / max(1, Nx)));
    // Ensure not too fine vs radius
    auto adjustByRadius = [&](int& N, double len) {
        double cell = len / N;
        double minCell = max(0.5, 0.5 * r); // don't make too fine
        while (cell < minCell && N > 16) {
            N = (N + 1) / 2;
            cell = len / N;
        }
    };
    adjustByRadius(Nx, width);
    adjustByRadius(Ny, height);
    double cellX = width / Nx;
    double cellY = height / Ny;

    vector<vector<int>> grid;
    grid.resize((size_t)Nx * (size_t)Ny);

    auto clampi = [](int v, int lo, int hi)->int{ if (v < lo) return lo; if (v > hi) return hi; return v; };

    size_t totalAssigned = 0;
    for (int i = 0; i < (int)segs.size(); ++i) {
        const Segment& s = segs[i];
        int ix0 = clampi((int)floor((s.bbx0 - xmin) / cellX), 0, Nx-1);
        int ix1 = clampi((int)floor((s.bbx1 - xmin) / cellX), 0, Nx-1);
        int iy0 = clampi((int)floor((s.bby0 - ymin) / cellY), 0, Ny-1);
        int iy1 = clampi((int)floor((s.bby1 - ymin) / cellY), 0, Ny-1);
        for (int ix = ix0; ix <= ix1; ++ix) {
            size_t base = (size_t)ix;
            base += (size_t)Nx * (size_t)iy0;
            for (int iy = iy0; iy <= iy1; ++iy) {
                grid[base].push_back(i);
                base += (size_t)Nx;
                ++totalAssigned;
            }
        }
    }

    // Determine sampling count adaptively by approximate complexity
    double avgPerCell = (Nx > 0 && Ny > 0) ? (double)totalAssigned / (double)(Nx * Ny) : (double)segs.size();
    // Budget operations: ~8e7 distance checks
    double opsBudget = 8e7;
    long long Nsamples = (long long)max(10000.0, opsBudget / max(1.0, avgPerCell));
    // Clamp samples
    Nsamples = min<long long>(Nsamples, 4000000LL);
    Nsamples = max<long long>(Nsamples, 200000LL);

    // Stratified sampling over a grid close to sqrt(Nsamples)
    double aspect = width / height;
    long long Sx = (long long)floor(sqrt((double)Nsamples * aspect));
    Sx = max(1LL, min(3000LL, Sx));
    long long Sy = max(1LL, min(3000LL, (long long)(Nsamples / max(1LL, Sx))));
    Nsamples = Sx * Sy;

    FastRNG rng(0x123456789ABCDEFuLL ^ (uint64_t)(n * 10007 + m * 1009 + (unsigned)round(r * 1000000)));
    long long insideCnt = 0;

    // Sample one random point per stratum
    for (long long iy = 0; iy < Sy; ++iy) {
        double y0 = ymin + (double)iy * (height / Sy);
        double y1 = ymin + (double)(iy + 1) * (height / Sy);
        for (long long ix = 0; ix < Sx; ++ix) {
            double x0 = xmin + (double)ix * (width / Sx);
            double x1 = xmin + (double)(ix + 1) * (width / Sx);
            double rx = rng.nextDouble();
            double ry = rng.nextDouble();
            double px = x0 + rx * (x1 - x0);
            double py = y0 + ry * (y1 - y0);

            int cx = (int)floor((px - xmin) / cellX);
            int cy = (int)floor((py - ymin) / cellY);
            if (cx < 0) cx = 0; else if (cx >= Nx) cx = Nx - 1;
            if (cy < 0) cy = 0; else if (cy >= Ny) cy = Ny - 1;
            const vector<int>& lst = grid[(size_t)cx + (size_t)Nx * (size_t)cy];
            bool ok = false;
            for (int idx : lst) {
                const Segment& s = segs[idx];
                // quick reject by capsule bbox
                if (px < s.bbx0 || px > s.bbx1 || py < s.bby0 || py > s.bby1) continue;
                if (pointNearSegment(px, py, s, r2)) { ok = true; break; }
            }
            if (ok) ++insideCnt;
        }
    }

    double areaEst = areaBB * ((double)insideCnt / (double)Nsamples);
    cout.setf(std::ios::fixed);
    cout << setprecision(7) << areaEst << "\n";
    return 0;
}