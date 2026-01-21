#include <bits/stdc++.h>
using namespace std;

struct Vec {
    double x, y, z;
};

static inline double dist2d(const Vec& a, const Vec& b) {
    double dx = a.x - b.x, dy = a.y - b.y, dz = a.z - b.z;
    return dx*dx + dy*dy + dz*dz;
}

static inline void normalize(Vec& p) {
    double len2 = p.x*p.x + p.y*p.y + p.z*p.z;
    if (len2 <= 0.0) return;
    double inv = 1.0 / sqrt(len2);
    p.x *= inv; p.y *= inv; p.z *= inv;
}

static inline void fixSmall(Vec& p) {
    if (fabs(p.x) < 1e-15) p.x = 0;
    if (fabs(p.y) < 1e-15) p.y = 0;
    if (fabs(p.z) < 1e-15) p.z = 0;
}

static vector<Vec> gen_special(int n) {
    const double PI = acos(-1.0);
    vector<Vec> pts;

    auto add = [&](double x, double y, double z) {
        Vec p{x,y,z};
        normalize(p);
        pts.push_back(p);
    };

    if (n == 2) {
        pts.push_back({0,0,1});
        pts.push_back({0,0,-1});
        return pts;
    }
    if (n == 3) {
        add(1,0,0);
        add(-0.5, sqrt(3.0)/2.0, 0);
        add(-0.5, -sqrt(3.0)/2.0, 0);
        return pts;
    }
    if (n == 4) {
        double s = 1.0 / sqrt(3.0);
        pts.push_back({ s, s, s});
        pts.push_back({ s,-s,-s});
        pts.push_back({-s, s,-s});
        pts.push_back({-s,-s, s});
        return pts;
    }
    if (n == 5) { // triangular dipyramid
        pts.push_back({0,0,1});
        pts.push_back({0,0,-1});
        for (int k = 0; k < 3; k++) {
            double ang = 2.0 * PI * k / 3.0;
            pts.push_back({cos(ang), sin(ang), 0});
        }
        return pts;
    }
    if (n == 6) { // octahedron
        pts.push_back({1,0,0});
        pts.push_back({-1,0,0});
        pts.push_back({0,1,0});
        pts.push_back({0,-1,0});
        pts.push_back({0,0,1});
        pts.push_back({0,0,-1});
        return pts;
    }
    if (n == 7) { // pentagonal dipyramid
        pts.push_back({0,0,1});
        pts.push_back({0,0,-1});
        for (int k = 0; k < 5; k++) {
            double ang = 2.0 * PI * k / 5.0;
            pts.push_back({cos(ang), sin(ang), 0});
        }
        return pts;
    }
    if (n == 8) { // square antiprism (near-optimal)
        double rt2 = sqrt(2.0);
        double h2 = rt2 / (4.0 + rt2);
        double h = sqrt(h2);
        double r = sqrt(max(0.0, 1.0 - h2));

        // top square (axis-aligned)
        pts.push_back({ r, 0, h});
        pts.push_back({ 0, r, h});
        pts.push_back({-r, 0, h});
        pts.push_back({ 0,-r, h});

        // bottom square (rotated by 45 degrees)
        double c = r / rt2;
        pts.push_back({ c, c,-h});
        pts.push_back({-c, c,-h});
        pts.push_back({-c,-c,-h});
        pts.push_back({ c,-c,-h});

        for (auto &p : pts) normalize(p);
        return pts;
    }
    if (n == 12) { // icosahedron
        double phi = (1.0 + sqrt(5.0)) / 2.0;
        vector<Vec> v;
        v.push_back({0, 1,  phi});
        v.push_back({0,-1,  phi});
        v.push_back({0, 1, -phi});
        v.push_back({0,-1, -phi});

        v.push_back({ 1,  phi, 0});
        v.push_back({-1,  phi, 0});
        v.push_back({ 1, -phi, 0});
        v.push_back({-1, -phi, 0});

        v.push_back({ phi, 0,  1});
        v.push_back({ phi, 0, -1});
        v.push_back({-phi, 0,  1});
        v.push_back({-phi, 0, -1});

        for (auto &p : v) normalize(p);
        return v;
    }

    return {};
}

static vector<Vec> gen_candidates(int baseM) {
    const double PI = acos(-1.0);
    vector<Vec> cand;
    cand.reserve(baseM + 64);

    auto push = [&](Vec p) {
        normalize(p);
        cand.push_back(p);
    };

    // Add some symmetric exact points
    push({0,0,1});
    push({0,0,-1});
    push({1,0,0});
    push({-1,0,0});
    push({0,1,0});
    push({0,-1,0});

    // Cube vertices
    for (int sx : {-1, 1})
        for (int sy : {-1, 1})
            for (int sz : {-1, 1})
                push({(double)sx, (double)sy, (double)sz});

    // Icosahedron vertices
    {
        double phi = (1.0 + sqrt(5.0)) / 2.0;
        vector<Vec> v;
        v.push_back({0, 1,  phi});
        v.push_back({0,-1,  phi});
        v.push_back({0, 1, -phi});
        v.push_back({0,-1, -phi});

        v.push_back({ 1,  phi, 0});
        v.push_back({-1,  phi, 0});
        v.push_back({ 1, -phi, 0});
        v.push_back({-1, -phi, 0});

        v.push_back({ phi, 0,  1});
        v.push_back({ phi, 0, -1});
        v.push_back({-phi, 0,  1});
        v.push_back({-phi, 0, -1});
        for (auto &p : v) push(p);
    }

    // Fibonacci sphere points
    double golden_angle = PI * (3.0 - sqrt(5.0));
    for (int i = 0; i < baseM; i++) {
        double z = 1.0 - 2.0 * (i + 0.5) / baseM;
        double r = sqrt(max(0.0, 1.0 - z*z));
        double theta = golden_angle * i;
        Vec p{r * cos(theta), r * sin(theta), z};
        normalize(p);
        cand.push_back(p);
    }
    return cand;
}

static vector<Vec> gen_fps(int n) {
    int baseM = max(8000, n * 20);
    vector<Vec> cand = gen_candidates(baseM);
    int C = (int)cand.size();

    vector<char> used(C, 0);
    vector<double> best(C, 1e100);

    uint64_t seed = 1469598103934665603ULL ^ (uint64_t)n * 1099511628211ULL;
    seed ^= seed >> 33; seed *= 0xff51afd7ed558ccdULL;
    seed ^= seed >> 33; seed *= 0xc4ceb9fe1a85ec53ULL;
    seed ^= seed >> 33;
    int first = (int)(seed % (uint64_t)C);

    vector<Vec> pts;
    pts.reserve(n);

    used[first] = 1;
    pts.push_back(cand[first]);

    for (int i = 0; i < C; i++) best[i] = dist2d(cand[i], cand[first]);
    best[first] = 0.0;

    for (int k = 1; k < n; k++) {
        int idx = -1;
        double mx = -1.0;
        for (int i = 0; i < C; i++) {
            if (!used[i] && best[i] > mx) {
                mx = best[i];
                idx = i;
            }
        }
        if (idx < 0) break;

        used[idx] = 1;
        pts.push_back(cand[idx]);

        for (int i = 0; i < C; i++) {
            if (used[i]) continue;
            double d2 = dist2d(cand[i], cand[idx]);
            if (d2 < best[i]) best[i] = d2;
        }
    }

    // If somehow short (shouldn't), pad with Fibonacci points
    if ((int)pts.size() < n) {
        const double PI = acos(-1.0);
        double golden_angle = PI * (3.0 - sqrt(5.0));
        for (int i = 0; (int)pts.size() < n; i++) {
            double z = 1.0 - 2.0 * (i + 0.5) / (n * 10 + 1);
            double r = sqrt(max(0.0, 1.0 - z*z));
            double theta = golden_angle * i;
            Vec p{r * cos(theta), r * sin(theta), z};
            normalize(p);
            pts.push_back(p);
        }
    }

    return pts;
}

static long double compute_min_dist(const vector<Vec>& pts) {
    int n = (int)pts.size();
    long double best2 = numeric_limits<long double>::infinity();
    for (int i = 0; i < n; i++) {
        for (int j = i + 1; j < n; j++) {
            long double dx = (long double)pts[i].x - pts[j].x;
            long double dy = (long double)pts[i].y - pts[j].y;
            long double dz = (long double)pts[i].z - pts[j].z;
            long double d2 = dx*dx + dy*dy + dz*dz;
            if (d2 < best2) best2 = d2;
        }
    }
    if (!isfinite((double)best2)) return 0;
    if (best2 < 0) best2 = 0;
    return sqrtl(best2);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    cin >> n;

    vector<Vec> pts = gen_special(n);
    if ((int)pts.size() != n) pts = gen_fps(n);

    for (auto &p : pts) {
        normalize(p);
        fixSmall(p);
    }

    long double minDist = compute_min_dist(pts);

    cout.setf(std::ios::fixed);
    cout << setprecision(17) << (double)minDist << "\n";
    for (auto &p : pts) {
        cout << setprecision(17) << p.x << " " << p.y << " " << p.z << "\n";
    }
    return 0;
}