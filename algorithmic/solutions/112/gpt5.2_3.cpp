#include <bits/stdc++.h>
using namespace std;

static inline long double sqr(long double x){ return x*x; }

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    vector<array<long double,3>> pts;
    pts.reserve(n);

    const long double pi = acosl(-1.0L);
    const long double phi = (1.0L + sqrtl(5.0L)) / 2.0L;

    auto push_norm = [&](long double x, long double y, long double z){
        long double norm = sqrtl(x*x + y*y + z*z);
        if (norm > 0) { x /= norm; y /= norm; z /= norm; }
        pts.push_back({x,y,z});
    };

    auto gen_fibonacci = [&](){
        const long double golden_angle = pi * (3.0L - sqrtl(5.0L));
        for (int i = 0; i < n; i++) {
            long double t = ( (long double)i + 0.5L ) / (long double)n;
            long double y = 1.0L - 2.0L * t;
            long double r = sqrtl(max((long double)0.0L, 1.0L - y*y));
            long double theta = golden_angle * (long double)i;
            long double x = cosl(theta) * r;
            long double z = sinl(theta) * r;
            push_norm(x, y, z);
        }
    };

    if (n == 2) {
        pts.push_back({0.0L, 0.0L, 1.0L});
        pts.push_back({0.0L, 0.0L, -1.0L});
    } else if (n == 3) {
        push_norm(1.0L, 0.0L, 0.0L);
        push_norm(-0.5L, sqrtl(3.0L)/2.0L, 0.0L);
        push_norm(-0.5L, -sqrtl(3.0L)/2.0L, 0.0L);
    } else if (n == 4) {
        push_norm(1.0L, 1.0L, 1.0L);
        push_norm(1.0L, -1.0L, -1.0L);
        push_norm(-1.0L, 1.0L, -1.0L);
        push_norm(-1.0L, -1.0L, 1.0L);
    } else if (n == 6) {
        pts.push_back({1.0L, 0.0L, 0.0L});
        pts.push_back({-1.0L, 0.0L, 0.0L});
        pts.push_back({0.0L, 1.0L, 0.0L});
        pts.push_back({0.0L, -1.0L, 0.0L});
        pts.push_back({0.0L, 0.0L, 1.0L});
        pts.push_back({0.0L, 0.0L, -1.0L});
    } else if (n == 8) {
        long double inv = 1.0L / sqrtl(3.0L);
        for (int sx : {-1, 1})
            for (int sy : {-1, 1})
                for (int sz : {-1, 1})
                    pts.push_back({(long double)sx*inv, (long double)sy*inv, (long double)sz*inv});
    } else if (n == 12) {
        vector<array<long double,3>> v;
        v.reserve(12);
        for (int s1 : {-1, 1}) for (int s2 : {-1, 1}) v.push_back({0.0L, (long double)s1, (long double)s2*phi});
        for (int s1 : {-1, 1}) for (int s2 : {-1, 1}) v.push_back({(long double)s1, (long double)s2*phi, 0.0L});
        for (int s1 : {-1, 1}) for (int s2 : {-1, 1}) v.push_back({(long double)s1*phi, 0.0L, (long double)s2});
        for (auto &p : v) push_norm(p[0], p[1], p[2]);
    } else if (n == 20) {
        vector<array<long double,3>> v;
        v.reserve(20);
        for (int sx : {-1, 1}) for (int sy : {-1, 1}) for (int sz : {-1, 1})
            v.push_back({(long double)sx, (long double)sy, (long double)sz});
        for (int sy : {-1, 1}) for (int sz : {-1, 1})
            v.push_back({0.0L, (long double)sy*(1.0L/phi), (long double)sz*phi});
        for (int sx : {-1, 1}) for (int sy : {-1, 1})
            v.push_back({(long double)sx*(1.0L/phi), (long double)sy*phi, 0.0L});
        for (int sx : {-1, 1}) for (int sz : {-1, 1})
            v.push_back({(long double)sx*phi, 0.0L, (long double)sz*(1.0L/phi)});
        for (auto &p : v) push_norm(p[0], p[1], p[2]);
    } else {
        gen_fibonacci();
    }

    // Compute minimum pairwise distance
    long double minSq = numeric_limits<long double>::infinity();
    for (int i = 0; i < n; i++) {
        for (int j = i + 1; j < n; j++) {
            long double dx = pts[i][0] - pts[j][0];
            long double dy = pts[i][1] - pts[j][1];
            long double dz = pts[i][2] - pts[j][2];
            long double d2 = dx*dx + dy*dy + dz*dz;
            if (d2 < minSq) minSq = d2;
        }
    }
    long double minDist = sqrtl(minSq);

    cout.setf(std::ios::fmtflags(0), std::ios::floatfield);
    cout << setprecision(17) << (double)minDist << "\n";
    for (int i = 0; i < n; i++) {
        // ensure inside unit sphere
        long double x = pts[i][0], y = pts[i][1], z = pts[i][2];
        long double norm2 = x*x + y*y + z*z;
        if (norm2 > 1.0L) {
            long double norm = sqrtl(norm2);
            x /= norm; y /= norm; z /= norm;
        }
        cout << setprecision(17) << (double)x << " " << (double)y << " " << (double)z << "\n";
    }
    return 0;
}