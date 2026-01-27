#include <bits/stdc++.h>
using namespace std;

struct Vec3 {
    double x, y, z;
    Vec3() : x(0), y(0), z(0) {}
    Vec3(double X, double Y, double Z) : x(X), y(Y), z(Z) {}
    Vec3 operator+(const Vec3& o) const { return Vec3(x + o.x, y + o.y, z + o.z); }
    Vec3 operator-(const Vec3& o) const { return Vec3(x - o.x, y - o.y, z - o.z); }
    Vec3 operator*(double k) const { return Vec3(x * k, y * k, z * k); }
    Vec3& operator+=(const Vec3& o) { x += o.x; y += o.y; z += o.z; return *this; }
    Vec3& operator-=(const Vec3& o) { x -= o.x; y -= o.y; z -= o.z; return *this; }
    double dot(const Vec3& o) const { return x * o.x + y * o.y + z * o.z; }
    double norm2() const { return x * x + y * y + z * z; }
    double norm() const { return sqrt(norm2()); }
};

static inline Vec3 normalize(const Vec3& v) {
    double n = sqrt(v.x * v.x + v.y * v.y + v.z * v.z);
    if (n == 0) return Vec3(1, 0, 0);
    return Vec3(v.x / n, v.y / n, v.z / n);
}

vector<Vec3> special_points(int n) {
    vector<Vec3> P;
    if (n == 2) {
        P.emplace_back(0, 0, 1);
        P.emplace_back(0, 0, -1);
    } else if (n == 3) {
        double pi = acos(-1.0);
        for (int k = 0; k < 3; ++k) {
            double ang = 2.0 * pi * k / 3.0;
            P.emplace_back(cos(ang), sin(ang), 0.0);
        }
    } else if (n == 4) {
        double s = 1.0 / sqrt(3.0);
        P.emplace_back( s,  s,  s);
        P.emplace_back( s, -s, -s);
        P.emplace_back(-s,  s, -s);
        P.emplace_back(-s, -s,  s);
    } else if (n == 6) {
        P.emplace_back(1,0,0);
        P.emplace_back(-1,0,0);
        P.emplace_back(0,1,0);
        P.emplace_back(0,-1,0);
        P.emplace_back(0,0,1);
        P.emplace_back(0,0,-1);
    } else if (n == 8) {
        double s = 1.0 / sqrt(3.0);
        for (int sx = -1; sx <= 1; sx += 2)
            for (int sy = -1; sy <= 1; sy += 2)
                for (int sz = -1; sz <= 1; sz += 2)
                    P.emplace_back(sx * s, sy * s, sz * s);
    } else if (n == 12) {
        double phi = (1.0 + sqrt(5.0)) / 2.0;
        double s = 1.0 / sqrt(1.0 + phi * phi);
        double a = 1.0 * s, b = phi * s, z = 0.0;
        // (0, ±1, ±φ)
        P.emplace_back(0,  a,  b);
        P.emplace_back(0,  a, -b);
        P.emplace_back(0, -a,  b);
        P.emplace_back(0, -a, -b);
        // (±1, ±φ, 0)
        P.emplace_back( a,  b, 0);
        P.emplace_back( a, -b, 0);
        P.emplace_back(-a,  b, 0);
        P.emplace_back(-a, -b, 0);
        // (±φ, 0, ±1)
        P.emplace_back( b, 0,  a);
        P.emplace_back( b, 0, -a);
        P.emplace_back(-b, 0,  a);
        P.emplace_back(-b, 0, -a);
    }
    return P;
}

vector<Vec3> fibonacci_sphere(int n) {
    vector<Vec3> P(n);
    const double phi = (3.0 - sqrt(5.0)) * acos(-1.0); // golden angle
    for (int k = 0; k < n; ++k) {
        double z = 1.0 - (2.0 * k + 1.0) / n;
        double r = sqrt(max(0.0, 1.0 - z * z));
        double theta = k * phi;
        double x = cos(theta) * r;
        double y = sin(theta) * r;
        P[k] = Vec3(x, y, z);
    }
    return P;
}

void relax_points(vector<Vec3>& P) {
    int n = (int)P.size();
    if (n <= 1) return;

    int iters;
    double s0, s1;
    if (n <= 30) { iters = 400; s0 = 0.20; s1 = 0.01; }
    else if (n <= 100) { iters = 200; s0 = 0.15; s1 = 0.010; }
    else if (n <= 300) { iters = 120; s0 = 0.12; s1 = 0.008; }
    else if (n <= 700) { iters = 80; s0 = 0.10; s1 = 0.006; }
    else { iters = 50; s0 = 0.08; s1 = 0.004; }

    vector<Vec3> F(n), Ft(n);

    const double eps = 1e-12;
    for (int it = 0; it < iters; ++it) {
        // Zero forces
        for (int i = 0; i < n; ++i) F[i] = Vec3(0, 0, 0);

        // Pairwise repulsion (Coulomb-like)
        for (int i = 0; i < n; ++i) {
            const Vec3& pi = P[i];
            for (int j = i + 1; j < n; ++j) {
                Vec3 d = Vec3(pi.x - P[j].x, pi.y - P[j].y, pi.z - P[j].z);
                double r2 = d.x * d.x + d.y * d.y + d.z * d.z + eps;
                double invr = 1.0 / sqrt(r2);
                double invr3 = invr * invr * invr;
                Vec3 f = d * invr3;
                F[i] += f;
                F[j] -= f;
            }
        }

        // Tangential component and scaling
        double max_norm = 0.0;
        for (int i = 0; i < n; ++i) {
            double proj = F[i].dot(P[i]);
            Ft[i] = Vec3(F[i].x - proj * P[i].x, F[i].y - proj * P[i].y, F[i].z - proj * P[i].z);
            double nn = sqrt(Ft[i].x * Ft[i].x + Ft[i].y * Ft[i].y + Ft[i].z * Ft[i].z);
            if (nn > max_norm) max_norm = nn;
        }

        double t = (double)(it) / max(1, iters - 1);
        double s = s0 * (1.0 - t) + s1 * t;

        if (max_norm < 1e-30) break;

        double inv_max = s / max_norm;
        for (int i = 0; i < n; ++i) {
            P[i].x += Ft[i].x * inv_max;
            P[i].y += Ft[i].y * inv_max;
            P[i].z += Ft[i].z * inv_max;
            // Renormalize to unit sphere
            double invn = 1.0 / sqrt(P[i].x * P[i].x + P[i].y * P[i].y + P[i].z * P[i].z);
            P[i].x *= invn;
            P[i].y *= invn;
            P[i].z *= invn;
        }
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n;
    if (!(cin >> n)) return 0;

    vector<Vec3> P = special_points(n);
    if ((int)P.size() != n) {
        P = fibonacci_sphere(n);
    }

    relax_points(P);

    // Slight uniform shrink to ensure strictly inside the unit sphere due to rounding
    const double shrink = 1.0 - 1e-12;
    for (int i = 0; i < n; ++i) {
        P[i].x *= shrink;
        P[i].y *= shrink;
        P[i].z *= shrink;
    }

    // Compute minimum pairwise distance
    double min_d2 = 1e300;
    for (int i = 0; i < n; ++i) {
        for (int j = i + 1; j < n; ++j) {
            double dx = P[i].x - P[j].x;
            double dy = P[i].y - P[j].y;
            double dz = P[i].z - P[j].z;
            double d2 = dx * dx + dy * dy + dz * dz;
            if (d2 < min_d2) min_d2 = d2;
        }
    }
    double min_dist = sqrt(min_d2);

    cout.setf(std::ios::fixed); 
    cout << setprecision(15) << min_dist << "\n";
    for (int i = 0; i < n; ++i) {
        cout << setprecision(15) << P[i].x << " " << P[i].y << " " << P[i].z << "\n";
    }
    return 0;
}