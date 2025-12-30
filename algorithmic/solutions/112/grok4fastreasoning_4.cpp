#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(NULL);
    cout << fixed << setprecision(15);
    int n;
    cin >> n;
    if (n == 2) {
        cout << 2.000000000000000 << "\n";
        cout << "0.000000000000000 0.000000000000000 1.000000000000000\n";
        cout << "0.000000000000000 0.000000000000000 -1.000000000000000\n";
        return 0;
    }
    if (n == 3) {
        cout << 1.732050807568878 << "\n";
        double ang = 2.0 * M_PI / 3.0;
        for (int k = 0; k < 3; k++) {
            double th = k * ang;
            cout << cos(th) << " " << sin(th) << " " << "0.000000000000000\n";
        }
        return 0;
    }
    if (n == 4) {
        double s = sqrt(8.0 / 3.0);
        cout << s << "\n";
        double t = 1.0 / sqrt(3.0);
        cout << t << " " << t << " " << t << "\n";
        cout << t << " " << -t << " " << -t << "\n";
        cout << -t << " " << t << " " << -t << "\n";
        cout << -t << " " << -t << " " << t << "\n";
        return 0;
    }
    // general case
    vector<double> X(n), Y(n), Z(n);
    double phi = (1.0 + sqrt(5.0)) / 2.0;
    for (int i = 0; i < n; i++) {
        double zi = 1.0 - (2.0 * i + 1.0) / (2.0 * n);
        double theta = 2.0 * M_PI * i / phi;
        double r = sqrt(1.0 - zi * zi);
        X[i] = r * cos(theta);
        Y[i] = r * sin(theta);
        Z[i] = zi;
    }
    double eps = 0.1;
    int iters = (n <= 200 ? 1000 : 100);
    for (int iter = 0; iter < iters; iter++) {
        vector<double> newX(n), newY(n), newZ(n);
        for (int i = 0; i < n; i++) {
            newX[i] = X[i];
            newY[i] = Y[i];
            newZ[i] = Z[i];
            double Fx = 0.0, Fy = 0.0, Fz = 0.0;
            for (int j = 0; j < n; j++) {
                if (i == j) continue;
                double dx = X[i] - X[j];
                double dy = Y[i] - Y[j];
                double dz = Z[i] - Z[j];
                double d2 = dx * dx + dy * dy + dz * dz;
                double d = sqrt(d2);
                if (d < 1e-12) continue;
                double inv_d3 = 1.0 / (d2 * d);
                Fx += dx * inv_d3;
                Fy += dy * inv_d3;
                Fz += dz * inv_d3;
            }
            newX[i] += eps * Fx;
            newY[i] += eps * Fy;
            newZ[i] += eps * Fz;
            double nn2 = newX[i] * newX[i] + newY[i] * newY[i] + newZ[i] * newZ[i];
            double nn = sqrt(nn2);
            if (nn > 1e-12) {
                newX[i] /= nn;
                newY[i] /= nn;
                newZ[i] /= nn;
            }
        }
        X = newX;
        Y = newY;
        Z = newZ;
    }
    double min_dist = 1e100;
    for (int i = 0; i < n; i++) {
        for (int j = i + 1; j < n; j++) {
            double dx = X[i] - X[j];
            double dy = Y[i] - Y[j];
            double dz = Z[i] - Z[j];
            double d = sqrt(dx * dx + dy * dy + dz * dz);
            if (d < min_dist) min_dist = d;
        }
    }
    cout << min_dist << "\n";
    for (int i = 0; i < n; i++) {
        cout << X[i] << " " << Y[i] << " " << Z[i] << "\n";
    }
    return 0;
}