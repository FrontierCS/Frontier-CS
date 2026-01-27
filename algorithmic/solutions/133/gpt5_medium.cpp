#include <bits/stdc++.h>
using namespace std;

struct Seg {
    double ax, ay, bx, by;
    double vx, vy;
    double len2;
    double minx, miny, maxx, maxy;
};

static inline uint64_t splitmix64(uint64_t& x) {
    uint64_t z = (x += 0x9e3779b97f4a7c15ULL);
    z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
    z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
    return z ^ (z >> 31);
}

struct FastRNG {
    uint64_t s;
    FastRNG() {
        uint64_t t = chrono::high_resolution_clock::now().time_since_epoch().count();
        s = splitmix64(t);
    }
    inline uint64_t next() {
        // xorshift64*
        uint64_t x = s;
        x ^= x >> 12;
        x ^= x << 25;
        x ^= x >> 27;
        s = x;
        return x * 2685821657736338717ULL;
    }
    inline double nextDouble() {
        // convert to [0,1)
        return (next() >> 11) * (1.0 / 9007199254740992.0);
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n;
    if (!(cin >> n)) {
        return 0;
    }
    vector<pair<double,double>> pts(n);
    for (int i = 0; i < n; ++i) cin >> pts[i].first >> pts[i].second;
    int m;
    cin >> m;
    vector<Seg> segs;
    segs.reserve(m);
    for (int i = 0; i < m; ++i) {
        int a,b;
        cin >> a >> b;
        --a; --b;
        Seg s;
        s.ax = pts[a].first;
        s.ay = pts[a].second;
        s.bx = pts[b].first;
        s.by = pts[b].second;
        s.vx = s.bx - s.ax;
        s.vy = s.by - s.ay;
        s.len2 = s.vx*s.vx + s.vy*s.vy;
        s.minx = min(s.ax, s.bx);
        s.maxx = max(s.ax, s.bx);
        s.miny = min(s.ay, s.by);
        s.maxy = max(s.ay, s.by);
        segs.push_back(s);
    }
    double r;
    cin >> r;
    double p1, p2, p3, p4;
    cin >> p1 >> p2 >> p3 >> p4; // read but unused

    if (m == 0) {
        cout.setf(std::ios::fixed); cout << setprecision(7) << 0.0 << "\n";
        return 0;
    }

    // Bounding box
    double xmin = 1e100, ymin = 1e100, xmax = -1e100, ymax = -1e100;
    for (int i = 0; i < n; ++i) {
        xmin = min(xmin, pts[i].first);
        xmax = max(xmax, pts[i].first);
        ymin = min(ymin, pts[i].second);
        ymax = max(ymax, pts[i].second);
    }
    xmin -= r; xmax += r; ymin -= r; ymax += r;

    double W = xmax - xmin;
    double H = ymax - ymin;
    if (W <= 0 || H <= 0) {
        cout.setf(std::ios::fixed); cout << setprecision(7) << 0.0 << "\n";
        return 0;
    }

    // Grid cell size selection
    double targetCells = 200000.0; // target total number of cells
    double s = sqrt((W * H) / targetCells);
    s = max(s, r); // ensure segments fit well; but cap total cells later
    int Nx = (int)ceil(W / s);
    int Ny = (int)ceil(H / s);
    // cap total cells
    const int maxCells = 800000;
    while ((int64_t)Nx * (int64_t)Ny > maxCells) {
        s *= 1.5;
        Nx = (int)ceil(W / s);
        Ny = (int)ceil(H / s);
    }
    Nx = max(1, Nx);
    Ny = max(1, Ny);
    double invS = 1.0 / s;

    // Build cell lists using two-pass method
    int64_t Ncells = (int64_t)Nx * (int64_t)Ny;
    vector<int> counts;
    counts.assign(Ncells, 0);

    auto clamp_ix = [&](double x)->int {
        int ix = (int)floor((x - xmin) * invS);
        if (ix < 0) ix = 0;
        if (ix >= Nx) ix = Nx - 1;
        return ix;
    };
    auto clamp_iy = [&](double y)->int {
        int iy = (int)floor((y - ymin) * invS);
        if (iy < 0) iy = 0;
        if (iy >= Ny) iy = Ny - 1;
        return iy;
    };

    for (int i = 0; i < m; ++i) {
        double exmin = segs[i].minx - r;
        double exmax = segs[i].maxx + r;
        double eymin = segs[i].miny - r;
        double eymax = segs[i].maxy + r;
        int ix0 = clamp_ix(exmin);
        int ix1 = clamp_ix(exmax);
        int iy0 = clamp_iy(eymin);
        int iy1 = clamp_iy(eymax);
        for (int iy = iy0; iy <= iy1; ++iy) {
            int base = iy * Nx;
            for (int ix = ix0; ix <= ix1; ++ix) {
                counts[base + ix]++;
            }
        }
    }

    vector<int> start(Ncells + 1, 0);
    for (int i = 0; i < Ncells; ++i) start[i+1] = start[i] + counts[i];
    vector<int> fill(Ncells, 0);
    vector<int> cellItems(start.back());
    for (int i = 0; i < m; ++i) {
        double exmin = segs[i].minx - r;
        double exmax = segs[i].maxx + r;
        double eymin = segs[i].miny - r;
        double eymax = segs[i].maxy + r;
        int ix0 = clamp_ix(exmin);
        int ix1 = clamp_ix(exmax);
        int iy0 = clamp_iy(eymin);
        int iy1 = clamp_iy(eymax);
        for (int iy = iy0; iy <= iy1; ++iy) {
            int base = iy * Nx;
            for (int ix = ix0; ix <= ix1; ++ix) {
                int cell = base + ix;
                int pos = start[cell] + fill[cell]++;
                cellItems[pos] = i;
            }
        }
    }

    double r2 = r * r;

    auto inside_capsule = [&](double px, double py, const Seg& s) -> bool {
        double ux = s.vx, uy = s.vy;
        double len2 = s.len2;
        if (len2 == 0.0) {
            double dx = px - s.ax, dy = py - s.ay;
            return dx*dx + dy*dy <= r2;
        } else {
            double t = ((px - s.ax)*ux + (py - s.ay)*uy) / len2;
            if (t <= 0.0) {
                double dx = px - s.ax, dy = py - s.ay;
                return dx*dx + dy*dy <= r2;
            } else if (t >= 1.0) {
                double dx = px - s.bx, dy = py - s.by;
                return dx*dx + dy*dy <= r2;
            } else {
                double projx = s.ax + t*ux;
                double projy = s.ay + t*uy;
                double dx = px - projx, dy = py - projy;
                return dx*dx + dy*dy <= r2;
            }
        }
    };

    // Monte Carlo sampling with time budget
    FastRNG rng;
    const double Area = W * H;
    uint64_t N = 0, K = 0;

    auto t0 = chrono::high_resolution_clock::now();
    double timeBudgetSec = 2.2; // sampling time budget
    const int batch = 200000; // samples per batch

    while (true) {
        for (int it = 0; it < batch; ++it) {
            double rx = rng.nextDouble();
            double ry = rng.nextDouble();
            double x = xmin + rx * W;
            double y = ymin + ry * H;
            int ix = (int)((x - xmin) * invS);
            int iy = (int)((y - ymin) * invS);
            if (ix < 0) ix = 0; else if (ix >= Nx) ix = Nx - 1;
            if (iy < 0) iy = 0; else if (iy >= Ny) iy = Ny - 1;
            int cell = iy * Nx + ix;
            bool inside = false;
            int st = start[cell], en = start[cell + 1];
            for (int p = st; p < en; ++p) {
                const Seg& sref = segs[cellItems[p]];
                if (inside_capsule(x, y, sref)) {
                    inside = true;
                    break;
                }
            }
            if (inside) ++K;
            ++N;
        }
        auto t1 = chrono::high_resolution_clock::now();
        double elapsed = chrono::duration<double>(t1 - t0).count();
        if (elapsed >= timeBudgetSec) break;

        // Optional convergence check using std dev of Monte Carlo
        // p*(1-p) <= 0.25
        double p_est = (double)K / (double)N;
        double sd = Area * sqrt(max(1e-18, p_est * (1.0 - p_est) / (double)N));
        // If estimated absolute error is already small, stop early
        if (sd < 1e-3) break; // about 0.001 area units
    }

    double area_est = (double)K / (double)N * Area;
    cout.setf(std::ios::fixed);
    cout << setprecision(7) << area_est << "\n";
    return 0;
}