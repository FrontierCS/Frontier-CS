#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if (!(cin >> n)) return 0;

    const double PI = acos(-1.0);
    const double GA = PI * (3.0 - sqrt(5.0)); // golden angle

    vector<double> x(n), y(n), z(n);

    if (n == 2) {
        x[0] = 0.0; y[0] = 0.0; z[0] = 1.0;
        x[1] = 0.0; y[1] = 0.0; z[1] = -1.0;
    } else {
        for (int k = 0; k < n; ++k) {
            double zk = 1.0 - (2.0*(k + 0.5))/double(n);
            double rk = sqrt(max(0.0, 1.0 - zk*zk));
            double theta = GA * k;
            double ck = cos(theta), sk = sin(theta);
            x[k] = rk * ck;
            y[k] = rk * sk;
            z[k] = zk;
        }

        // Small repulsion iterations to improve spacing
        int iters;
        if (n <= 10) iters = 400;
        else if (n <= 30) iters = 200;
        else if (n <= 100) iters = 120;
        else if (n <= 300) iters = 100;
        else if (n <= 700) iters = 80;
        else iters = 60;

        double base0 = 0.05, base1 = 0.005;
        double scale = 1.0 / sqrt((double)n);
        double eps2 = 1e-12;

        vector<double> fx(n), fy(n), fz(n);

        for (int it = 0; it < iters; ++it) {
            double t = (iters <= 1) ? 1.0 : (double)it / (double)(iters - 1);
            double step = (base0 * pow(base1 / base0, t)) * scale;

            fill(fx.begin(), fx.end(), 0.0);
            fill(fy.begin(), fy.end(), 0.0);
            fill(fz.begin(), fz.end(), 0.0);

            for (int i = 0; i < n; ++i) {
                double xi = x[i], yi = y[i], zi = z[i];
                for (int j = i + 1; j < n; ++j) {
                    double dx = xi - x[j];
                    double dy = yi - y[j];
                    double dz = zi - z[j];
                    double r2 = dx*dx + dy*dy + dz*dz + eps2;
                    double inv = 1.0 / r2; // simple inverse-square-like interaction
                    double fxij = dx * inv;
                    double fyij = dy * inv;
                    double fzij = dz * inv;
                    fx[i] += fxij; fy[i] += fyij; fz[i] += fzij;
                    fx[j] -= fxij; fy[j] -= fyij; fz[j] -= fzij;
                }
            }

            for (int i = 0; i < n; ++i) {
                // Project force onto tangent plane
                double dot = fx[i]*x[i] + fy[i]*y[i] + fz[i]*z[i];
                double tx = fx[i] - dot * x[i];
                double ty = fy[i] - dot * y[i];
                double tz = fz[i] - dot * z[i];

                x[i] += step * tx;
                y[i] += step * ty;
                z[i] += step * tz;

                // Renormalize to unit sphere
                double norm = sqrt(x[i]*x[i] + y[i]*y[i] + z[i]*z[i]);
                if (norm > 0) {
                    x[i] /= norm; y[i] /= norm; z[i] /= norm;
                } else {
                    // Fallback in the unlikely event of zero norm
                    x[i] = 0; y[i] = 0; z[i] = 1;
                }
            }
        }
    }

    // Compute minimum pairwise distance
    double minDist2 = 1e100;
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
    cout << setprecision(15) << minDist << "\n";
    for (int i = 0; i < n; ++i) {
        cout << setprecision(15) << x[i] << " " << y[i] << " " << z[i] << "\n";
    }

    return 0;
}