#include <bits/stdc++.h>
using namespace std;

static inline void normalize_inplace(array<double,3>& v) {
    double x = v[0], y = v[1], z = v[2];
    double n = sqrt(x*x + y*y + z*z);
    if (n <= 0) { v = {0.0, 0.0, 1.0}; return; }
    double s = (1.0 - 1e-12) / n;
    v[0] *= s; v[1] *= s; v[2] *= s;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    vector<array<double,3>> p(n);

    auto output = [&](const vector<array<double,3>>& pts) {
        double md = numeric_limits<double>::infinity();
        for (int i = 0; i < (int)pts.size(); i++) {
            for (int j = i + 1; j < (int)pts.size(); j++) {
                double dx = pts[i][0] - pts[j][0];
                double dy = pts[i][1] - pts[j][1];
                double dz = pts[i][2] - pts[j][2];
                double d = sqrt(dx*dx + dy*dy + dz*dz);
                if (d < md) md = d;
            }
        }

        cout.setf(std::ios::fixed);
        cout << setprecision(15) << md << "\n";
        for (auto &v : pts) {
            cout << setprecision(15) << v[0] << " " << v[1] << " " << v[2] << "\n";
        }
    };

    if (n <= 6) {
        if (n == 2) {
            p[0] = {0.0, 0.0, 1.0};
            p[1] = {0.0, 0.0, -1.0};
        } else if (n == 3) {
            const double pi = acos(-1.0);
            for (int i = 0; i < 3; i++) {
                double a = 2.0 * pi * i / 3.0;
                p[i] = {cos(a), sin(a), 0.0};
            }
        } else if (n == 4) {
            p[0] = {1.0, 1.0, 1.0};
            p[1] = {1.0, -1.0, -1.0};
            p[2] = {-1.0, 1.0, -1.0};
            p[3] = {-1.0, -1.0, 1.0};
        } else if (n == 5) {
            p[0] = {0.0, 0.0, 1.0};
            p[1] = {0.0, 0.0, -1.0};
            const double pi = acos(-1.0);
            for (int i = 0; i < 3; i++) {
                double a = 2.0 * pi * i / 3.0;
                p[2 + i] = {cos(a), sin(a), 0.0};
            }
        } else if (n == 6) {
            p[0] = {1.0, 0.0, 0.0};
            p[1] = {-1.0, 0.0, 0.0};
            p[2] = {0.0, 1.0, 0.0};
            p[3] = {0.0, -1.0, 0.0};
            p[4] = {0.0, 0.0, 1.0};
            p[5] = {0.0, 0.0, -1.0};
        }
        for (auto &v : p) normalize_inplace(v);
        output(p);
        return 0;
    }

    // Fibonacci spiral initialization on the sphere
    const double pi = acos(-1.0);
    const double ga = pi * (3.0 - sqrt(5.0)); // golden angle
    for (int i = 0; i < n; i++) {
        double t = (i + 0.5) / (double)n;
        double z = 1.0 - 2.0 * t;
        double r = sqrt(max(0.0, 1.0 - z*z));
        double theta = ga * i;
        p[i] = {r * cos(theta), r * sin(theta), z};
        normalize_inplace(p[i]);
    }

    // Repulsion iterations
    int iters;
    if (n <= 200) iters = 60;
    else if (n <= 500) iters = 30;
    else iters = 15;

    double step = 0.2 / (double)n;
    double maxMove = 0.10;

    vector<array<double,3>> f(n);

    for (int it = 0; it < iters; it++) {
        for (int i = 0; i < n; i++) f[i] = {0.0, 0.0, 0.0};

        for (int i = 0; i < n; i++) {
            const auto &pii = p[i];
            for (int j = i + 1; j < n; j++) {
                double dx = pii[0] - p[j][0];
                double dy = pii[1] - p[j][1];
                double dz = pii[2] - p[j][2];
                double d2 = dx*dx + dy*dy + dz*dz;
                if (d2 < 1e-12) d2 = 1e-12;
                double inv = 1.0 / sqrt(d2);
                double inv3 = inv * inv * inv;
                double fx = dx * inv3;
                double fy = dy * inv3;
                double fz = dz * inv3;
                f[i][0] += fx; f[i][1] += fy; f[i][2] += fz;
                f[j][0] -= fx; f[j][1] -= fy; f[j][2] -= fz;
            }
        }

        for (int i = 0; i < n; i++) {
            double mx = step * f[i][0];
            double my = step * f[i][1];
            double mz = step * f[i][2];
            double ml = sqrt(mx*mx + my*my + mz*mz);
            if (ml > maxMove) {
                double s = maxMove / ml;
                mx *= s; my *= s; mz *= s;
            }
            p[i][0] += mx; p[i][1] += my; p[i][2] += mz;
            normalize_inplace(p[i]);
        }

        step *= 0.95;
        maxMove *= 0.95;
    }

    output(p);
    return 0;
}