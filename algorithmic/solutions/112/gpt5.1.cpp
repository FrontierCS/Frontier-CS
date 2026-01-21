#include <bits/stdc++.h>
using namespace std;

struct Point {
    double x, y, z;
};

bool build_points_RSA(int n, double delta, vector<Point>& pts, mt19937_64& rng) {
    pts.clear();
    pts.reserve(n);
    const double PI = acos(-1.0);
    const double cellSize = delta / sqrt(3.0);
    const double invCellSize = 1.0 / cellSize;
    int Nx = (int)ceil(2.0 * invCellSize);
    int Ny = Nx, Nz = Nx;
    int Ncells = Nx * Ny * Nz;

    vector<int> grid(Ncells, -1);
    vector<int> next(n, -1);

    uniform_real_distribution<double> U01(0.0, 1.0);
    const double delta2 = delta * delta;
    const int MAX_TRIES = 200;
    const int RANGE = 2;

    auto cellIndex = [Ny, Nz](int ix, int iy, int iz) {
        return (ix * Ny + iy) * Nz + iz;
    };

    for (int i = 0; i < n; ++i) {
        bool placed = false;
        for (int tries = 0; tries < MAX_TRIES; ++tries) {
            double u1 = U01(rng);
            double u2 = U01(rng);
            double u3 = U01(rng);

            double zdir = 2.0 * u1 - 1.0;
            double t = sqrt(max(0.0, 1.0 - zdir * zdir));
            double phi = 2.0 * PI * u2;
            double r = cbrt(u3);

            double x = r * t * cos(phi);
            double y = r * t * sin(phi);
            double z = r * zdir;

            int ix = (int)((x + 1.0) * invCellSize);
            int iy = (int)((y + 1.0) * invCellSize);
            int iz = (int)((z + 1.0) * invCellSize);
            if (ix < 0) ix = 0; else if (ix >= Nx) ix = Nx - 1;
            if (iy < 0) iy = 0; else if (iy >= Ny) iy = Ny - 1;
            if (iz < 0) iz = 0; else if (iz >= Nz) iz = Nz - 1;

            bool ok = true;
            for (int dx = -RANGE; dx <= RANGE && ok; ++dx) {
                int nx = ix + dx;
                if (nx < 0 || nx >= Nx) continue;
                for (int dy = -RANGE; dy <= RANGE && ok; ++dy) {
                    int ny = iy + dy;
                    if (ny < 0 || ny >= Ny) continue;
                    for (int dz = -RANGE; dz <= RANGE; ++dz) {
                        int nz = iz + dz;
                        if (nz < 0 || nz >= Nz) continue;
                        int idx = cellIndex(nx, ny, nz);
                        int pj = grid[idx];
                        while (pj != -1) {
                            const Point& q = pts[pj];
                            double dxp = x - q.x;
                            double dyp = y - q.y;
                            double dzp = z - q.z;
                            double dist2 = dxp * dxp + dyp * dyp + dzp * dzp;
                            if (dist2 < delta2) {
                                ok = false;
                                break;
                            }
                            pj = next[pj];
                        }
                        if (!ok) break;
                    }
                }
            }

            if (ok) {
                int newIndex = (int)pts.size();
                pts.push_back({x, y, z});
                int idx0 = cellIndex(ix, iy, iz);
                next[newIndex] = grid[idx0];
                grid[idx0] = newIndex;
                placed = true;
                break;
            }
        }
        if (!placed) {
            return false;
        }
    }
    return true;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    vector<Point> pts;

    if (n == 2) {
        pts.push_back({0.0, 0.0, 1.0});
        pts.push_back({0.0, 0.0, -1.0});
    } else if (n == 3) {
        double s3 = sqrt(3.0);
        pts.push_back({1.0, 0.0, 0.0});
        pts.push_back({-0.5, 0.5 * s3, 0.0});
        pts.push_back({-0.5, -0.5 * s3, 0.0});
    } else if (n == 4) {
        double f = 1.0 / sqrt(3.0);
        pts.push_back({ f,  f,  f});
        pts.push_back({ f, -f, -f});
        pts.push_back({-f,  f, -f});
        pts.push_back({-f, -f,  f});
    } else {
        mt19937_64 rng(123456789ULL);
        double delta = 1.4 / cbrt((double)n);
        bool ok = build_points_RSA(n, delta, pts, rng);
        if (!ok || (int)pts.size() != n) {
            // Fallback: purely random points inside unit sphere
            pts.clear();
            pts.reserve(n);
            uniform_real_distribution<double> U01(0.0, 1.0);
            const double PI = acos(-1.0);
            for (int i = 0; i < n; ++i) {
                double u1 = U01(rng);
                double u2 = U01(rng);
                double u3 = U01(rng);
                double zdir = 2.0 * u1 - 1.0;
                double t = sqrt(max(0.0, 1.0 - zdir * zdir));
                double phi = 2.0 * PI * u2;
                double r = cbrt(u3);
                double x = r * t * cos(phi);
                double y = r * t * sin(phi);
                double z = r * zdir;
                pts.push_back({x, y, z});
            }
        }
    }

    // Compute minimum pairwise distance
    double minD2 = 1e100;
    for (int i = 0; i < n; ++i) {
        for (int j = i + 1; j < n; ++j) {
            double dx = pts[i].x - pts[j].x;
            double dy = pts[i].y - pts[j].y;
            double dz = pts[i].z - pts[j].z;
            double d2 = dx * dx + dy * dy + dz * dz;
            if (d2 < minD2) minD2 = d2;
        }
    }
    double minD = sqrt(minD2);

    cout.setf(ios::fixed);
    cout << setprecision(15) << minD << '\n';
    for (int i = 0; i < n; ++i) {
        cout << setprecision(15)
             << pts[i].x << ' ' << pts[i].y << ' ' << pts[i].z << '\n';
    }

    return 0;
}