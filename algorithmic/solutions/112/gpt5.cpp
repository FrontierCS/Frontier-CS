#include <bits/stdc++.h>
using namespace std;

struct Vec {
    double x, y, z;
    Vec() : x(0), y(0), z(0) {}
    Vec(double x_, double y_, double z_) : x(x_), y(y_), z(z_) {}
    Vec operator+(const Vec& o) const { return Vec(x + o.x, y + o.y, z + o.z); }
    Vec operator-(const Vec& o) const { return Vec(x - o.x, y - o.y, z - o.z); }
    Vec operator*(double k) const { return Vec(x * k, y * k, z * k); }
    Vec& operator+=(const Vec& o) { x += o.x; y += o.y; z += o.z; return *this; }
    Vec& operator-=(const Vec& o) { x -= o.x; y -= o.y; z -= o.z; return *this; }
};

static inline double dot(const Vec& a, const Vec& b) {
    return a.x * b.x + a.y * b.y + a.z * b.z;
}
static inline double norm2(const Vec& a) {
    return dot(a, a);
}
static inline double norm(const Vec& a) {
    return sqrt(norm2(a));
}
static inline Vec normalize(const Vec& a) {
    double n = norm(a);
    if (n == 0) return a;
    return a * (1.0 / n);
}

vector<Vec> special_points(int n) {
    vector<Vec> p;
    if (n == 2) {
        p.push_back(Vec(0, 0, 1));
        p.push_back(Vec(0, 0, -1));
    } else if (n == 3) {
        for (int k = 0; k < 3; ++k) {
            double ang = 2.0 * M_PI * k / 3.0;
            p.push_back(Vec(cos(ang), sin(ang), 0.0));
        }
    } else if (n == 4) {
        double s = 1.0 / sqrt(3.0);
        p.push_back(Vec( s,  s,  s));
        p.push_back(Vec( s, -s, -s));
        p.push_back(Vec(-s,  s, -s));
        p.push_back(Vec(-s, -s,  s));
    } else if (n == 6) {
        p.push_back(Vec(1, 0, 0));
        p.push_back(Vec(-1, 0, 0));
        p.push_back(Vec(0, 1, 0));
        p.push_back(Vec(0, -1, 0));
        p.push_back(Vec(0, 0, 1));
        p.push_back(Vec(0, 0, -1));
    } else if (n == 8) {
        double s = 1.0 / sqrt(3.0);
        int signs[2] = { -1, 1 };
        for (int a : signs) for (int b : signs) for (int c : signs) {
            p.push_back(Vec(a * s, b * s, c * s));
        }
    } else if (n == 12) {
        double t = (1.0 + sqrt(5.0)) * 0.5;
        double l = sqrt(1.0 + t * t);
        double s = 1.0 / l;
        // (0, ±1, ±t)
        for (int i : { -1, 1 }) for (int j : { -1, 1 })
            p.push_back(Vec(0.0, i * 1.0 * s, j * t * s));
        // (±1, ±t, 0)
        for (int i : { -1, 1 }) for (int j : { -1, 1 })
            p.push_back(Vec(i * 1.0 * s, j * t * s, 0.0));
        // (±t, 0, ±1)
        for (int i : { -1, 1 }) for (int j : { -1, 1 })
            p.push_back(Vec(i * t * s, 0.0, j * 1.0 * s));
    }
    return p;
}

vector<Vec> fibonacci_sphere(int n) {
    vector<Vec> p(n);
    const double phi = (1.0 + sqrt(5.0)) * 0.5;
    const double ga = 2.0 * M_PI * (1.0 - 1.0 / phi); // golden angle
    for (int i = 0; i < n; ++i) {
        double z = 1.0 - (2.0 * (i + 0.5)) / n;
        double r = sqrt(max(0.0, 1.0 - z * z));
        double theta = ga * i;
        double x = cos(theta) * r;
        double y = sin(theta) * r;
        p[i] = Vec(x, y, z);
    }
    return p;
}

void repulsion_optimize(vector<Vec>& p) {
    int n = (int)p.size();
    if (n <= 12) return; // special configurations already good
    // Simple repulsion iterations
    int I = min(20, (int)(3000.0 / n) + 8); // more iterations for smaller n
    double step_base = 0.2 / n;
    vector<Vec> force(n);
    for (int it = 0; it < I; ++it) {
        fill(force.begin(), force.end(), Vec(0, 0, 0));
        for (int i = 0; i < n; ++i) {
            const Vec& pi = p[i];
            for (int j = i + 1; j < n; ++j) {
                Vec d = Vec(pi.x - p[j].x, pi.y - p[j].y, pi.z - p[j].z);
                double d2 = d.x * d.x + d.y * d.y + d.z * d.z + 1e-12;
                double inv = 1.0 / d2; // 1/r^2 repulsion
                Vec f = d * inv;
                force[i] += f;
                force[j] -= f;
            }
        }
        double step = step_base * pow(0.97, it);
        for (int i = 0; i < n; ++i) {
            // project to tangent plane to keep on sphere
            Vec Fi = force[i];
            double radial = dot(Fi, p[i]);
            Fi -= p[i] * radial;
            double len = norm(Fi);
            double maxmove = 0.1;
            double factor = (len > 0 ? min(step, maxmove / len) : 0.0);
            p[i] = normalize(p[i] + Fi * factor);
        }
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n;
    if (!(cin >> n)) return 0;

    vector<Vec> pts = special_points(n);
    if ((int)pts.size() != n) {
        pts = fibonacci_sphere(n);
        repulsion_optimize(pts);
    }

    // Slightly shrink to ensure strictly inside or on unit sphere within tolerance
    const double shrink = 1.0 - 1e-12;
    for (auto& v : pts) {
        double r = norm(v);
        if (r > 0) {
            double s = shrink / r;
            v.x *= s; v.y *= s; v.z *= s;
        }
    }

    // Compute minimum pairwise distance
    double minD2 = 1e100;
    for (int i = 0; i < n; ++i) {
        for (int j = i + 1; j < n; ++j) {
            double dx = pts[i].x - pts[j].x;
            double dy = pts[i].y - pts[j].y;
            double dz = pts[i].z - pts[j].z;
            double d2 = dx*dx + dy*dy + dz*dz;
            if (d2 < minD2) minD2 = d2;
        }
    }
    double minDist = (minD2 < 0 ? 0.0 : sqrt(minD2));

    cout.setf(std::ios::fixed);
    cout << setprecision(12) << minDist << "\n";
    for (int i = 0; i < n; ++i) {
        cout << setprecision(12) << pts[i].x << " " << pts[i].y << " " << pts[i].z << "\n";
    }

    return 0;
}