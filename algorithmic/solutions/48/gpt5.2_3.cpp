#include <bits/stdc++.h>
using namespace std;

struct Vec3 {
    double x, y, z;
};

static inline double clamp01(double v) {
    if (v < 0.0) return 0.0;
    if (v > 1.0) return 1.0;
    return v;
}

static int ceil_cuberoot_ll(long long n) {
    int x = (int)floor(cbrt((long double)n));
    while (1LL * x * x * x < n) ++x;
    while (x > 0 && 1LL * (x - 1) * (x - 1) * (x - 1) >= n) --x;
    return x;
}

static double computeRadius(const vector<Vec3>& p) {
    int n = (int)p.size();
    double minB = 1e100;
    for (int i = 0; i < n; i++) {
        const auto &c = p[i];
        minB = min(minB, min({c.x, 1.0 - c.x, c.y, 1.0 - c.y, c.z, 1.0 - c.z}));
    }
    double minD2 = 1e100;
    for (int i = 0; i < n; i++) {
        for (int j = i + 1; j < n; j++) {
            double dx = p[i].x - p[j].x;
            double dy = p[i].y - p[j].y;
            double dz = p[i].z - p[j].z;
            double d2 = dx * dx + dy * dy + dz * dz;
            if (d2 < minD2) minD2 = d2;
        }
    }
    return min(minB, 0.5 * sqrt(minD2));
}

static vector<Vec3> generateGrid(int n) {
    int g = ceil_cuberoot_ll(n);
    vector<Vec3> pts;
    pts.reserve(n);
    for (int k = 0; k < g && (int)pts.size() < n; k++) {
        for (int j = 0; j < g && (int)pts.size() < n; j++) {
            for (int i = 0; i < g && (int)pts.size() < n; i++) {
                Vec3 c;
                c.x = (i + 0.5) / g;
                c.y = (j + 0.5) / g;
                c.z = (k + 0.5) / g;
                pts.push_back(c);
            }
        }
    }
    return pts;
}

static vector<Vec3> generateFCC(int n) {
    const double invSqrt2 = 1.0 / sqrt(2.0);
    int m = (int)ceil(cbrt((long double)n / 4.0));
    if (m < 1) m = 1;
    while (4LL * m * m * m < n) ++m;

    const double shrink = 1.0 - 1e-12;
    double denom = (m - 0.5) + invSqrt2;
    double a = shrink / denom;
    double r = a / (2.0 * sqrt(2.0));
    double off = r;

    static const double ox[4] = {0.0, 0.0, 0.5, 0.5};
    static const double oy[4] = {0.0, 0.5, 0.0, 0.5};
    static const double oz[4] = {0.0, 0.5, 0.5, 0.0};

    vector<Vec3> pts;
    pts.reserve(n);
    for (int k = 0; k < m && (int)pts.size() < n; k++) {
        for (int j = 0; j < m && (int)pts.size() < n; j++) {
            for (int i = 0; i < m && (int)pts.size() < n; i++) {
                for (int t = 0; t < 4 && (int)pts.size() < n; t++) {
                    Vec3 c;
                    c.x = off + a * (i + ox[t]);
                    c.y = off + a * (j + oy[t]);
                    c.z = off + a * (k + oz[t]);
                    c.x = clamp01(c.x);
                    c.y = clamp01(c.y);
                    c.z = clamp01(c.z);
                    pts.push_back(c);
                }
            }
        }
    }
    return pts;
}

static vector<Vec3> initJitteredGrid(int n, mt19937_64 &rng) {
    int g = ceil_cuberoot_ll(n);
    uniform_real_distribution<double> U(-0.5, 0.5);
    double cell = 1.0 / g;
    double jitter = 0.35 * cell;
    const double epsWall = 1e-6;

    vector<Vec3> pts(n);
    for (int idx = 0; idx < n; idx++) {
        int i = idx % g;
        int j = (idx / g) % g;
        int k = (idx / (g * g));
        double x = (i + 0.5) * cell + U(rng) * jitter;
        double y = (j + 0.5) * cell + U(rng) * jitter;
        double z = (k + 0.5) * cell + U(rng) * jitter;
        x = min(1.0 - epsWall, max(epsWall, x));
        y = min(1.0 - epsWall, max(epsWall, y));
        z = min(1.0 - epsWall, max(epsWall, z));
        pts[idx] = {x, y, z};
    }
    shuffle(pts.begin(), pts.end(), rng);
    return pts;
}

static vector<Vec3> initRandom(int n, mt19937_64 &rng) {
    uniform_real_distribution<double> U(0.0, 1.0);
    const double epsWall = 1e-6;
    vector<Vec3> pts(n);
    for (int i = 0; i < n; i++) {
        double x = U(rng), y = U(rng), z = U(rng);
        x = min(1.0 - epsWall, max(epsWall, x));
        y = min(1.0 - epsWall, max(epsWall, y));
        z = min(1.0 - epsWall, max(epsWall, z));
        pts[i] = {x, y, z};
    }
    return pts;
}

static void relaxRepulsion(vector<Vec3>& p, int iters) {
    int n = (int)p.size();
    vector<Vec3> f(n);
    const double eps = 1e-12;
    const double epsWall = 1e-6;

    double startMove = 0.05;
    double endMove = 1e-5;
    if (iters <= 1) iters = 1;
    double decay = pow(endMove / startMove, 1.0 / iters);
    double maxMove = startMove;

    for (int iter = 0; iter < iters; iter++) {
        for (int i = 0; i < n; i++) f[i] = {0.0, 0.0, 0.0};

        for (int i = 0; i < n; i++) {
            for (int j = i + 1; j < n; j++) {
                double dx = p[i].x - p[j].x;
                double dy = p[i].y - p[j].y;
                double dz = p[i].z - p[j].z;
                double d2 = dx * dx + dy * dy + dz * dz + eps;
                double inv = 1.0 / (d2 * sqrt(d2)); // 1/r^3
                double fx = dx * inv, fy = dy * inv, fz = dz * inv;
                f[i].x += fx; f[i].y += fy; f[i].z += fz;
                f[j].x -= fx; f[j].y -= fy; f[j].z -= fz;
            }
        }

        // Wall repulsion via self-mirrors across each face
        for (int i = 0; i < n; i++) {
            // x=0 mirror
            {
                double dx = 2.0 * p[i].x;
                double d2 = dx * dx + eps;
                double inv = 1.0 / (d2 * sqrt(d2));
                f[i].x += dx * inv;
            }
            // x=1 mirror
            {
                double dx = 2.0 * (p[i].x - 1.0);
                double d2 = dx * dx + eps;
                double inv = 1.0 / (d2 * sqrt(d2));
                f[i].x += dx * inv;
            }
            // y=0 mirror
            {
                double dy = 2.0 * p[i].y;
                double d2 = dy * dy + eps;
                double inv = 1.0 / (d2 * sqrt(d2));
                f[i].y += dy * inv;
            }
            // y=1 mirror
            {
                double dy = 2.0 * (p[i].y - 1.0);
                double d2 = dy * dy + eps;
                double inv = 1.0 / (d2 * sqrt(d2));
                f[i].y += dy * inv;
            }
            // z=0 mirror
            {
                double dz = 2.0 * p[i].z;
                double d2 = dz * dz + eps;
                double inv = 1.0 / (d2 * sqrt(d2));
                f[i].z += dz * inv;
            }
            // z=1 mirror
            {
                double dz = 2.0 * (p[i].z - 1.0);
                double d2 = dz * dz + eps;
                double inv = 1.0 / (d2 * sqrt(d2));
                f[i].z += dz * inv;
            }
        }

        double maxNorm = 0.0;
        for (int i = 0; i < n; i++) {
            double norm = sqrt(f[i].x * f[i].x + f[i].y * f[i].y + f[i].z * f[i].z);
            if (norm > maxNorm) maxNorm = norm;
        }
        if (maxNorm < 1e-30) break;

        double scale = maxMove / maxNorm;
        for (int i = 0; i < n; i++) {
            p[i].x += f[i].x * scale;
            p[i].y += f[i].y * scale;
            p[i].z += f[i].z * scale;

            p[i].x = min(1.0 - epsWall, max(epsWall, p[i].x));
            p[i].y = min(1.0 - epsWall, max(epsWall, p[i].y));
            p[i].z = min(1.0 - epsWall, max(epsWall, p[i].z));
        }

        maxMove *= decay;
    }
}

static void outputGridOnTheFly(long long n) {
    int g = ceil_cuberoot_ll(n);
    cout << setprecision(17);
    long long cnt = 0;
    for (int k = 0; k < g && cnt < n; k++) {
        for (int j = 0; j < g && cnt < n; j++) {
            for (int i = 0; i < g && cnt < n; i++) {
                double x = (i + 0.5) / g;
                double y = (j + 0.5) / g;
                double z = (k + 0.5) / g;
                cout << x << ' ' << y << ' ' << z << '\n';
                cnt++;
            }
        }
    }
}

static void outputFCCOnTheFly(long long n) {
    const double invSqrt2 = 1.0 / sqrt(2.0);
    int m = (int)ceil(cbrt((long double)n / 4.0));
    if (m < 1) m = 1;
    while (4LL * m * m * m < n) ++m;

    const double shrink = 1.0 - 1e-12;
    double denom = (m - 0.5) + invSqrt2;
    double a = shrink / denom;
    double r = a / (2.0 * sqrt(2.0));
    double off = r;

    static const double ox[4] = {0.0, 0.0, 0.5, 0.5};
    static const double oy[4] = {0.0, 0.5, 0.0, 0.5};
    static const double oz[4] = {0.0, 0.5, 0.5, 0.0};

    cout << setprecision(17);
    long long cnt = 0;
    for (int k = 0; k < m && cnt < n; k++) {
        for (int j = 0; j < m && cnt < n; j++) {
            for (int i = 0; i < m && cnt < n; i++) {
                for (int t = 0; t < 4 && cnt < n; t++) {
                    double x = off + a * (i + ox[t]);
                    double y = off + a * (j + oy[t]);
                    double z = off + a * (k + oz[t]);
                    // should already be inside; clamp softly just in case
                    x = clamp01(x);
                    y = clamp01(y);
                    z = clamp01(z);
                    cout << x << ' ' << y << ' ' << z << '\n';
                    cnt++;
                }
            }
        }
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    long long nll;
    if (!(cin >> nll)) return 0;
    int n = (int)nll;

    if (n <= 256) {
        mt19937_64 rng(0xC0FFEEULL ^ (uint64_t)nll);

        vector<Vec3> best = generateGrid(n);
        double bestR = computeRadius(best);

        {
            vector<Vec3> cand = generateFCC(n);
            double r = computeRadius(cand);
            if (r > bestR) { bestR = r; best.swap(cand); }
        }

        int restarts, iters;
        if (n <= 16) { restarts = 10; iters = 3500; }
        else if (n <= 32) { restarts = 8; iters = 3000; }
        else if (n <= 64) { restarts = 5; iters = 2200; }
        else if (n <= 128) { restarts = 3; iters = 1600; }
        else { restarts = 2; iters = 1200; }

        for (int r = 0; r < restarts; r++) {
            vector<Vec3> cand;
            if (r % 2 == 0) cand = initJitteredGrid(n, rng);
            else cand = initRandom(n, rng);

            relaxRepulsion(cand, iters);
            double rad = computeRadius(cand);
            if (rad > bestR) {
                bestR = rad;
                best.swap(cand);
            }
        }

        cout << setprecision(17);
        for (int i = 0; i < n; i++) {
            double x = clamp01(best[i].x);
            double y = clamp01(best[i].y);
            double z = clamp01(best[i].z);
            cout << x << ' ' << y << ' ' << z << '\n';
        }
        return 0;
    }

    int g = ceil_cuberoot_ll(nll);
    double r_grid = 1.0 / (2.0 * g);

    const double invSqrt2 = 1.0 / sqrt(2.0);
    int m = (int)ceil(cbrt((long double)nll / 4.0));
    if (m < 1) m = 1;
    while (4LL * m * m * m < nll) ++m;

    const double shrink = 1.0 - 1e-12;
    double denom = (m - 0.5) + invSqrt2;
    double a = shrink / denom;
    double r_fcc = a / (2.0 * sqrt(2.0));

    if (r_fcc > r_grid) outputFCCOnTheFly(nll);
    else outputGridOnTheFly(nll);

    return 0;
}