#include <iostream>
#include <vector>
#include <cmath>
#include <cstdlib>
#include <algorithm>
#include <iomanip>

using namespace std;

struct Point {
    double x, y, z;
};

int main() {
    int n;
    cin >> n;

    // Initialization: perturbed cubic grid
    int m = (int)ceil(pow(n, 1.0/3));
    double spacing = 1.0 / m;
    vector<Point> pts(n);
    srand(12345);  // fixed seed for reproducibility
    for (int i = 0; i < n; ++i) {
        int ix = i % m;
        int iy = (i / m) % m;
        int iz = i / (m * m);
        double jitter = (rand() / (double)RAND_MAX - 0.5) * spacing * 0.5;
        pts[i].x = (ix + 0.5) * spacing + jitter;
        pts[i].y = (iy + 0.5) * spacing + jitter;
        pts[i].z = (iz + 0.5) * spacing + jitter;
        // clamp to [0,1]
        pts[i].x = max(0.0, min(1.0, pts[i].x));
        pts[i].y = max(0.0, min(1.0, pts[i].y));
        pts[i].z = max(0.0, min(1.0, pts[i].z));
    }

    // Parameters
    double D = 1.0 / m;               // target separation
    double margin = D / 2;            // desired minimum distance to cube faces
    double cellSize = D / 2;          // spatial grid cell size
    int ncell = (int)(1.0 / cellSize) + 2;
    int maxIter = 200;
    double initialStep = 0.1;
    double finalStep = 0.01;

    for (int iter = 0; iter < maxIter; ++iter) {
        double step = initialStep * (1.0 - (double)iter / maxIter) + finalStep * ((double)iter / maxIter);

        // Build spatial grid
        vector<vector<int>> grid(ncell * ncell * ncell);
        for (int i = 0; i < n; ++i) {
            int ix = (int)(pts[i].x / cellSize);
            int iy = (int)(pts[i].y / cellSize);
            int iz = (int)(pts[i].z / cellSize);
            ix = max(0, min(ncell - 1, ix));
            iy = max(0, min(ncell - 1, iy));
            iz = max(0, min(ncell - 1, iz));
            int idx = (ix * ncell + iy) * ncell + iz;
            grid[idx].push_back(i);
        }

        vector<Point> newPts = pts;  // copy for update

        for (int i = 0; i < n; ++i) {
            double fx = 0.0, fy = 0.0, fz = 0.0;
            int cx = (int)(pts[i].x / cellSize);
            int cy = (int)(pts[i].y / cellSize);
            int cz = (int)(pts[i].z / cellSize);

            // Repulsion from nearby points
            for (int di = -1; di <= 1; ++di) {
                for (int dj = -1; dj <= 1; ++dj) {
                    for (int dk = -1; dk <= 1; ++dk) {
                        int nx = cx + di, ny = cy + dj, nz = cz + dk;
                        if (nx < 0 || nx >= ncell || ny < 0 || ny >= ncell || nz < 0 || nz >= ncell)
                            continue;
                        int idx = (nx * ncell + ny) * ncell + nz;
                        for (int j : grid[idx]) {
                            if (i == j) continue;
                            double dx = pts[i].x - pts[j].x;
                            double dy = pts[i].y - pts[j].y;
                            double dz = pts[i].z - pts[j].z;
                            double d2 = dx*dx + dy*dy + dz*dz;
                            if (d2 < 1e-12) continue;
                            double d = sqrt(d2);
                            if (d < D) {
                                double f = (D - d) / d;
                                fx += f * dx / d;
                                fy += f * dy / d;
                                fz += f * dz / d;
                            }
                        }
                    }
                }
            }

            // Repulsion from cube faces
            if (pts[i].x < margin)        fx += (margin - pts[i].x);
            if (pts[i].x > 1 - margin)    fx += (1 - margin - pts[i].x);
            if (pts[i].y < margin)        fy += (margin - pts[i].y);
            if (pts[i].y > 1 - margin)    fy += (1 - margin - pts[i].y);
            if (pts[i].z < margin)        fz += (margin - pts[i].z);
            if (pts[i].z > 1 - margin)    fz += (1 - margin - pts[i].z);

            // Update position
            newPts[i].x = pts[i].x + step * fx;
            newPts[i].y = pts[i].y + step * fy;
            newPts[i].z = pts[i].z + step * fz;

            // Ensure inside [0,1]
            newPts[i].x = max(0.0, min(1.0, newPts[i].x));
            newPts[i].y = max(0.0, min(1.0, newPts[i].y));
            newPts[i].z = max(0.0, min(1.0, newPts[i].z));
        }
        pts = newPts;
    }

    // Output
    cout << fixed << setprecision(10);
    for (int i = 0; i < n; ++i) {
        cout << pts[i].x << " " << pts[i].y << " " << pts[i].z << "\n";
    }

    return 0;
}