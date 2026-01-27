#include <bits/stdc++.h>
using namespace std;

struct Vec3 {
    double x, y, z;
    Vec3() : x(0), y(0), z(0) {}
    Vec3(double x_, double y_, double z_) : x(x_), y(y_), z(z_) {}
    Vec3 operator+(const Vec3& o) const { return Vec3(x + o.x, y + o.y, z + o.z); }
    Vec3 operator-(const Vec3& o) const { return Vec3(x - o.x, y - o.y, z - o.z); }
    Vec3 operator*(double s) const { return Vec3(x * s, y * s, z * s); }
    Vec3& operator+=(const Vec3& o) { x += o.x; y += o.y; z += o.z; return *this; }
};

static inline double dot(const Vec3& a, const Vec3& b) { return a.x*b.x + a.y*b.y + a.z*b.z; }
static inline double norm(const Vec3& a) { return sqrt(dot(a,a)); }
static inline Vec3 normalize(const Vec3& a) { double l = norm(a); if (l == 0) return a; return a * (1.0 / l); }

vector<Vec3> fibonacci_sphere(int n) {
    vector<Vec3> pts(n);
    const double phi = (3.0 - sqrt(5.0)) * M_PI; // golden angle
    for (int i = 0; i < n; ++i) {
        double z = 1.0 - 2.0 * (i + 0.5) / n;
        double r = sqrt(max(0.0, 1.0 - z*z));
        double theta = phi * i;
        double x = r * cos(theta);
        double y = r * sin(theta);
        pts[i] = Vec3(x, y, z);
        pts[i] = normalize(pts[i]);
    }
    return pts;
}

vector<Vec3> initial_points(int n) {
    vector<Vec3> pts;
    if (n == 2) {
        pts = { Vec3(0,0,1), Vec3(0,0,-1) };
    } else if (n == 3) {
        pts.resize(3);
        for (int i = 0; i < 3; ++i) {
            double ang = 2.0 * M_PI * i / 3.0;
            pts[i] = Vec3(cos(ang), sin(ang), 0.0);
        }
    } else if (n == 4) {
        double s = 1.0 / sqrt(3.0);
        pts = {
            Vec3( s,  s,  s),
            Vec3( s, -s, -s),
            Vec3(-s,  s, -s),
            Vec3(-s, -s,  s)
        };
    } else if (n == 6) {
        pts = {
            Vec3(1,0,0), Vec3(-1,0,0),
            Vec3(0,1,0), Vec3(0,-1,0),
            Vec3(0,0,1), Vec3(0,0,-1)
        };
    } else {
        pts = fibonacci_sphere(n);
    }
    // Normalize to be safe
    for (auto& p : pts) p = normalize(p);
    return pts;
}

void refine_points(vector<Vec3>& pts) {
    int n = (int)pts.size();
    if (n <= 1) return;

    int T;
    if (n <= 20) T = 300;
    else if (n <= 50) T = 200;
    else if (n <= 200) T = 100;
    else if (n <= 600) T = 50;
    else T = 20;

    double s0 = 0.8 / sqrt((double)n); // base step
    vector<Vec3> F(n);

    for (int iter = 0; iter < T; ++iter) {
        for (int i = 0; i < n; ++i) F[i] = Vec3(0,0,0);

        for (int i = 0; i < n; ++i) {
            const Vec3& a = pts[i];
            for (int j = i+1; j < n; ++j) {
                const Vec3& b = pts[j];
                Vec3 d = a - b;
                double d2 = dot(d, d) + 1e-12;
                double inv = 1.0 / d2; // 1/r^2 repulsion
                Vec3 f = d * inv;
                F[i] += f;
                F[j] += f * (-1.0);
            }
        }

        double s = s0 * (1.0 - 0.5 * (double)iter / (double)T);
        for (int i = 0; i < n; ++i) {
            // Project force onto tangent plane at point
            double proj = dot(F[i], pts[i]);
            Vec3 Ft = F[i] - pts[i] * proj;
            double m = norm(Ft);
            if (m > 1e-18) {
                Vec3 dir = Ft * (1.0 / m);
                Vec3 pnew = pts[i] + dir * s;
                pts[i] = normalize(pnew);
            } else {
                // No change
            }
        }
    }
}

double compute_min_dist(const vector<Vec3>& pts) {
    int n = (int)pts.size();
    double minD2 = numeric_limits<double>::infinity();
    for (int i = 0; i < n; ++i) {
        for (int j = i+1; j < n; ++j) {
            Vec3 d = pts[i] - pts[j];
            double d2 = dot(d, d);
            if (d2 < minD2) minD2 = d2;
        }
    }
    if (!isfinite(minD2)) return 0.0;
    return sqrt(minD2);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;
    vector<Vec3> pts = initial_points(n);
    refine_points(pts);

    // Final normalization to guarantee on sphere
    for (auto& p : pts) p = normalize(p);

    double min_dist = compute_min_dist(pts);

    cout.setf(std::ios::fixed);
    cout << setprecision(10) << min_dist << "\n";
    for (auto& p : pts) {
        cout << setprecision(10) << p.x << " " << p.y << " " << p.z << "\n";
    }
    return 0;
}