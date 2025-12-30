#include <bits/stdc++.h>
using namespace std;

struct FastRand {
    uint64_t xstate;
    FastRand(uint64_t seed = 88172645463393265ull) : xstate(seed) {}
    inline uint64_t next() {
        xstate ^= xstate << 7;
        xstate ^= xstate >> 9;
        return xstate;
    }
    inline double nextDouble() {
        // Uniform in [0,1)
        return (next() >> 11) * (1.0 / 9007199254740992.0);
    }
    inline uint64_t nextBound(uint64_t bound) { // [0, bound)
        // 128-bit multiply and shift for unbiased range
        __uint128_t r = (__uint128_t)next() * (__uint128_t)bound;
        return (uint64_t)(r >> 64);
    }
};

static inline double dist2_point_segment(double px, double py, double x1, double y1, double x2, double y2) {
    double vx = x2 - x1, vy = y2 - y1;
    double wx = px - x1, wy = py - y1;
    double vv = vx * vx + vy * vy;
    if (vv == 0.0) {
        double dx = px - x1, dy = py - y1;
        return dx * dx + dy * dy;
    }
    double t = (wx * vx + wy * vy) / vv;
    if (t < 0.0) t = 0.0;
    else if (t > 1.0) t = 1.0;
    double dx = (x1 + t * vx) - px;
    double dy = (y1 + t * vy) - py;
    return dx * dx + dy * dy;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if (!(cin >> n)) {
        return 0;
    }
    vector<double> px(n), py(n);
    for (int i = 0; i < n; i++) cin >> px[i] >> py[i];
    int m;
    cin >> m;
    vector<int> U(m), V(m);
    for (int i = 0; i < m; i++) {
        int a, b;
        cin >> a >> b;
        --a; --b;
        U[i] = a; V[i] = b;
    }
    double r;
    cin >> r;
    double p1, p2, p3, p4;
    cin >> p1 >> p2 >> p3 >> p4;
    
    if (m == 0) {
        cout.setf(std::ios::fixed); cout<<setprecision(7)<<0.0<<"\n";
        return 0;
    }
    
    // Compute bounding box expanded by r
    double minx = 1e100, miny = 1e100, maxx = -1e100, maxy = -1e100;
    for (int i = 0; i < n; i++) {
        minx = min(minx, px[i]);
        maxx = max(maxx, px[i]);
        miny = min(miny, py[i]);
        maxy = max(maxy, py[i]);
    }
    minx -= r; maxx += r; miny -= r; maxy += r;
    if (minx == maxx) { minx -= 1.0; maxx += 1.0; }
    if (miny == maxy) { miny -= 1.0; maxy += 1.0; }
    
    double rangeX = maxx - minx;
    double rangeY = maxy - miny;
    double areaBB = rangeX * rangeY;
    
    // Choose target number of grid cells based on m
    int targetCells;
    if (m <= 100000) targetCells = 160000;
    else if (m <= 300000) targetCells = 110000;
    else if (m <= 600000) targetCells = 80000;
    else if (m <= 1000000) targetCells = 60000;
    else if (m <= 2000000) targetCells = 40000;
    else targetCells = 25000;
    
    // Derive grid resolution. Use possibly different cell sizes in X/Y
    double baseS = sqrt(max(areaBB, 1e-12) / targetCells);
    int Nx = max(1, (int)ceil(rangeX / baseS));
    int Ny = max(1, (int)ceil(rangeY / baseS));
    // recompute cell size to fit exactly
    double sX = rangeX / Nx;
    double sY = rangeY / Ny;
    int Ncells = Nx * Ny;
    
    // Neighbor expansion to cover radius r
    int wX = max(1, (int)ceil(r / sX));
    int wY = max(1, (int)ceil(r / sY));
    // Slight safety margin
    wX = max(wX, 1);
    wY = max(wY, 1);
    
    auto cellIndex = [Ny](int ix, int iy) -> int { return ix * Ny + iy; };
    auto clampi = [](int v, int lo, int hi)->int { if (v < lo) return lo; if (v > hi) return hi; return v; };
    auto toCellX = [minx, sX, Nx](double x)->int {
        int ix = (int)floor((x - minx) / sX);
        if (ix < 0) ix = 0;
        if (ix >= Nx) ix = Nx - 1;
        return ix;
    };
    auto toCellY = [miny, sY, Ny](double y)->int {
        int iy = (int)floor((y - miny) / sY);
        if (iy < 0) iy = 0;
        if (iy >= Ny) iy = Ny - 1;
        return iy;
    };
    
    vector<int> head(Ncells, -1);
    vector<int> next;
    vector<int> segid;
    next.reserve((size_t)min<int64_t>( (int64_t)m * 8, (int64_t)1e8 ));
    segid.reserve((size_t)min<int64_t>( (int64_t)m * 8, (int64_t)1e8 ));
    vector<int> cellMark(Ncells, 0);
    
    auto addCell = [&](int cx, int cy, int id){
        if ((unsigned)cx < (unsigned)Nx && (unsigned)cy < (unsigned)Ny) {
            int idx = cellIndex(cx, cy);
            if (cellMark[idx] != id + 1) {
                cellMark[idx] = id + 1;
                segid.push_back(id);
                next.push_back(head[idx]);
                head[idx] = (int)segid.size() - 1;
            }
        }
    };
    
    // Grid traversal per segment with neighborhood expansion
    for (int id = 0; id < m; id++) {
        int a = U[id], b = V[id];
        double x0 = px[a], y0 = py[a];
        double x1 = px[b], y1 = py[b];
        // Handle degenerate segment
        if (x0 == x1 && y0 == y1) {
            int ix = toCellX(x0), iy = toCellY(y0);
            for (int dx = -wX; dx <= wX; ++dx)
                for (int dy = -wY; dy <= wY; ++dy)
                    addCell(ix + dx, iy + dy, id);
            continue;
        }
        int ix = toCellX(x0), iy = toCellY(y0);
        int ixEnd = toCellX(x1), iyEnd = toCellY(y1);
        
        double dx = x1 - x0, dy = y1 - y0;
        int stepX = (dx > 0) ? 1 : (dx < 0 ? -1 : 0);
        int stepY = (dy > 0) ? 1 : (dy < 0 ? -1 : 0);
        double tMaxX, tMaxY, tDeltaX, tDeltaY;
        if (stepX != 0) {
            double nextBoundaryX = minx + (ix + (stepX > 0 ? 1 : 0)) * sX;
            tMaxX = (nextBoundaryX - x0) / dx;
            tDeltaX = sX / fabs(dx);
        } else {
            tMaxX = 1e100;
            tDeltaX = 1e100;
        }
        if (stepY != 0) {
            double nextBoundaryY = miny + (iy + (stepY > 0 ? 1 : 0)) * sY;
            tMaxY = (nextBoundaryY - y0) / dy;
            tDeltaY = sY / fabs(dy);
        } else {
            tMaxY = 1e100;
            tDeltaY = 1e100;
        }
        auto addNeighborhood = [&](int cx, int cy){
            for (int dx2 = -wX; dx2 <= wX; ++dx2) {
                int tx = cx + dx2;
                if ((unsigned)tx >= (unsigned)Nx) continue;
                for (int dy2 = -wY; dy2 <= wY; ++dy2) {
                    int ty = cy + dy2;
                    if ((unsigned)ty >= (unsigned)Ny) continue;
                    addCell(tx, ty, id);
                }
            }
        };
        addNeighborhood(ix, iy);
        // Traverse cells intersected by the segment
        double t = 0.0;
        int safeIter = Nx + Ny + 4 + (int)(fabs((x1 - x0)/sX) + fabs((y1 - y0)/sY)) + 10;
        for (int it = 0; it < safeIter && (ix != ixEnd || iy != iyEnd); ++it) {
            if (tMaxX < tMaxY) {
                ix += stepX;
                t = tMaxX;
                tMaxX += tDeltaX;
            } else {
                iy += stepY;
                t = tMaxY;
                tMaxY += tDeltaY;
            }
            if ((unsigned)ix >= (unsigned)Nx || (unsigned)iy >= (unsigned)Ny) continue;
            addNeighborhood(ix, iy);
            if (t > 1.0 + 1e-12) break;
        }
        // ensure end cell neighborhood
        addNeighborhood(ixEnd, iyEnd);
    }
    
    // Build list of active cells and their exact area
    vector<int> active;
    active.reserve(Ncells / 4 + 1);
    for (int i = 0; i < Ncells; i++) {
        if (head[i] != -1) active.push_back(i);
    }
    if (active.empty()) {
        cout.setf(std::ios::fixed); cout<<setprecision(7)<<0.0<<"\n";
        return 0;
    }
    // Precompute area for each cell (handle last row/col cells may be smaller)
    vector<double> cellArea(active.size());
    double totalActiveArea = 0.0;
    for (size_t k = 0; k < active.size(); ++k) {
        int idx = active[k];
        int ix = idx / Ny;
        int iy = idx % Ny;
        double xL = minx + ix * sX;
        double xR = (ix + 1 == Nx) ? maxx : (xL + sX);
        double yB = miny + iy * sY;
        double yT = (iy + 1 == Ny) ? maxy : (yB + sY);
        double A = max(0.0, xR - xL) * max(0.0, yT - yB);
        cellArea[k] = A;
        totalActiveArea += A;
    }
    // Prefix sums for weighted sampling
    vector<double> prefix(active.size());
    double acc = 0.0;
    for (size_t k = 0; k < active.size(); ++k) {
        acc += cellArea[k];
        prefix[k] = acc;
    }
    if (acc <= 0) {
        cout.setf(std::ios::fixed); cout<<setprecision(7)<<0.0<<"\n";
        return 0;
    }
    
    // Estimate average list size per cell for sampling budget
    long long totalEdges = (long long)segid.size();
    double avgList = (double)totalEdges / (double)active.size();
    
    // Determine number of samples based on budget and difficulty
    // Budget of segment checks around 2e7
    double budgetChecks = 2.0e7;
    int maxSamples = 1500000;
    int minSamples = 20000;
    int samples = (int)(budgetChecks / max(1.0, avgList));
    samples = min(samples, maxSamples);
    samples = max(samples, minSamples);
    // Also scale with p1, p3 mildly (more samples if these suggest higher accuracy)
    double accFactor = 1.0 + 0.5 * (tanh(p1) + tanh(p3));
    samples = (int)min<double>(maxSamples, samples * accFactor);
    
    // If m is very small, boost samples a bit
    if (m <= 5000) samples = min(maxSamples, max(samples, 300000));
    // Lower bound by number of active cells to avoid too poor sampling
    samples = max(samples, (int)active.size());
    
    // Sampling
    FastRand rng(0x9e3779b97f4a7c15ull ^ ((uint64_t)n<<32) ^ (uint64_t)m ^ 0xD1B54A32D192ED03ull);
    vector<int> seen(m, -1);
    int64_t hits = 0;
    double rr2 = r * r;
    
    for (int it = 0; it < samples; ++it) {
        // Weighted random choose an active cell by area
        double u = rng.nextDouble() * acc;
        size_t k = (size_t)(lower_bound(prefix.begin(), prefix.end(), u) - prefix.begin());
        if (k >= active.size()) k = active.size() - 1;
        int idx = active[k];
        int ix = idx / Ny;
        int iy = idx % Ny;
        double xL = minx + ix * sX;
        double xR = (ix + 1 == Nx) ? maxx : (xL + sX);
        double yB = miny + iy * sY;
        double yT = (iy + 1 == Ny) ? maxy : (yB + sY);
        double rx = xL + (xR - xL) * rng.nextDouble();
        double ry = yB + (yT - yB) * rng.nextDouble();
        
        bool inside = false;
        for (int e = head[idx]; e != -1; e = next[e]) {
            int sid_ = segid[e];
            if (seen[sid_] == it) continue; // already checked this segment for this sample
            seen[sid_] = it;
            int a = U[sid_], b = V[sid_];
            double d2 = dist2_point_segment(rx, ry, px[a], py[a], px[b], py[b]);
            if (d2 <= rr2) { inside = true; break; }
        }
        if (inside) hits++;
    }
    
    double areaEst = (double)hits / (double)samples * totalActiveArea;
    cout.setf(std::ios::fixed);
    cout << setprecision(7) << areaEst << "\n";
    return 0;
}