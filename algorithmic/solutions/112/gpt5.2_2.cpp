#include <bits/stdc++.h>
using namespace std;

struct Vec3 {
    double x, y, z;
    Vec3() : x(0), y(0), z(0) {}
    Vec3(double x_, double y_, double z_) : x(x_), y(y_), z(z_) {}
    Vec3 operator + (const Vec3& o) const { return Vec3(x + o.x, y + o.y, z + o.z); }
    Vec3 operator - (const Vec3& o) const { return Vec3(x - o.x, y - o.y, z - o.z); }
    Vec3 operator * (double k) const { return Vec3(x * k, y * k, z * k); }
    Vec3 operator / (double k) const { return Vec3(x / k, y / k, z / k); }
    Vec3& operator += (const Vec3& o) { x += o.x; y += o.y; z += o.z; return *this; }
    Vec3& operator -= (const Vec3& o) { x -= o.x; y -= o.y; z -= o.z; return *this; }
    Vec3& operator *= (double k) { x *= k; y *= k; z *= k; return *this; }
};

static inline double dot(const Vec3& a, const Vec3& b) { return a.x*b.x + a.y*b.y + a.z*b.z; }
static inline Vec3 crossp(const Vec3& a, const Vec3& b) {
    return Vec3(a.y*b.z - a.z*b.y, a.z*b.x - a.x*b.z, a.x*b.y - a.y*b.x);
}
static inline double norm2(const Vec3& a) { return dot(a,a); }
static inline double norm(const Vec3& a) { return sqrt(norm2(a)); }

static inline Vec3 normalized(const Vec3& a) {
    double l = norm(a);
    if (l <= 0) return Vec3(1,0,0);
    return a / l;
}

static inline void normalize_inplace(Vec3& a) {
    double l = norm(a);
    if (l <= 0) { a = Vec3(1,0,0); return; }
    a.x /= l; a.y /= l; a.z /= l;
}

static inline void clamp_inside_unit(Vec3& a) {
    double r2 = norm2(a);
    if (r2 > 1.0) {
        double r = sqrt(r2);
        double s = (1.0 - 1e-12) / r;
        a *= s;
    }
}

static double minDist2(const vector<Vec3>& p) {
    int n = (int)p.size();
    double best = numeric_limits<double>::infinity();
    for (int i = 0; i < n; i++) {
        const Vec3 &pi = p[i];
        for (int j = i+1; j < n; j++) {
            Vec3 d = pi - p[j];
            double d2 = d.x*d.x + d.y*d.y + d.z*d.z;
            if (d2 < best) best = d2;
        }
    }
    return best;
}

static vector<Vec3> hardcoded(int n) {
    vector<Vec3> p;
    if (n == 2) {
        p = {Vec3(0,0,1), Vec3(0,0,-1)};
    } else if (n == 3) {
        double s3 = sqrt(3.0);
        p = {Vec3(1,0,0), Vec3(-0.5, s3/2.0, 0), Vec3(-0.5, -s3/2.0, 0)};
        for (auto &v: p) clamp_inside_unit(v);
    } else if (n == 4) {
        double inv = 1.0 / sqrt(3.0);
        p = {Vec3( 1, 1, 1), Vec3(-1,-1, 1), Vec3(-1, 1,-1), Vec3( 1,-1,-1)};
        for (auto &v: p) v *= inv;
    }
    return p;
}

static vector<Vec3> fibonacciSphere(int n) {
    vector<Vec3> p(n);
    const double ga = M_PI * (3.0 - sqrt(5.0));
    for (int i = 0; i < n; i++) {
        double z = 1.0 - 2.0 * (i + 0.5) / n;
        double r = sqrt(max(0.0, 1.0 - z*z));
        double phi = ga * i;
        double x = r * cos(phi);
        double y = r * sin(phi);
        p[i] = Vec3(x,y,z);
        normalize_inplace(p[i]);
    }
    return p;
}

static Vec3 randomUnitVec(mt19937_64& rng) {
    uniform_real_distribution<double> U01(0.0, 1.0);
    double u = U01(rng) * 2.0 - 1.0;
    double th = U01(rng) * 2.0 * M_PI;
    double r = sqrt(max(0.0, 1.0 - u*u));
    return Vec3(r*cos(th), r*sin(th), u);
}

static void relaxOnSphere(vector<Vec3>& p, int iters, double step0, double step1) {
    int n = (int)p.size();
    vector<Vec3> f(n);
    const double eps = 1e-12;
    for (int it = 0; it < iters; it++) {
        double t = (iters <= 1 ? 1.0 : (double)it / (double)(iters - 1));
        double step = step0 * (1.0 - t) + step1 * t;

        for (int i = 0; i < n; i++) f[i] = Vec3(0,0,0);

        for (int i = 0; i < n; i++) {
            const Vec3& pi = p[i];
            for (int j = i+1; j < n; j++) {
                Vec3 d = pi - p[j];
                double d2 = d.x*d.x + d.y*d.y + d.z*d.z + eps;
                double inv = 1.0 / d2; // ~ 1/dist^2, force magnitude ~ 1/dist
                Vec3 g = d * inv;
                f[i] += g;
                f[j] -= g;
            }
        }

        for (int i = 0; i < n; i++) {
            Vec3 fi = f[i];
            // Project to tangent plane
            double dp = dot(fi, p[i]);
            fi -= p[i] * dp;
            double l2 = norm2(fi);
            if (l2 > 1e-24) {
                fi *= (1.0 / sqrt(l2));
                p[i] += fi * step;
                normalize_inplace(p[i]);
            }
        }
    }
}

static vector<Vec3> bestSphere(int n) {
    if (n <= 4) return hardcoded(n);

    int starts = 1, iters = 0;
    if (n <= 12) { starts = 20; iters = 900; }
    else if (n <= 30) { starts = 12; iters = 650; }
    else if (n <= 60) { starts = 8; iters = 450; }
    else if (n <= 100) { starts = 4; iters = 280; }
    else { starts = 1; iters = 0; }

    mt19937_64 rng(1234567ULL);

    vector<Vec3> bestP;
    double bestD2 = -1.0;

    for (int s = 0; s < starts; s++) {
        vector<Vec3> p;
        if (s == 0) p = fibonacciSphere(n);
        else {
            p.resize(n);
            for (int i = 0; i < n; i++) p[i] = randomUnitVec(rng);
        }

        if (iters > 0) {
            double step0 = 0.12;
            double step1 = 0.02;
            relaxOnSphere(p, iters, step0, step1);
        }

        for (auto &v : p) clamp_inside_unit(v);

        double d2 = minDist2(p);
        if (d2 > bestD2) {
            bestD2 = d2;
            bestP = std::move(p);
        }
    }

    return bestP;
}

struct Ball {
    Vec3 c;
    double r;
};

static inline bool containsBall(const Ball& b, const Vec3& p) {
    double d2 = norm2(p - b.c);
    return d2 <= b.r*b.r + 1e-9;
}

static Ball ballFrom1(const Vec3& a) {
    return Ball{a, 0.0};
}

static Ball ballFrom2(const Vec3& a, const Vec3& b) {
    Vec3 c = (a + b) * 0.5;
    double r = norm(a - c);
    return Ball{c, r};
}

static Ball ballFrom3(const Vec3& a, const Vec3& b, const Vec3& c) {
    Vec3 ab = b - a, ac = c - a;
    Vec3 cr = crossp(ab, ac);
    double denom = 2.0 * norm2(cr);
    if (denom < 1e-18) {
        // Collinear: take ball from farthest pair
        double dab = norm2(b - a);
        double dac = norm2(c - a);
        double dbc = norm2(c - b);
        if (dab >= dac && dab >= dbc) return ballFrom2(a, b);
        if (dac >= dab && dac >= dbc) return ballFrom2(a, c);
        return ballFrom2(b, c);
    }

    double ab2 = norm2(ab);
    double ac2 = norm2(ac);

    Vec3 term1 = crossp(cr, ab) * ac2;
    Vec3 term2 = crossp(ac, cr) * ab2;
    Vec3 center = a + (term1 + term2) / denom;
    double r = norm(center - a);
    return Ball{center, r};
}

static bool solve3x3(double A[3][3], double B[3], double X[3]) {
    // Gaussian elimination with partial pivoting
    int piv[3] = {0,1,2};

    for (int col = 0; col < 3; col++) {
        int best = col;
        double bestv = fabs(A[col][col]);
        for (int row = col+1; row < 3; row++) {
            double v = fabs(A[row][col]);
            if (v > bestv) { bestv = v; best = row; }
        }
        if (bestv < 1e-18) return false;
        if (best != col) {
            for (int k = col; k < 3; k++) swap(A[col][k], A[best][k]);
            swap(B[col], B[best]);
        }
        double invPivot = 1.0 / A[col][col];
        for (int row = col+1; row < 3; row++) {
            double factor = A[row][col] * invPivot;
            if (factor == 0.0) continue;
            for (int k = col; k < 3; k++) A[row][k] -= factor * A[col][k];
            B[row] -= factor * B[col];
        }
    }
    for (int i = 2; i >= 0; i--) {
        double sum = B[i];
        for (int k = i+1; k < 3; k++) sum -= A[i][k] * X[k];
        if (fabs(A[i][i]) < 1e-18) return false;
        X[i] = sum / A[i][i];
    }
    return true;
}

static Ball ballFrom4_exact(const Vec3& p1, const Vec3& p2, const Vec3& p3, const Vec3& p4, bool &ok) {
    double A[3][3];
    double B[3];
    Vec3 q[3] = {p2 - p1, p3 - p1, p4 - p1};
    Vec3 ps[3] = {p2, p3, p4};

    for (int i = 0; i < 3; i++) {
        A[i][0] = 2.0 * q[i].x;
        A[i][1] = 2.0 * q[i].y;
        A[i][2] = 2.0 * q[i].z;
        B[i] = norm2(ps[i]) - norm2(p1);
    }

    double X[3] = {0,0,0};
    double Acpy[3][3]; double Bcpy[3];
    for (int i = 0; i < 3; i++) {
        Bcpy[i] = B[i];
        for (int j = 0; j < 3; j++) Acpy[i][j] = A[i][j];
    }
    if (!solve3x3(Acpy, Bcpy, X)) {
        ok = false;
        return Ball{Vec3(0,0,0), numeric_limits<double>::infinity()};
    }
    ok = true;
    Vec3 center(X[0], X[1], X[2]);
    double r = norm(center - p1);
    return Ball{center, r};
}

static Ball ballFrom4(const Vec3& a, const Vec3& b, const Vec3& c, const Vec3& d) {
    bool ok = false;
    Ball s = ballFrom4_exact(a,b,c,d,ok);
    if (ok) return s;

    // Fallback: minimal ball containing these 4 points by checking subsets
    Vec3 pts[4] = {a,b,c,d};
    Ball best{Vec3(0,0,0), numeric_limits<double>::infinity()};

    // pairs
    for (int i = 0; i < 4; i++) for (int j = i+1; j < 4; j++) {
        Ball bb = ballFrom2(pts[i], pts[j]);
        bool good = true;
        for (int k = 0; k < 4; k++) if (!containsBall(bb, pts[k])) { good = false; break; }
        if (good && bb.r < best.r) best = bb;
    }
    // triples
    for (int i = 0; i < 4; i++) for (int j = i+1; j < 4; j++) for (int k = j+1; k < 4; k++) {
        Ball bb = ballFrom3(pts[i], pts[j], pts[k]);
        bool good = true;
        for (int t = 0; t < 4; t++) if (!containsBall(bb, pts[t])) { good = false; break; }
        if (good && bb.r < best.r) best = bb;
    }
    if (isfinite(best.r)) return best;

    // last resort: huge
    return Ball{Vec3(0,0,0), 1e300};
}

static Ball minEnclosingBall(vector<Vec3> p) {
    mt19937_64 rng(987654321ULL);
    shuffle(p.begin(), p.end(), rng);

    Ball b = ballFrom1(p[0]);
    int n = (int)p.size();
    for (int i = 0; i < n; i++) {
        if (containsBall(b, p[i])) continue;
        b = ballFrom1(p[i]);
        for (int j = 0; j < i; j++) {
            if (containsBall(b, p[j])) continue;
            b = ballFrom2(p[i], p[j]);
            for (int k = 0; k < j; k++) {
                if (containsBall(b, p[k])) continue;
                b = ballFrom3(p[i], p[j], p[k]);
                for (int l = 0; l < k; l++) {
                    if (containsBall(b, p[l])) continue;
                    b = ballFrom4(p[i], p[j], p[k], p[l]);
                }
            }
        }
    }
    return b;
}

struct CandPoint {
    double r2;
    Vec3 p;
};

static vector<Vec3> generateFCC(int n, const Vec3& shift) {
    const double a = sqrt(2.0); // cubic parameter so nearest-neighbor distance = a/sqrt(2)=1
    // estimate radius needed in unscaled space
    const double ptsPerVol = 4.0 / (a*a*a); // 4 points per cell volume
    const double approxCoeff = ptsPerVol * (4.0/3.0) * M_PI; // ~ 5.923
    double Rest = cbrt((double)n / approxCoeff) + 2.5;
    int K = (int)ceil(Rest / a) + 2;
    K = max(K, 4);

    vector<CandPoint> cand;
    cand.reserve((size_t)4 * (2*K+1) * (2*K+1) * (2*K+1));

    for (int i = -K; i <= K; i++) for (int j = -K; j <= K; j++) for (int k = -K; k <= K; k++) {
        // 4 offsets
        Vec3 p0(i*a, j*a, k*a); p0 += shift;
        Vec3 p1(i*a, (j+0.5)*a, (k+0.5)*a); p1 += shift;
        Vec3 p2((i+0.5)*a, j*a, (k+0.5)*a); p2 += shift;
        Vec3 p3((i+0.5)*a, (j+0.5)*a, k*a); p3 += shift;

        cand.push_back({norm2(p0), p0});
        cand.push_back({norm2(p1), p1});
        cand.push_back({norm2(p2), p2});
        cand.push_back({norm2(p3), p3});
    }

    if ((int)cand.size() < n) {
        // Should not happen with chosen K, but fallback: increase K a bit.
        int extra = 3;
        for (int i = -(K+extra); i <= (K+extra); i++) for (int j = -(K+extra); j <= (K+extra); j++) for (int k = -(K+extra); k <= (K+extra); k++) {
            Vec3 p0(i*a, j*a, k*a); p0 += shift;
            Vec3 p1(i*a, (j+0.5)*a, (k+0.5)*a); p1 += shift;
            Vec3 p2((i+0.5)*a, j*a, (k+0.5)*a); p2 += shift;
            Vec3 p3((i+0.5)*a, (j+0.5)*a, k*a); p3 += shift;
            cand.push_back({norm2(p0), p0});
            cand.push_back({norm2(p1), p1});
            cand.push_back({norm2(p2), p2});
            cand.push_back({norm2(p3), p3});
        }
    }

    nth_element(cand.begin(), cand.begin() + n, cand.end(), [](const CandPoint& A, const CandPoint& B){
        return A.r2 < B.r2;
    });
    cand.resize(n);

    vector<Vec3> pts(n);
    for (int i = 0; i < n; i++) pts[i] = cand[i].p;

    Ball b = minEnclosingBall(pts);
    Vec3 center = b.c;
    double R = b.r;
    if (!(R > 0.0) || !isfinite(R)) {
        // fallback center at average
        Vec3 avg(0,0,0);
        for (auto &v: pts) avg += v;
        avg *= (1.0 / n);
        center = avg;
        double maxr2 = 0;
        for (auto &v: pts) maxr2 = max(maxr2, norm2(v - center));
        R = sqrt(maxr2);
    }

    double scale = (1.0 - 1e-10) / R;
    for (auto &v: pts) {
        v -= center;
        v *= scale;
        clamp_inside_unit(v);
    }
    return pts;
}

static vector<Vec3> bestFCC(int n) {
    const double a = sqrt(2.0);
    vector<Vec3> baseShifts = {
        Vec3(0,0,0),
        Vec3(0.5*a,0,0),
        Vec3(0,0.5*a,0),
        Vec3(0,0,0.5*a),
        Vec3(0.5*a,0.5*a,0),
        Vec3(0.5*a,0,0.5*a),
        Vec3(0,0.5*a,0.5*a),
        Vec3(0.5*a,0.5*a,0.5*a)
    };

    int trials = 8;
    if (n >= 800) trials = 4;
    else if (n >= 200) trials = 8;
    else trials = 12;

    mt19937_64 rng(246813579ULL);
    uniform_real_distribution<double> U(0.0, a);

    vector<Vec3> bestP;
    double bestD2 = -1.0;

    for (int t = 0; t < trials; t++) {
        Vec3 shift;
        if (t < (int)baseShifts.size()) shift = baseShifts[t];
        else shift = Vec3(U(rng), U(rng), U(rng));

        vector<Vec3> p = generateFCC(n, shift);
        double d2 = minDist2(p);
        if (d2 > bestD2) {
            bestD2 = d2;
            bestP = std::move(p);
        }
    }
    return bestP;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    vector<Vec3> ans;

    if (n <= 4) {
        ans = hardcoded(n);
    } else {
        vector<Vec3> sphere = bestSphere(n);
        vector<Vec3> fcc = bestFCC(n);

        double ds2 = minDist2(sphere);
        double df2 = minDist2(fcc);

        ans = (df2 > ds2 ? std::move(fcc) : std::move(sphere));
    }

    for (auto &v: ans) clamp_inside_unit(v);

    double md2 = minDist2(ans);
    double md = sqrt(max(0.0, md2));

    cout.setf(std::ios::fixed);
    cout << setprecision(15) << md << "\n";
    for (auto &v: ans) {
        cout << setprecision(15) << v.x << " " << v.y << " " << v.z << "\n";
    }
    return 0;
}