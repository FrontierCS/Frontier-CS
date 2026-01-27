#include <bits/stdc++.h>
using namespace std;

struct Segment {
    double ax, ay, bx, by;
    double vx, vy, len2;
};

static const int MAX_DEPTH = 12;

int n;
vector<pair<double,double>> pts;
int m;
vector<Segment> segs;
double r, r2;

double xmin_b, ymin_b, xmax_b, ymax_b;

double cellSize;
double gx0, gy0;
int nx, ny;

struct KeyHash {
    size_t operator()(const long long &k) const noexcept { return std::hash<long long>()(k); }
};
unordered_map<long long, vector<int>, KeyHash> grid;

inline long long cellKey(int ix, int iy) {
    return ( (long long)ix << 32 ) ^ (unsigned long long)iy;
}

inline int clampi(int v, int lo, int hi) {
    if (v < lo) return lo;
    if (v > hi) return hi;
    return v;
}

void insert_segment_to_grid(int id, double minx, double miny, double maxx, double maxy) {
    int ix0 = clampi((int)floor((minx - gx0) / cellSize), 0, nx-1);
    int iy0 = clampi((int)floor((miny - gy0) / cellSize), 0, ny-1);
    int ix1 = clampi((int)floor((maxx - gx0) / cellSize), 0, nx-1);
    int iy1 = clampi((int)floor((maxy - gy0) / cellSize), 0, ny-1);
    for (int ix = ix0; ix <= ix1; ++ix) {
        for (int iy = iy0; iy <= iy1; ++iy) {
            grid[cellKey(ix,iy)].push_back(id);
        }
    }
}

inline bool point_in_union(double px, double py) {
    int ix = (int)floor((px - gx0) / cellSize);
    int iy = (int)floor((py - gy0) / cellSize);
    if (ix < 0 || iy < 0 || ix >= nx || iy >= ny) return false;
    auto it = grid.find(cellKey(ix,iy));
    if (it == grid.end()) return false;
    const auto &vec = it->second;
    for (int id : vec) {
        const Segment &s = segs[id];
        double dx = px - s.ax, dy = py - s.ay;
        double t = (dx*s.vx + dy*s.vy) / s.len2;
        if (t < 0.0) t = 0.0;
        else if (t > 1.0) t = 1.0;
        double cx = s.ax + t * s.vx;
        double cy = s.ay + t * s.vy;
        double ddx = px - cx, ddy = py - cy;
        if (ddx*ddx + ddy*ddy <= r2) return true;
    }
    return false;
}

bool rect_has_candidates(double x0, double y0, double x1, double y1) {
    int ix0 = clampi((int)floor((x0 - gx0) / cellSize), 0, nx-1);
    int iy0 = clampi((int)floor((y0 - gy0) / cellSize), 0, ny-1);
    int ix1 = clampi((int)floor((x1 - gx0) / cellSize), 0, nx-1);
    int iy1 = clampi((int)floor((y1 - gy0) / cellSize), 0, ny-1);
    for (int ix = ix0; ix <= ix1; ++ix) {
        for (int iy = iy0; iy <= iy1; ++iy) {
            auto it = grid.find(cellKey(ix,iy));
            if (it != grid.end() && !it->second.empty()) return true;
        }
    }
    return false;
}

double area_rect(double x0, double y0, double x1, double y1, int depth) {
    // Quick empty check
    if (!rect_has_candidates(x0, y0, x1, y1)) return 0.0;

    bool c00 = point_in_union(x0, y0);
    bool c10 = point_in_union(x1, y0);
    bool c01 = point_in_union(x0, y1);
    bool c11 = point_in_union(x1, y1);

    double area = (x1 - x0) * (y1 - y0);

    if (c00 && c10 && c01 && c11) {
        return area;
    }

    if (depth >= MAX_DEPTH) {
        // sample center and edge midpoints
        double cx = 0.5*(x0 + x1);
        double cy = 0.5*(y0 + y1);
        int inside = 0;
        inside += point_in_union(cx, cy);
        inside += point_in_union(0.5*(x0+x1), y0);
        inside += point_in_union(0.5*(x0+x1), y1);
        inside += point_in_union(x0, 0.5*(y0+y1));
        inside += point_in_union(x1, 0.5*(y0+y1));
        return area * (inside / 5.0);
    }

    double mx = 0.5*(x0 + x1);
    double my = 0.5*(y0 + y1);

    return area_rect(x0, y0, mx, my, depth+1)
         + area_rect(mx, y0, x1, my, depth+1)
         + area_rect(x0, my, mx, y1, depth+1)
         + area_rect(mx, my, x1, y1, depth+1);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N;
    if (!(cin >> N)) return 0;
    n = N;
    pts.resize(n);
    for (int i = 0; i < n; ++i) {
        cin >> pts[i].first >> pts[i].second;
    }
    cin >> m;
    segs.reserve(m);
    xmin_b = 1e100; ymin_b = 1e100; xmax_b = -1e100; ymax_b = -1e100;
    vector<pair<int,int>> edges;
    edges.reserve(m);
    for (int i = 0; i < m; ++i) {
        int a,b;
        cin >> a >> b;
        --a; --b;
        edges.emplace_back(a,b);
        const auto &pa = pts[a];
        const auto &pb = pts[b];
        xmin_b = min(xmin_b, min(pa.first, pb.first));
        ymin_b = min(ymin_b, min(pa.second, pb.second));
        xmax_b = max(xmax_b, max(pa.first, pb.first));
        ymax_b = max(ymax_b, max(pa.second, pb.second));
    }
    cin >> r;
    double p1, p2, p3, p4;
    cin >> p1 >> p2 >> p3 >> p4;
    if (m == 0) {
        cout.setf(std::ios::fixed); cout<<setprecision(7)<<0.0<<"\n";
        return 0;
    }
    r2 = r*r;

    // Build segments
    segs.resize(m);
    for (int i = 0; i < m; ++i) {
        int a = edges[i].first, b = edges[i].second;
        Segment s;
        s.ax = pts[a].first; s.ay = pts[a].second;
        s.bx = pts[b].first; s.by = pts[b].second;
        s.vx = s.bx - s.ax; s.vy = s.by - s.ay;
        s.len2 = s.vx*s.vx + s.vy*s.vy;
        if (s.len2 == 0.0) s.len2 = 1e-18;
        segs[i] = s;
    }

    // Expand bbox by r
    xmin_b -= r; ymin_b -= r; xmax_b += r; ymax_b += r;

    // Grid setup
    double spanx = xmax_b - xmin_b;
    double spany = ymax_b - ymin_b;
    double baseDiv = 200.0; // target ~200 divisions across span
    double suggested = max({r, spanx/baseDiv, spany/baseDiv, 1e-3});
    cellSize = suggested;
    gx0 = xmin_b; gy0 = ymin_b;
    nx = max(1, (int)ceil(spanx / cellSize));
    ny = max(1, (int)ceil(spany / cellSize));

    // Reserve map buckets (rough estimate)
    grid.reserve(min( (long long)nx * ny, (long long)m * 10LL + 1000LL ));

    // Insert segments into grid
    for (int i = 0; i < m; ++i) {
        const Segment &s = segs[i];
        double minx = min(s.ax, s.bx) - r;
        double maxx = max(s.ax, s.bx) + r;
        double miny = min(s.ay, s.by) - r;
        double maxy = max(s.ay, s.by) + r;
        insert_segment_to_grid(i, minx, miny, maxx, maxy);
    }

    double area = area_rect(xmin_b, ymin_b, xmax_b, ymax_b, 0);

    cout.setf(std::ios::fixed);
    cout << setprecision(7) << area << "\n";
    return 0;
}