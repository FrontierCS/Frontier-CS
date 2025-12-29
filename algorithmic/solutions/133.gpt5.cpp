#include <bits/stdc++.h>
using namespace std;

struct FastScanner {
    static const int BUFSIZE = 1 << 20;
    int idx, size;
    char buf[BUFSIZE];
    FastScanner(): idx(0), size(0) {}
    inline char getChar() {
        if (idx >= size) {
            size = (int)fread(buf, 1, BUFSIZE, stdin);
            idx = 0;
            if (size == 0) return 0;
        }
        return buf[idx++];
    }
    template<typename T>
    bool readInt(T &out) {
        char c; T sign = 1; T val = 0;
        c = getChar(); if (!c) return false;
        while (c <= ' ') { c = getChar(); if (!c) return false; }
        if (c == '-') { sign = -1; c = getChar(); }
        for (; c >= '0' && c <= '9'; c = getChar()) val = val * 10 + (c - '0');
        out = val * sign;
        return true;
    }
    bool readDouble(double &out) {
        char c = getChar(); if (!c) return false;
        while (c <= ' ') { c = getChar(); if (!c) return false; }
        double sign = 1.0;
        if (c == '-') { sign = -1.0; c = getChar(); }
        double val = 0.0;
        while (c >= '0' && c <= '9') {
            val = val * 10.0 + (c - '0');
            c = getChar();
        }
        if (c == '.') {
            double mul = 1.0;
            c = getChar();
            while (c >= '0' && c <= '9') {
                mul *= 0.1;
                val += (c - '0') * mul;
                c = getChar();
            }
        }
        if (c == 'e' || c == 'E') {
            int esign = 1, e = 0;
            c = getChar();
            if (c == '-') { esign = -1; c = getChar(); }
            else if (c == '+') { c = getChar(); }
            while (c >= '0' && c <= '9') {
                e = e * 10 + (c - '0');
                c = getChar();
            }
            double pow10 = pow(10.0, esign * e);
            val *= pow10;
        }
        out = val * sign;
        return true;
    }
};

struct Seg {
    float ax, ay, bx, by;
    float dx, dy;
    float len2;
};

struct MinHeap {
    vector<double> key;
    vector<int> val;
    inline void clear() { key.clear(); val.clear(); }
    inline bool empty() const { return key.empty(); }
    inline void push(double k, int v) {
        key.push_back(k);
        val.push_back(v);
        int i = (int)key.size() - 1;
        while (i > 0) {
            int p = (i - 1) >> 1;
            if (key[p] <= key[i]) break;
            swap(key[p], key[i]);
            swap(val[p], val[i]);
            i = p;
        }
    }
    inline void pop() {
        int n = (int)key.size();
        if (n == 0) return;
        key[0] = key[n - 1];
        val[0] = val[n - 1];
        key.pop_back();
        val.pop_back();
        n--;
        int i = 0;
        while (true) {
            int l = i * 2 + 1;
            if (l >= n) break;
            int r = l + 1;
            int m = (r < n && key[r] < key[l]) ? r : l;
            if (key[i] <= key[m]) break;
            swap(key[i], key[m]);
            swap(val[i], val[m]);
            i = m;
        }
    }
    inline pair<double,int> top() const { return {key[0], val[0]}; }
};

static inline double dist2_point_to_segment(const Seg &s, double x, double y) {
    double ax = s.ax, ay = s.ay, bx = s.bx, by = s.by;
    double dx = s.dx, dy = s.dy;
    double len2 = s.len2;
    if (len2 <= 1e-24) {
        double ux = x - ax, uy = y - ay;
        return ux*ux + uy*uy;
    }
    double ux = x - ax, uy = y - ay;
    double t = (ux * dx + uy * dy) / len2;
    if (t < 0.0) t = 0.0;
    else if (t > 1.0) t = 1.0;
    double px = ax + t * dx;
    double py = ay + t * dy;
    double vx = x - px, vy = y - py;
    return vx*vx + vy*vy;
}

struct GridIndex {
    double x0, y0, cellSize;
    int nx, ny;
    vector<int> offsets;
    vector<int> entries;
    vector<int> writePtr;
    vector<int> tempCounts;
    vector<int> stamp; // visited stamps per cell
    int currentStamp;

    GridIndex(): x0(0), y0(0), cellSize(5.0), nx(0), ny(0), currentStamp(1) {}

    inline int idx(int ix, int iy) const {
        return iy * nx + ix;
    }
    inline bool inRange(int ix, int iy) const {
        return ix >= 0 && ix < nx && iy >= 0 && iy < ny;
    }
    inline pair<int,int> cellOf(double x, double y) const {
        int ix = (int)floor((x - x0) / cellSize);
        int iy = (int)floor((y - y0) / cellSize);
        if (ix < 0) ix = 0; else if (ix >= nx) ix = nx - 1;
        if (iy < 0) iy = 0; else if (iy >= ny) iy = ny - 1;
        return {ix, iy};
    }
    inline double cellMinDist2(double px, double py, int ix, int iy) const {
        double x1 = x0 + ix * cellSize;
        double y1 = y0 + iy * cellSize;
        double x2 = x1 + cellSize;
        double y2 = y1 + cellSize;
        double dx = 0.0;
        if (px < x1) dx = x1 - px;
        else if (px > x2) dx = px - x2;
        double dy = 0.0;
        if (py < y1) dy = y1 - py;
        else if (py > y2) dy = py - y2;
        return dx*dx + dy*dy;
    }
    void init(double minx, double miny, double maxx, double maxy, double csize) {
        x0 = minx;
        y0 = miny;
        cellSize = csize;
        nx = max(1, (int)ceil((maxx - minx) / cellSize));
        ny = max(1, (int)ceil((maxy - miny) / cellSize));
        int cells = nx * ny;
        tempCounts.assign(cells, 0);
        offsets.assign(cells + 1, 0);
        writePtr.assign(cells, 0);
        stamp.assign(cells, 0);
        currentStamp = 1;
    }
    inline void incrementStamp() {
        currentStamp++;
        if (currentStamp == INT_MAX) {
            currentStamp = 1;
            fill(stamp.begin(), stamp.end(), 0);
        }
    }
    // Enumerate grid cells intersected by a segment using Amanatides & Woo algorithm
    template <typename F>
    void visitSegmentCells(double ax, double ay, double bx, double by, F func) {
        // Clamp to grid
        int ix0 = (int)floor((ax - x0) / cellSize);
        int iy0 = (int)floor((ay - y0) / cellSize);
        int ix1 = (int)floor((bx - x0) / cellSize);
        int iy1 = (int)floor((by - y0) / cellSize);
        if (ix0 < 0) ix0 = 0; else if (ix0 >= nx) ix0 = nx - 1;
        if (iy0 < 0) iy0 = 0; else if (iy0 >= ny) iy0 = ny - 1;
        if (ix1 < 0) ix1 = 0; else if (ix1 >= nx) ix1 = nx - 1;
        if (iy1 < 0) iy1 = 0; else if (iy1 >= ny) iy1 = ny - 1;

        int ix = ix0, iy = iy0;
        int stepx = 0, stepy = 0;
        double dx = bx - ax, dy = by - ay;
        if (dx > 0) stepx = 1; else if (dx < 0) stepx = -1; else stepx = 0;
        if (dy > 0) stepy = 1; else if (dy < 0) stepy = -1; else stepy = 0;

        double tMaxX, tMaxY, tDeltaX, tDeltaY;
        const double INF = 1e100;

        if (stepx != 0) {
            double nextX = x0 + (ix + (stepx > 0 ? 1 : 0)) * cellSize;
            tMaxX = (nextX - ax) / (dx == 0.0 ? 1e-300 : dx);
            tDeltaX = (double)cellSize / fabs(dx == 0.0 ? 1e-300 : dx);
        } else {
            tMaxX = INF; tDeltaX = INF;
        }
        if (stepy != 0) {
            double nextY = y0 + (iy + (stepy > 0 ? 1 : 0)) * cellSize;
            tMaxY = (nextY - ay) / (dy == 0.0 ? 1e-300 : dy);
            tDeltaY = (double)cellSize / fabs(dy == 0.0 ? 1e-300 : dy);
        } else {
            tMaxY = INF; tDeltaY = INF;
        }

        func(ix, iy);
        while (ix != ix1 || iy != iy1) {
            if (tMaxX <= tMaxY) {
                ix += stepx;
                tMaxX += tDeltaX;
                if (ix < 0) ix = 0;
                if (ix >= nx) ix = nx - 1;
            } else {
                iy += stepy;
                tMaxY += tDeltaY;
                if (iy < 0) iy = 0;
                if (iy >= ny) iy = ny - 1;
            }
            func(ix, iy);
        }
    }
    void countSegment(double ax, double ay, double bx, double by) {
        visitSegmentCells(ax, ay, bx, by, [&](int ix, int iy){
            int id = idx(ix, iy);
            tempCounts[id]++;
        });
    }
    void addSegment(int segId, double ax, double ay, double bx, double by) {
        visitSegmentCells(ax, ay, bx, by, [&](int ix, int iy){
            int id = idx(ix, iy);
            int pos = offsets[id] + writePtr[id]++;
            entries[pos] = segId;
        });
    }
};

struct Context {
    vector<Seg> segs;
    GridIndex grid;
    double r;
    double xmin, ymin, xmax, ymax;
};

static inline double minDistToSegments(Context &ctx, double x, double y) {
    // Priority queue over cells by lower bound distance from (x,y) to cell rectangle
    int nx = ctx.grid.nx, ny = ctx.grid.ny;
    auto cellOf = ctx.grid.cellOf(x, y);
    int ci = cellOf.first;
    int cj = cellOf.second;
    int startIdx = ctx.grid.idx(ci, cj);
    ctx.grid.incrementStamp();
    int currentStamp = ctx.grid.currentStamp;
    MinHeap heap;
    heap.push(0.0, startIdx);
    double best2 = numeric_limits<double>::infinity();
    // To reduce overhead, process the start cell directly (avoid PQ overhead)
    // but we already pushed it; keep general.

    while (!heap.empty()) {
        auto cur = heap.top();
        double d2 = cur.first;
        int id = cur.second;
        heap.pop();
        if (ctx.grid.stamp[id] == currentStamp) continue;
        ctx.grid.stamp[id] = currentStamp;
        if (d2 >= best2) break; // no need to explore further
        // process segments in this cell
        int begin = ctx.grid.offsets[id];
        int end = ctx.grid.offsets[id + 1];
        for (int p = begin; p < end; ++p) {
            int sid = ctx.grid.entries[p];
            const Seg &s = ctx.segs[sid];
            double d2s = dist2_point_to_segment(s, x, y);
            if (d2s < best2) best2 = d2s;
        }
        // expand neighbors
        int ix = id % nx;
        int iy = id / nx;
        for (int dj = -1; dj <= 1; ++dj) {
            int nyy = iy + dj;
            if (nyy < 0 || nyy >= ny) continue;
            for (int di = -1; di <= 1; ++di) {
                int nxx = ix + di;
                if (nxx < 0 || nxx >= nx) continue;
                int nid = ctx.grid.idx(nxx, nyy);
                if (ctx.grid.stamp[nid] == currentStamp) continue;
                double nd2 = ctx.grid.cellMinDist2(x, y, nxx, nyy);
                if (nd2 < best2) {
                    heap.push(nd2, nid);
                }
            }
        }
    }
    return sqrt(best2);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    FastScanner fs;
    int n;
    if (!fs.readInt(n)) {
        return 0;
    }
    vector<double> px(n), py(n);
    for (int i = 0; i < n; ++i) {
        double x, y;
        fs.readDouble(x);
        fs.readDouble(y);
        px[i] = x; py[i] = y;
    }
    int m;
    fs.readInt(m);
    vector<pair<int,int>> edges;
    edges.reserve(m);
    for (int i = 0; i < m; ++i) {
        int a, b;
        fs.readInt(a);
        fs.readInt(b);
        --a; --b;
        edges.emplace_back(a, b);
    }
    double r;
    fs.readDouble(r);
    double p1, p2, p3, p4;
    fs.readDouble(p1);
    fs.readDouble(p2);
    fs.readDouble(p3);
    fs.readDouble(p4);
    if (m == 0) {
        cout.setf(std::ios::fixed); cout<<setprecision(7)<<0.0<<"\n";
        return 0;
    }
    Context ctx;
    ctx.r = r;
    ctx.segs.resize(m);
    double xmin = 1e100, ymin = 1e100, xmax = -1e100, ymax = -1e100;
    for (int i = 0; i < m; ++i) {
        int a = edges[i].first;
        int b = edges[i].second;
        double ax = px[a], ay = py[a];
        double bx = px[b], by = py[b];
        xmin = min(xmin, min(ax, bx));
        ymin = min(ymin, min(ay, by));
        xmax = max(xmax, max(ax, bx));
        ymax = max(ymax, max(ay, by));
        Seg s;
        s.ax = (float)ax; s.ay = (float)ay; s.bx = (float)bx; s.by = (float)by;
        s.dx = (float)(bx - ax); s.dy = (float)(by - ay);
        s.len2 = (float)((bx - ax) * (bx - ax) + (by - ay) * (by - ay));
        ctx.segs[i] = s;
    }
    // Expand bounding box by r
    xmin -= r; ymin -= r; xmax += r; ymax += r;
    // Slight expansion to avoid boundary issues
    double epsBound = 1e-8;
    xmin -= epsBound; ymin -= epsBound; xmax += epsBound; ymax += epsBound;

    // Choose grid cell size
    double W = xmax - xmin, H = ymax - ymin;
    // Heuristic for grid size based on area/segments
    double avgLen = 0.0;
    int sampleCount = min(m, 20000);
    if (sampleCount > 0) {
        for (int i = 0; i < sampleCount; ++i) {
            const Seg &s = ctx.segs[i];
            avgLen += sqrt((double)s.len2);
        }
        avgLen /= sampleCount;
    } else avgLen = 1.0;
    double cellSize = max( (W + H) / 100.0, 2.5 ); // heuristic base
    // Adjust based on avgLen and number of segments to control memory
    if (m > 500000) cellSize = max(cellSize, 5.0);
    if (m > 1500000) cellSize = max(cellSize, 7.5);
    if (m > 2500000) cellSize = max(cellSize, 10.0);
    cellSize = min(cellSize, max(W, H)); // avoid too many cells
    if (cellSize <= 0) cellSize = 5.0;

    ctx.grid.init(xmin, ymin, xmax, ymax, cellSize);

    // First pass: count entries per cell using grid traversal along segments (Amanatides & Woo)
    for (int i = 0; i < m; ++i) {
        const Seg &s = ctx.segs[i];
        ctx.grid.countSegment(s.ax, s.ay, s.bx, s.by);
    }

    // Build offsets
    int cells = ctx.grid.nx * ctx.grid.ny;
    long long totalEntries = 0;
    for (int i = 0; i < cells; ++i) {
        ctx.grid.offsets[i + 1] = ctx.grid.offsets[i] + ctx.grid.tempCounts[i];
    }
    totalEntries = ctx.grid.offsets[cells];
    ctx.grid.entries.assign(totalEntries, 0);
    // Reset write pointers
    fill(ctx.grid.writePtr.begin(), ctx.grid.writePtr.end(), 0);

    // Second pass: fill entries
    for (int i = 0; i < m; ++i) {
        const Seg &s = ctx.segs[i];
        ctx.grid.addSegment(i, s.ax, s.ay, s.bx, s.by);
    }

    // Adaptive quadtree integration
    struct Node { double x1, y1, x2, y2; int depth; };
    vector<Node> stack;
    stack.reserve(1 << 20);
    stack.push_back({xmin, ymin, xmax, ymax, 0});
    double totalArea = 0.0;

    // Heuristic leaf size
    double leafMinSize = max(0.02, ctx.r * 0.05);
    leafMinSize = min(leafMinSize, 0.5);
    int maxDepth = 22;

    while (!stack.empty()) {
        Node node = stack.back();
        stack.pop_back();
        double x1 = node.x1, y1 = node.y1, x2 = node.x2, y2 = node.y2;
        double cx = 0.5 * (x1 + x2);
        double cy = 0.5 * (y1 + y2);
        double w = x2 - x1, h = y2 - y1;
        double halfDiag = 0.5 * hypot(w, h);
        double d = minDistToSegments(ctx, cx, cy) - ctx.r;
        if (d >= halfDiag) {
            // fully outside
            continue;
        } else if (d <= -halfDiag) {
            // fully inside
            totalArea += w * h;
            continue;
        } else {
            if (node.depth >= maxDepth || (w <= leafMinSize && h <= leafMinSize)) {
                // approximate by sampling 5 points: center and four corners
                double points[5][2] = {
                    {cx, cy},
                    {x1, y1},
                    {x1, y2},
                    {x2, y1},
                    {x2, y2}
                };
                int inside = 0;
                for (int k = 0; k < 5; ++k) {
                    double dd = minDistToSegments(ctx, points[k][0], points[k][1]);
                    if (dd <= ctx.r) inside++;
                }
                totalArea += (w * h) * (inside / 5.0);
                continue;
            } else {
                // subdivide into 4
                double mx = 0.5 * (x1 + x2);
                double my = 0.5 * (y1 + y2);
                int nd = node.depth + 1;
                stack.push_back({x1, y1, mx, my, nd});
                stack.push_back({mx, y1, x2, my, nd});
                stack.push_back({x1, my, mx, y2, nd});
                stack.push_back({mx, my, x2, y2, nd});
            }
        }
    }

    cout.setf(std::ios::fixed);
    cout << setprecision(7) << totalArea << "\n";
    return 0;
}