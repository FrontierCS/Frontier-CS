#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if (!(cin >> n)) return 0;

    const double PI = acos(-1.0);
    const double GA = PI * (3.0 - sqrt(5.0)); // golden angle
    const double SHRINK = 1.0 - 1e-12;

    vector<double> x(n), y(n), z(n);

    auto renorm = [&](int i) {
        double r = sqrt(x[i]*x[i] + y[i]*y[i] + z[i]*z[i]);
        if (r == 0.0) { x[i] = SHRINK; y[i] = 0.0; z[i] = 0.0; return; }
        double s = SHRINK / r;
        x[i] *= s; y[i] *= s; z[i] *= s;
    };

    auto set_point = [&](int i, double xi, double yi, double zi){
        x[i] = xi; y[i] = yi; z[i] = zi;
        renorm(i);
    };

    bool special = false;

    if (n == 2) {
        special = true;
        set_point(0, 0.0, 0.0, 1.0);
        set_point(1, 0.0, 0.0, -1.0);
    } else if (n == 3) {
        special = true;
        for (int i = 0; i < 3; ++i) {
            double ang = 2.0 * PI * i / 3.0;
            set_point(i, cos(ang), sin(ang), 0.0);
        }
    } else if (n == 4) {
        special = true;
        double s = 1.0 / sqrt(3.0);
        set_point(0,  s,  s,  s);
        set_point(1, -s, -s,  s);
        set_point(2, -s,  s, -s);
        set_point(3,  s, -s, -s);
    } else if (n == 5) {
        special = true;
        set_point(0, 0.0, 0.0, 1.0);
        set_point(1, 0.0, 0.0, -1.0);
        for (int i = 0; i < 3; ++i) {
            double ang = 2.0 * PI * i / 3.0;
            set_point(2 + i, cos(ang), sin(ang), 0.0);
        }
    } else if (n == 6) {
        special = true;
        set_point(0, 1.0, 0.0, 0.0);
        set_point(1, -1.0, 0.0, 0.0);
        set_point(2, 0.0, 1.0, 0.0);
        set_point(3, 0.0, -1.0, 0.0);
        set_point(4, 0.0, 0.0, 1.0);
        set_point(5, 0.0, 0.0, -1.0);
    }

    if (!special) {
        for (int i = 0; i < n; ++i) {
            double zi = 1.0 - (2.0 * (i + 0.5)) / n;
            double r = sqrt(max(0.0, 1.0 - zi * zi));
            double phi = i * GA;
            x[i] = r * cos(phi);
            y[i] = r * sin(phi);
            z[i] = zi;
            renorm(i);
        }

        // Repulsive relaxation on the sphere
        vector<double> fx(n), fy(n), fz(n);

        auto iterations_for_n = [&](int m)->int {
            if (m <= 20) return 150;
            if (m <= 50) return 120;
            if (m <= 100) return 100;
            if (m <= 200) return 80;
            if (m <= 400) return 60;
            if (m <= 600) return 45;
            if (m <= 800) return 35;
            return 30;
        };
        auto initial_eta = [&](int m)->double {
            if (m <= 20) return 0.2;
            if (m <= 100) return 0.15;
            if (m <= 400) return 0.12;
            return 0.10;
        };

        int iters = iterations_for_n(n);
        double eta = initial_eta(n);
        double decay = 0.98;

        for (int it = 0; it < iters; ++it) {
            fill(fx.begin(), fx.end(), 0.0);
            fill(fy.begin(), fy.end(), 0.0);
            fill(fz.begin(), fz.end(), 0.0);

            for (int i = 0; i < n; ++i) {
                for (int j = i + 1; j < n; ++j) {
                    double dx = x[i] - x[j];
                    double dy = y[i] - y[j];
                    double dz = z[i] - z[j];
                    double d2 = dx*dx + dy*dy + dz*dz + 1e-12;
                    double inv = 1.0 / d2; // ~ 1/|d|
                    double fxij = dx * inv;
                    double fyij = dy * inv;
                    double fzij = dz * inv;
                    fx[i] += fxij; fy[i] += fyij; fz[i] += fzij;
                    fx[j] -= fxij; fy[j] -= fyij; fz[j] -= fzij;
                }
            }

            double maxnorm = 0.0;
            for (int i = 0; i < n; ++i) {
                double dotp = fx[i]*x[i] + fy[i]*y[i] + fz[i]*z[i];
                fx[i] -= dotp * x[i];
                fy[i] -= dotp * y[i];
                fz[i] -= dotp * z[i];
                double nn = sqrt(fx[i]*fx[i] + fy[i]*fy[i] + fz[i]*fz[i]);
                if (nn > maxnorm) maxnorm = nn;
            }

            double step = (maxnorm > 1e-20) ? (eta / maxnorm) : 0.0;

            for (int i = 0; i < n; ++i) {
                x[i] += step * fx[i];
                y[i] += step * fy[i];
                z[i] += step * fz[i];
                renorm(i);
            }

            eta *= decay;
        }
    }

    // Compute actual minimum pairwise distance
    double minDist2 = 1e300;
    for (int i = 0; i < n; ++i) {
        for (int j = i + 1; j < n; ++j) {
            double dx = x[i] - x[j];
            double dy = y[i] - y[j];
            double dz = z[i] - z[j];
            double d2 = dx*dx + dy*dy + dz*dz;
            if (d2 < minDist2) minDist2 = d2;
        }
    }
    double minDist = sqrt(minDist2);

    cout.setf(std::ios::fixed);
    cout << setprecision(12) << minDist << "\n";
    for (int i = 0; i < n; ++i) {
        cout << setprecision(12) << x[i] << " " << y[i] << " " << z[i] << "\n";
    }

    return 0;
}