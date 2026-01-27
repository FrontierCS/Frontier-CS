#include <bits/stdc++.h>
using namespace std;

struct Segment {
    double x1, y1, x2, y2;
};

static inline double dist2_point_to_segment(double px, double py, const Segment& s) {
    double x1 = s.x1, y1 = s.y1, x2 = s.x2, y2 = s.y2;
    double vx = x2 - x1, vy = y2 - y1;
    double wx = px - x1, wy = py - y1;
    double vv = vx*vx + vy*vy;
    double t = 0.0;
    if (vv > 0) t = (wx*vx + wy*vy) / vv;
    if (t < 0.0) { t = 0.0; }
    else if (t > 1.0) { t = 1.0; }
    double dx = (x1 + t*vx) - px;
    double dy = (y1 + t*vy) - py;
    return dx*dx + dy*dy;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n;
    if (!(cin >> n)) return 0;
    vector<pair<double,double>> pts(n);
    for (int i = 0; i < n; ++i) cin >> pts[i].first >> pts[i].second;
    int m;
    cin >> m;
    vector<Segment> segs;
    segs.reserve(m);
    for (int i = 0; i < m; ++i) {
        int a, b;
        cin >> a >> b;
        --a; --b;
        Segment s;
        s.x1 = pts[a].first; s.y1 = pts[a].second;
        s.x2 = pts[b].first; s.y2 = pts[b].second;
        segs.push_back(s);
    }
    double r; cin >> r;
    double p1, p2, p3, p4; cin >> p1 >> p2 >> p3 >> p4; // read but ignore p2,p4

    if (m == 0) {
        cout.setf(std::ios::fixed); cout<<setprecision(7)<<0.0<<"\n";
        return 0;
    }

    // Bounding box
    double minx = 1e100, miny = 1e100, maxx = -1e100, maxy = -1e100;
    for (int i = 0; i < n; ++i) {
        minx = min(minx, pts[i].first);
        miny = min(miny, pts[i].second);
        maxx = max(maxx, pts[i].first);
        maxy = max(maxy, pts[i].second);
    }
    double pad = r + 1e-9;
    minx -= pad; miny -= pad; maxx += pad; maxy += pad;
    double width = max(1e-9, maxx - minx);
    double height = max(1e-9, maxy - miny);
    double area_box = width * height;

    // Determine fine grid resolution
    const double target_cells_cap = 6e6; // cap number of fine cells
    double h = max(r / 3.0, 1e-3); // fine cell size
    double needed_cells = (width * height) / (h * h);
    if (needed_cells > target_cells_cap) {
        h = sqrt((width * height) / target_cells_cap);
    }
    int W = (int)ceil(width / h);
    int H = (int)ceil(height / h);
    // coarse grid for indexing segments
    double scell = max(r, h * 16.0);
    int CW = max(1, (int)ceil(width / scell));
    int CH = max(1, (int)ceil(height / scell));

    // Build coarse grid
    vector<vector<int>> coarse(CW * CH);
    auto coarse_idx = [&](double x, double y)->pair<int,int>{
        int cx = (int)floor((x - minx) / scell);
        int cy = (int)floor((y - miny) / scell);
        if (cx < 0) cx = 0; if (cx >= CW) cx = CW-1;
        if (cy < 0) cy = 0; if (cy >= CH) cy = CH-1;
        return {cx, cy};
    };
    for (int i = 0; i < m; ++i) {
        const auto& s = segs[i];
        double sxmin = min(s.x1, s.x2) - r, sxmax = max(s.x1, s.x2) + r;
        double symin = min(s.y1, s.y2) - r, symax = max(s.y1, s.y2) + r;
        int cx0 = (int)floor((sxmin - minx) / scell); if (cx0 < 0) cx0 = 0; if (cx0 >= CW) cx0 = CW-1;
        int cx1 = (int)floor((sxmax - minx) / scell); if (cx1 < 0) cx1 = 0; if (cx1 >= CW) cx1 = CW-1;
        int cy0 = (int)floor((symin - miny) / scell); if (cy0 < 0) cy0 = 0; if (cy0 >= CH) cy0 = CH-1;
        int cy1 = (int)floor((symax - miny) / scell); if (cy1 < 0) cy1 = 0; if (cy1 >= CH) cy1 = CH-1;
        for (int cy = cy0; cy <= cy1; ++cy) {
            int base = cy * CW;
            for (int cx = cx0; cx <= cx1; ++cx) {
                coarse[base + cx].push_back(i);
            }
        }
    }

    // Raster evaluation
    const double r2 = r * r;
    uint64_t covered = 0;
    // Process row by row
    for (int iy = 0; iy < H; ++iy) {
        double y = miny + (iy + 0.5) * h;
        int cY = (int)floor((y - miny) / scell);
        if (cY < 0) cY = 0; if (cY >= CH) cY = CH - 1;
        for (int ix = 0; ix < W; ++ix) {
            double x = minx + (ix + 0.5) * h;
            int cX = (int)floor((x - minx) / scell);
            if (cX < 0) cX = 0; if (cX >= CW) cX = CW - 1;
            const auto& cand = coarse[cY * CW + cX];
            bool inside = false;
            for (int idx : cand) {
                if (dist2_point_to_segment(x, y, segs[idx]) <= r2) {
                    inside = true;
                    break;
                }
            }
            if (inside) ++covered;
        }
    }

    double area = covered * (h * h);
    cout.setf(std::ios::fixed);
    cout << setprecision(7) << area << "\n";
    return 0;
}