#include <bits/stdc++.h>
using namespace std;

struct Segment {
    double x1, y1, x2, y2;
    double dx, dy, L2;
    double xmin, xmax;
    bool isPoint;
    bool isVertical;
    bool isHorizontal;
};

int n;
vector<Segment> segs;
double r, r2;
vector<pair<double,double>> intervals;

inline void add_interval(double l, double r) {
    if (r - l <= 0.0) return;
    intervals.emplace_back(l, r);
}

inline void add_segment_intervals_at_x(const Segment &s, double x) {
    if (x < s.xmin - r || x > s.xmax + r) return;

    double xdiffA = x - s.x1;
    double valA = r2 - xdiffA * xdiffA;
    if (valA > 0.0) {
        double RA = sqrt(valA);
        add_interval(s.y1 - RA, s.y1 + RA);
    }

    double xdiffB = x - s.x2;
    double valB = r2 - xdiffB * xdiffB;
    if (valB > 0.0) {
        double RB = sqrt(valB);
        add_interval(s.y2 - RB, s.y2 + RB);
    }

    if (s.isPoint) return;

    const double eps = 1e-12;

    // Vertical segment
    if (s.isVertical) {
        double xdiff = x - s.x1;
        if (xdiff * xdiff <= r2 + 1e-12) {
            double yl = min(s.y1, s.y2);
            double yr = max(s.y1, s.y2);
            add_interval(yl, yr);
        }
        return;
    }

    // Horizontal segment
    if (s.isHorizontal) {
        if ((x >= s.xmin && x <= s.xmax)) {
            add_interval(s.y1 - r, s.y1 + r);
        }
        return;
    }

    // General case
    double dx = s.dx;
    double dy = s.dy;
    double L2 = s.L2;
    double xdiff = x - s.x1;

    double invL2 = 1.0 / L2;
    double alpha = dx * dx * invL2;
    if (alpha < eps) return; // extremely unlikely here

    double beta = -2.0 * dx * dy * xdiff * invL2;
    double gamma = xdiff * xdiff * dy * dy * invL2 - r2;

    double D = beta * beta - 4.0 * alpha * gamma;
    if (D <= 0.0) return; // no interior intersection

    double sqrtD = sqrt(D);
    double Y1 = (-beta - sqrtD) / (2.0 * alpha);
    double Y2 = (-beta + sqrtD) / (2.0 * alpha);
    if (Y1 > Y2) swap(Y1, Y2);

    // t-range constraints: 0 <= t <= 1
    // t = (dx*xdiff + dy*Y) / L2
    double ya = (-dx * xdiff) / dy;
    double yb = (L2 - dx * xdiff) / dy;
    double Ylo_t = min(ya, yb);
    double Yhi_t = max(ya, yb);

    double Ylo = max(Y1, Ylo_t);
    double Yhi = min(Y2, Yhi_t);
    if (Ylo < Yhi) {
        add_interval(s.y1 + Ylo, s.y1 + Yhi);
    }
}

double unionLength(double x) {
    intervals.clear();

    for (const auto &s : segs) {
        add_segment_intervals_at_x(s, x);
    }

    if (intervals.empty()) return 0.0;

    sort(intervals.begin(), intervals.end());
    double total = 0.0;
    double curL = intervals[0].first;
    double curR = intervals[0].second;

    for (size_t i = 1; i < intervals.size(); ++i) {
        double l = intervals[i].first;
        double r = intervals[i].second;
        if (r <= curR) continue;
        if (l <= curR) {
            curR = r;
        } else {
            total += curR - curL;
            curL = l;
            curR = r;
        }
    }
    total += curR - curL;
    return total;
}

double adaptiveSimpson(double L, double R, double fL, double fM, double fR, double S, double eps, int depth) {
    double M = (L + R) * 0.5;
    double LM = (L + M) * 0.5;
    double RM = (M + R) * 0.5;

    double fLM = unionLength(LM);
    double fRM = unionLength(RM);

    double SL = (M - L) * (fL + 4.0 * fLM + fM) / 6.0;
    double SR = (R - M) * (fM + 4.0 * fRM + fR) / 6.0;

    double diff = SL + SR - S;
    if (depth <= 0 || fabs(diff) <= 15.0 * eps) {
        return SL + SR + diff / 15.0;
    }
    return adaptiveSimpson(L, M, fL, fLM, fM, SL, eps * 0.5, depth - 1) +
           adaptiveSimpson(M, R, fM, fRM, fR, SR, eps * 0.5, depth - 1);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    if (!(cin >> n)) return 0;
    vector<double> xs(n), ys(n);
    for (int i = 0; i < n; ++i) {
        cin >> xs[i] >> ys[i];
    }

    int m;
    cin >> m;
    segs.reserve(m);

    vector<pair<int,int>> edges(m);
    for (int i = 0; i < m; ++i) {
        int a, b;
        cin >> a >> b;
        --a; --b;
        edges[i] = {a, b};
    }

    cin >> r;
    r2 = r * r;

    double p1, p2, p3, p4;
    cin >> p1 >> p2 >> p3 >> p4; // not used

    double globalMinX = 1e100, globalMaxX = -1e100;

    for (int i = 0; i < m; ++i) {
        int a = edges[i].first;
        int b = edges[i].second;
        Segment s;
        s.x1 = xs[a];
        s.y1 = ys[a];
        s.x2 = xs[b];
        s.y2 = ys[b];
        s.dx = s.x2 - s.x1;
        s.dy = s.y2 - s.y1;
        s.L2 = s.dx * s.dx + s.dy * s.dy;
        s.xmin = min(s.x1, s.x2);
        s.xmax = max(s.x1, s.x2);
        s.isPoint = (s.L2 == 0.0);
        const double eps = 1e-12;
        s.isVertical = (!s.isPoint && fabs(s.dx) < eps);
        s.isHorizontal = (!s.isPoint && fabs(s.dy) < eps);

        globalMinX = min(globalMinX, s.xmin);
        globalMaxX = max(globalMaxX, s.xmax);

        segs.push_back(s);
    }

    if (m == 0) {
        cout.setf(ios::fixed);
        cout << setprecision(7) << 0.0 << "\n";
        return 0;
    }

    intervals.reserve((size_t)max(1, m * 3));

    double L = globalMinX - r;
    double R = globalMaxX + r;

    double fL = unionLength(L);
    double fR = unionLength(R);
    double M = 0.5 * (L + R);
    double fM = unionLength(M);
    double S = (R - L) * (fL + 4.0 * fM + fR) / 6.0;

    double eps = 1e-5;
    int maxDepth = 12;
    double area = adaptiveSimpson(L, R, fL, fM, fR, S, eps, maxDepth);

    cout.setf(ios::fixed);
    cout << setprecision(7) << area << "\n";
    return 0;
}