#include <bits/stdc++.h>
using namespace std;

int main() {
    long long n;
    cin >> n;
    // Compute baseline cubic
    int l = 0;
    while ((long long)l * l * l < n) l++;
    double r_base = 1.0 / (2.0 * l);
    long long target = (n + l - 1LL) / l;
    int best_m = 1, best_k = l;
    double best_balance = 1e9;
    for (int mm = 1; mm <= l; mm++) {
        long long need = (target + mm - 1LL) / mm;
        int kk = (int)need;
        if (kk > l) continue;
        long long prod = (long long)mm * kk * l;
        if (prod >= n) {
            int m2 = mm, k2 = kk;
            if (m2 > k2) swap(m2, k2);
            double balance = abs(m2 - k2) + abs(k2 - l) + abs(l - m2);
            if (balance < best_balance) {
                best_balance = balance;
                best_m = m2;
                best_k = k2;
            }
        }
    }
    int a = best_m, b = best_k, c = l;
    // Now FCC
    int N_fcc = 0;
    while (4LL * N_fcc * N_fcc * N_fcc < n) N_fcc++;
    bool use_fcc = false;
    double r_fcc = 0;
    if (4LL * N_fcc * N_fcc * N_fcc >= n) {
        double M = N_fcc - 0.5;
        double alpha = sqrt(2.0) / 4.0;
        r_fcc = alpha / (M + 2 * alpha);
        if (r_fcc > r_base) {
            use_fcc = true;
        }
    }
    vector<tuple<double, double, double>> points;
    if (use_fcc) {
        // FCC
        double M = N_fcc - 0.5;
        double alpha = sqrt(2.0) / 4.0;
        r_fcc = alpha / (M + 2 * alpha);
        double s = (1.0 - 2 * r_fcc) / M;
        double shift = r_fcc;
        for (int p = 0; p < N_fcc; p++) {
            for (int q = 0; q < N_fcc; q++) {
                for (int rr = 0; rr < N_fcc; rr++) {
                    // 1
                    {
                        double ux = p;
                        double uy = q;
                        double uz = rr;
                        double x = shift + s * ux;
                        double y = shift + s * uy;
                        double z = shift + s * uz;
                        points.emplace_back(x, y, z);
                    }
                    // 2
                    {
                        double ux = p + 0.5;
                        double uy = q + 0.5;
                        double uz = rr;
                        double x = shift + s * ux;
                        double y = shift + s * uy;
                        double z = shift + s * uz;
                        points.emplace_back(x, y, z);
                    }
                    // 3
                    {
                        double ux = p + 0.5;
                        double uy = q;
                        double uz = rr + 0.5;
                        double x = shift + s * ux;
                        double y = shift + s * uy;
                        double z = shift + s * uz;
                        points.emplace_back(x, y, z);
                    }
                    // 4
                    {
                        double ux = p;
                        double uy = q + 0.5;
                        double uz = rr + 0.5;
                        double x = shift + s * ux;
                        double y = shift + s * uy;
                        double z = shift + s * uz;
                        points.emplace_back(x, y, z);
                    }
                }
            }
        }
    } else {
        // Cubic
        double dx = 1.0 / a;
        double dy = 1.0 / b;
        double dz = 1.0 / c;
        double rx = 1.0 / (2.0 * a);
        double ry = 1.0 / (2.0 * b);
        double rz = 1.0 / (2.0 * c);
        for (int i = 0; i < a; i++) {
            double x = rx + i * dx;
            for (int j = 0; j < b; j++) {
                double y = ry + j * dy;
                for (int ii = 0; ii < c; ii++) {
                    double z = rz + ii * dz;
                    points.emplace_back(x, y, z);
                }
            }
        }
    }
    // Output first n points
    for (long long i = 0; i < n; i++) {
        auto [x, y, z] = points[i];
        printf("%.10f %.10f %.10f\n", x, y, z);
    }
    return 0;
}