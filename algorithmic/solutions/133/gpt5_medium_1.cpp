#include <bits/stdc++.h>
using namespace std;

struct Seg {
    double x1, y1, x2, y2;
    double dx, dy, L2, L;
    double ymin, ymax;
};

static const double EPS = 1e-12;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if (!(cin >> n)) return 0;
    vector<double> xs(n+1), ys(n+1);
    for (int i = 1; i <= n; ++i) {
        cin >> xs[i] >> ys[i];
    }
    int m;
    cin >> m;
    vector<pair<int,int>> edges;
    edges.reserve(m);
    for (int i = 0; i < m; ++i) {
        int a,b; cin >> a >> b;
        edges.emplace_back(a,b);
    }
    double r; cin >> r;
    double p1, p2, p3, p4; cin >> p1 >> p2 >> p3 >> p4; // read but unused
    
    vector<Seg> segs;
    segs.reserve(m);
    double Ymin = 1e100, Ymax = -1e100;
    for (int i = 0; i < m; ++i) {
        int a = edges[i].first;
        int b = edges[i].second;
        double x1 = xs[a], y1 = ys[a];
        double x2 = xs[b], y2 = ys[b];
        Seg s;
        s.x1 = x1; s.y1 = y1; s.x2 = x2; s.y2 = y2;
        s.dx = x2 - x1; s.dy = y2 - y1;
        s.L2 = s.dx*s.dx + s.dy*s.dy;
        s.L = sqrt(s.L2);
        s.ymin = min(y1, y2) - r;
        s.ymax = max(y1, y2) + r;
        segs.push_back(s);
        Ymin = min(Ymin, s.ymin);
        Ymax = max(Ymax, s.ymax);
    }
    if (m == 0) {
        cout.setf(std::ios::fixed); cout << setprecision(7) << 0.0 << "\n";
        return 0;
    }
    // Bin by y to reduce per-evaluation candidates
    double binH = 1.0;
    if (Ymax < Ymin) swap(Ymax, Ymin);
    int Nbins = (int)floor((Ymax - Ymin) / binH) + 1;
    vector<vector<int>> bins(Nbins);
    for (int i = 0; i < m; ++i) {
        int i0 = (int)floor((segs[i].ymin - Ymin) / binH);
        int i1 = (int)floor((segs[i].ymax - Ymin) / binH);
        if (i0 < 0) i0 = 0;
        if (i1 >= Nbins) i1 = Nbins - 1;
        for (int k = i0; k <= i1; ++k) bins[k].push_back(i);
    }

    struct Interval { double l, r; };
    vector<Interval> intervals;
    intervals.reserve(1024);

    auto f_cache = unordered_map<uint64_t, double>();
    f_cache.reserve(4096);

    auto as_uint64 = [](double x)->uint64_t {
        uint64_t u;
        memcpy(&u, &x, sizeof(double));
        return u;
    };

    auto L_at_y = [&](double y) -> double {
        // memoization
        uint64_t key = as_uint64(y);
        auto itc = f_cache.find(key);
        if (itc != f_cache.end()) return itc->second;

        int binIdx = (int)floor((y - Ymin) / binH);
        if (binIdx < 0 || binIdx >= Nbins) {
            f_cache.emplace(key, 0.0);
            return 0.0;
        }
        auto &cand = bins[binIdx];
        if (cand.empty()) {
            f_cache.emplace(key, 0.0);
            return 0.0;
        }
        intervals.clear();
        intervals.reserve(cand.size() * 3);

        for (int idx : cand) {
            const Seg &s = segs[idx];
            if (y < s.ymin - 1e-14 || y > s.ymax + 1e-14) continue;

            // Rectangle (segment interior thickened) contribution
            if (s.L > 0) {
                if (fabs(s.dy) <= EPS) {
                    // horizontal segment
                    if (fabs(y - s.y1) <= r + 1e-14) {
                        double l = min(s.x1, s.x2);
                        double rr = max(s.x1, s.x2);
                        intervals.push_back({l, rr});
                    }
                } else if (fabs(s.dx) <= EPS) {
                    // vertical segment
                    if (y >= min(s.y1, s.y2) - 1e-14 && y <= max(s.y1, s.y2) + 1e-14) {
                        intervals.push_back({s.x1 - r, s.x1 + r});
                    }
                } else {
                    // general
                    double L = s.L;
                    // Inequality 1: |dy * x + c1| <= r * L
                    double c1 = - s.x1 * s.dy - (y - s.y1) * s.dx;
                    double left1 = (-r*L - c1) / s.dy;
                    double right1 = ( r*L - c1) / s.dy;
                    if (left1 > right1) swap(left1, right1);

                    // Inequality 2: 0 <= dx * x + const2 <= L2
                    double const2 = - s.x1 * s.dx + (y - s.y1) * s.dy;
                    double q1 = (-const2) / s.dx;
                    double q2 = ( s.L2 - const2) / s.dx;
                    double left2 = min(q1, q2);
                    double right2 = max(q1, q2);

                    double l = max(left1, left2);
                    double rr = min(right1, right2);
                    if (l <= rr + 1e-14) {
                        intervals.push_back({l, rr});
                    }
                }
            }

            // Caps (disks) at endpoints
            double dyA = y - s.y1;
            if (fabs(dyA) <= r + 1e-14) {
                double h = sqrt(max(0.0, r*r - dyA*dyA));
                intervals.push_back({s.x1 - h, s.x1 + h});
            }
            double dyB = y - s.y2;
            if (fabs(dyB) <= r + 1e-14) {
                double h = sqrt(max(0.0, r*r - dyB*dyB));
                intervals.push_back({s.x2 - h, s.x2 + h});
            }
        }

        if (intervals.empty()) {
            f_cache.emplace(key, 0.0);
            return 0.0;
        }

        sort(intervals.begin(), intervals.end(), [](const Interval &a, const Interval &b){
            if (a.l == b.l) return a.r < b.r;
            return a.l < b.l;
        });

        double len = 0.0;
        double curL = intervals[0].l, curR = intervals[0].r;
        for (size_t i = 1; i < intervals.size(); ++i) {
            double l = intervals[i].l, r = intervals[i].r;
            if (l > curR + 1e-12) {
                len += max(0.0, curR - curL);
                curL = l; curR = r;
            } else {
                if (r > curR) curR = r;
            }
        }
        len += max(0.0, curR - curL);

        f_cache.emplace(key, len);
        return len;
    };

    function<double(double,double,double,double,double,double,double)> asr;
    auto simpson = [&](double a, double b, double fa, double fm, double fb) {
        return (b - a) * (fa + 4.0*fm + fb) / 6.0;
    };
    asr = [&](double a, double b, double fa, double fm, double fb, double whole, double eps) -> double {
        double m = 0.5*(a + b);
        double l = 0.5*(a + m);
        double r = 0.5*(m + b);
        double fl = L_at_y(l);
        double fr = L_at_y(r);
        double left = simpson(a, m, fa, fl, fm);
        double right = simpson(m, b, fm, fr, fb);
        double delta = left + right - whole;
        if (fabs(delta) <= 15.0 * eps) {
            return left + right + delta / 15.0;
        }
        return asr(a, m, fa, fl, fm, left, eps * 0.5) + asr(m, b, fm, fr, fb, right, eps * 0.5);
    };

    double a = Ymin, b = Ymax;
    double fa = L_at_y(a);
    double fbv = L_at_y(b);
    double m = 0.5*(a + b);
    double fm = L_at_y(m);
    double whole = (b - a) * (fa + 4.0*fm + fbv) / 6.0;

    // Set absolute epsilon for area
    double eps = 1e-6; // reasonably strict; adjust if needed
    double area = asr(a, b, fa, fm, fbv, whole, eps);

    cout.setf(std::ios::fixed);
    cout << setprecision(7) << area << "\n";
    return 0;
}