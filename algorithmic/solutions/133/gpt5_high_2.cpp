#include <bits/stdc++.h>
using namespace std;

struct FastScanner {
    static const int S = 1 << 20;
    int idx = 0, size = 0;
    char buf[S];
    inline char getChar() {
        if (idx >= size) {
            size = (int)fread(buf, 1, S, stdin);
            idx = 0;
            if (size == 0) return EOF;
        }
        return buf[idx++];
    }
    template<typename T>
    bool readInt(T &out) {
        char c; T sign = 1; T x = 0;
        c = getChar();
        if (c == EOF) return false;
        while (c != '-' && (c < '0' || c > '9')) {
            c = getChar();
            if (c == EOF) return false;
        }
        if (c == '-') { sign = -1; c = getChar(); }
        for (; c >= '0' && c <= '9'; c = getChar()) x = x * 10 + (c - '0');
        out = x * sign;
        return true;
    }
    bool readDouble(double &out) {
        char c = getChar();
        if (c == EOF) return false;
        while (!(c == '-' || c == '.' || (c >= '0' && c <= '9'))) {
            c = getChar();
            if (c == EOF) return false;
        }
        int sign = 1;
        if (c == '-') { sign = -1; c = getChar(); }
        double x = 0.0;
        while (c >= '0' && c <= '9') { x = x * 10.0 + (c - '0'); c = getChar(); }
        if (c == '.') {
            double place = 1.0;
            c = getChar();
            while (c >= '0' && c <= '9') {
                place *= 10.0;
                x += (c - '0') / place;
                c = getChar();
            }
        }
        if (c == 'e' || c == 'E') {
            int esign = 1, e = 0;
            c = getChar();
            if (c == '+') c = getChar();
            else if (c == '-') { esign = -1; c = getChar(); }
            while (c >= '0' && c <= '9') { e = e * 10 + (c - '0'); c = getChar(); }
            x = x * pow(10.0, esign * e);
        }
        out = x * sign;
        return true;
    }
} In;

struct Point {
    double x, y;
};
static inline double cross(const Point &O, const Point &A, const Point &B) {
    return (A.x - O.x) * (B.y - O.y) - (A.y - O.y) * (B.x - O.x);
}
static vector<Point> convexHull(vector<Point> v) {
    sort(v.begin(), v.end(), [](const Point& a, const Point& b) {
        if (a.x != b.x) return a.x < b.x;
        return a.y < b.y;
    });
    v.erase(unique(v.begin(), v.end(), [](const Point& a, const Point& b){
        return a.x == b.x && a.y == b.y;
    }), v.end());
    int n = (int)v.size();
    if (n <= 1) return v;
    vector<Point> H(2*n);
    int k = 0;
    for (int i = 0; i < n; ++i) {
        while (k >= 2 && cross(H[k-2], H[k-1], v[i]) <= 0) --k;
        H[k++] = v[i];
    }
    for (int i = n-2, t = k+1; i >= 0; --i) {
        while (k >= t && cross(H[k-2], H[k-1], v[i]) <= 0) --k;
        H[k++] = v[i];
    }
    H.resize(k-1);
    return H;
}
static inline double polygonArea(const vector<Point>& poly) {
    int n = (int)poly.size();
    if (n < 3) return 0.0;
    long double s = 0;
    for (int i = 0; i < n; ++i) {
        int j = (i + 1) % n;
        s += (long double)poly[i].x * poly[j].y - (long double)poly[i].y * poly[j].x;
    }
    return (double)fabs(s) * 0.5;
}
static inline double polygonPerimeter(const vector<Point>& poly) {
    int n = (int)poly.size();
    if (n == 0) return 0.0;
    if (n == 1) return 0.0;
    long double p = 0;
    for (int i = 0; i < n; ++i) {
        int j = (i + 1) % n;
        long double dx = (long double)poly[i].x - poly[j].x;
        long double dy = (long double)poly[i].y - poly[j].y;
        p += sqrt((double)(dx*dx + dy*dy));
    }
    return (double)p;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n;
    if (!In.readInt(n)) return 0;
    vector<Point> pts(n+1);
    for (int i = 1; i <= n; ++i) {
        double x, y;
        In.readDouble(x); In.readDouble(y);
        pts[i] = {x, y};
    }
    long long m;
    In.readInt(m);
    vector<int> deg(n+1, 0);
    long double sumLen = 0.0L;
    for (long long i = 0; i < m; ++i) {
        int a, b;
        In.readInt(a); In.readInt(b);
        double dx = pts[a].x - pts[b].x;
        double dy = pts[a].y - pts[b].y;
        sumLen += sqrt(dx*dx + dy*dy);
        if (a >= 1 && a <= n) deg[a]++;
        if (b >= 1 && b <= n) deg[b]++;
    }
    double r; In.readDouble(r);
    double p1, p2, p3, p4;
    In.readDouble(p1); In.readDouble(p2); In.readDouble(p3); In.readDouble(p4);
    const double PI = acos(-1.0);
    if (m == 0) {
        printf("%.7f\n", 0.0);
        return 0;
    }
    vector<Point> usedPts;
    int usedCnt = 0;
    usedPts.reserve(n);
    for (int i = 1; i <= n; ++i) {
        if (deg[i] > 0) {
            usedPts.push_back(pts[i]);
            usedCnt++;
        }
    }
    double A_sumCorr = (double)(2.0L * r * sumLen) + PI * r * r * (double)usedCnt;

    // Convex hull of used points for an upper bound
    double A_hull_buf = 0.0;
    if (usedCnt == 0) {
        A_hull_buf = 0.0;
    } else if (usedCnt == 1) {
        A_hull_buf = PI * r * r;
    } else {
        vector<Point> hull = convexHull(usedPts);
        if (hull.size() == 0) {
            A_hull_buf = 0.0;
        } else if (hull.size() == 1) {
            A_hull_buf = PI * r * r;
        } else {
            double area = polygonArea(hull);
            double perim = polygonPerimeter(hull);
            A_hull_buf = area + r * perim + PI * r * r;
        }
    }

    long long denomPairs = 1LL * n * (n - 1) / 2;
    double delta = (denomPairs > 0) ? (double)m / (double)denomPairs : 1.0;
    if (delta < 0) delta = 0;
    if (delta > 1) delta = 1;
    double gamma = 0.5; // blending exponent
    double alpha = pow(delta, gamma);

    double approx = alpha * A_hull_buf + (1.0 - alpha) * A_sumCorr;
    if (approx < 0) approx = 0;
    if (approx > A_hull_buf) approx = A_hull_buf;

    printf("%.7f\n", approx);
    return 0;
}