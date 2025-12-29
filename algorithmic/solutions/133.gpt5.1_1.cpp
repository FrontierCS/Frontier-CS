#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;
    vector<double> xs(n), ys(n);
    for (int i = 0; i < n; ++i) {
        cin >> xs[i] >> ys[i];
    }

    int m;
    cin >> m;
    vector<int> segA(m), segB(m);
    double L_tot = 0.0;
    for (int i = 0; i < m; ++i) {
        int a, b;
        cin >> a >> b;
        --a; --b;
        segA[i] = a;
        segB[i] = b;
        double dx = xs[a] - xs[b];
        double dy = ys[a] - ys[b];
        L_tot += hypot(dx, dy);
    }

    double r;
    cin >> r;
    double p1, p2, p3, p4;
    cin >> p1 >> p2 >> p3 >> p4; // p2 and p4 unused

    const double PI = acos(-1.0);
    const double WIDTH = 210.0;
    const double MINX = -105.0;
    const double MINY = -105.0;
    const double AREA_BOX = WIDTH * WIDTH;

    double A_total = 2.0 * r * L_tot + (double)m * PI * r * r;

    const long long MAX_CELLS = 100000000LL; // up to 1e8 cells (~100MB for uint8_t grid)
    const double s_min2 = AREA_BOX / double(MAX_CELLS);

    const double UPDATES_BUDGET = 2e8; // used to choose grid resolution
    double raw_s2 = (A_total > 0.0 ? (A_total / UPDATES_BUDGET) : s_min2);
    double s2 = max(raw_s2, s_min2);
    double s = sqrt(s2);
    int Nx = (int)ceil(WIDTH / s);
    if (Nx < 1) Nx = 1;
    s = WIDTH / Nx;
    s2 = s * s;
    int Ny = Nx;
    size_t Ncells = (size_t)Nx * (size_t)Ny;

    vector<unsigned char> grid(Ncells, 0);

    vector<double> xCenters(Nx), yCenters(Ny);
    for (int i = 0; i < Nx; ++i) {
        xCenters[i] = MINX + (i + 0.5) * s;
    }
    for (int j = 0; j < Ny; ++j) {
        yCenters[j] = MINY + (j + 0.5) * s;
    }

    // Choose disc sampling step along segments
    const double DISC_BUDGET = 1e8; // limit total number of discs
    double ds2 = (L_tot > 0.0 ? (L_tot / DISC_BUDGET) : 0.0);
    double ds = r * 0.5;
    if (ds2 > ds) ds = ds2;
    if (ds <= 0.0) ds = 1.0; // fallback, should not happen as r > 0

    double r2 = r * r;

    auto rasterDisc = [&](double cx, double cy) {
        double yMinC = cy - r;
        double yMaxC = cy + r;
        int jBeg = (int)((yMinC - MINY) / s);
        if (jBeg < 0) jBeg = 0;
        int jEnd = (int)((yMaxC - MINY) / s);
        if (jEnd >= Ny) jEnd = Ny - 1;
        for (int jy = jBeg; jy <= jEnd; ++jy) {
            double dy = yCenters[jy] - cy;
            double dy2 = dy * dy;
            if (dy2 > r2) continue;
            double dxMax = sqrt(r2 - dy2);
            double xMinC = cx - dxMax;
            double xMaxC = cx + dxMax;
            int iBeg = (int)((xMinC - MINX) / s);
            if (iBeg < 0) iBeg = 0;
            int iEnd = (int)((xMaxC - MINX) / s);
            if (iEnd >= Nx) iEnd = Nx - 1;
            size_t rowOffset = (size_t)jy * (size_t)Nx;
            for (int ix = iBeg; ix <= iEnd; ++ix) {
                grid[rowOffset + ix] = 1;
            }
        }
    };

    for (int e = 0; e < m; ++e) {
        int a = segA[e];
        int b = segB[e];
        double x1 = xs[a], y1 = ys[a];
        double x2 = xs[b], y2 = ys[b];
        double dx = x2 - x1;
        double dy = y2 - y1;
        double len = hypot(dx, dy);
        if (len < 1e-9) {
            rasterDisc(x1, y1);
        } else {
            int steps = max(1, (int)ceil(len / ds));
            double inv_steps = 1.0 / steps;
            for (int k = 0; k <= steps; ++k) {
                double t = k * inv_steps;
                double cx = x1 + dx * t;
                double cy = y1 + dy * t;
                rasterDisc(cx, cy);
            }
        }
    }

    size_t count = 0;
    for (size_t i = 0; i < Ncells; ++i) {
        if (grid[i]) ++count;
    }
    double area = (double)count * s * s;

    cout.setf(ios::fixed);
    cout << setprecision(7) << area << '\n';

    return 0;
}