#include <bits/stdc++.h>
using namespace std;

struct FastInput {
    static const int S = 1 << 20;
    int idx, size;
    char buf[S];
    FastInput(): idx(0), size(0) {}
    inline char getChar() {
        if (idx >= size) {
            size = (int)fread(buf, 1, S, stdin);
            idx = 0;
            if (size == 0) return 0;
        }
        return buf[idx++];
    }
    template<typename T>
    bool readInt(T &out) {
        char c;
        T sign = 1;
        T val = 0;
        c = getChar();
        if (!c) return false;
        while (c!='-' && (c<'0' || c>'9')) {
            c = getChar();
            if (!c) return false;
        }
        if (c=='-') { sign = -1; c = getChar(); }
        for (; c>='0' && c<='9'; c = getChar()) {
            val = val*10 + (c - '0');
        }
        out = val * sign;
        return true;
    }
    bool readDouble(double &out) {
        char c = getChar();
        if (!c) return false;
        while (c!='-' && c!='+' && c!='.' && (c<'0' || c>'9')) {
            c = getChar();
            if (!c) return false;
        }
        int sign = 1;
        if (c=='-' || c=='+') {
            if (c=='-') sign = -1;
            c = getChar();
        }
        long long intPart = 0;
        bool intGot = false;
        while (c>='0' && c<='9') {
            intGot = true;
            intPart = intPart*10 + (c - '0');
            c = getChar();
        }
        double frac = 0.0, base = 1.0;
        if (c=='.') {
            c = getChar();
            while (c>='0' && c<='9') {
                base *= 10.0;
                frac = frac*10.0 + (c - '0');
                c = getChar();
            }
        }
        double val = (double)intPart + (frac / base);
        if (c=='e' || c=='E') {
            int esign = 1;
            int e = 0;
            c = getChar();
            if (c=='+' || c=='-') { if (c=='-') esign = -1; c = getChar(); }
            while (c>='0' && c<='9') {
                e = e*10 + (c - '0');
                c = getChar();
            }
            val *= pow(10.0, esign * e);
        }
        out = sign * val;
        return true;
    }
} In;

struct Point { double x, y; };

struct SegInfo {
    double Ax, Ay, Bx, By;
    double L;
    double ux, uy; // unit direction
    double nx, ny; // unit normal
    double xminr, xmaxr;
    double ylo_vert, yhi_vert; // for vertical segments
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n;
    if (!In.readInt(n)) return 0;
    vector<Point> P(n);
    double minx = 1e100, maxx = -1e100;
    for (int i = 0; i < n; ++i) {
        In.readDouble(P[i].x);
        In.readDouble(P[i].y);
        if (P[i].x < minx) minx = P[i].x;
        if (P[i].x > maxx) maxx = P[i].x;
    }
    int m;
    In.readInt(m);
    vector<pair<int,int>> edges(m);
    for (int i = 0; i < m; ++i) {
        int a,b;
        In.readInt(a);
        In.readInt(b);
        --a; --b;
        edges[i] = {a,b};
    }
    double r;
    In.readDouble(r);
    double p1, p2, p3, p4;
    In.readDouble(p1);
    In.readDouble(p2);
    In.readDouble(p3);
    In.readDouble(p4);
    // Build segments
    vector<SegInfo> S;
    S.reserve(m);
    for (int i = 0; i < m; ++i) {
        int a = edges[i].first;
        int b = edges[i].second;
        if (a < 0 || b < 0 || a >= n || b >= n) continue;
        double Ax = P[a].x, Ay = P[a].y;
        double Bx = P[b].x, By = P[b].y;
        double dx = Bx - Ax, dy = By - Ay;
        double L = hypot(dx, dy);
        if (L <= 1e-15) continue;
        SegInfo si;
        si.Ax = Ax; si.Ay = Ay; si.Bx = Bx; si.By = By;
        si.L = L;
        si.ux = dx / L; si.uy = dy / L;
        si.nx = -si.uy; si.ny = si.ux;
        si.xminr = min(Ax, Bx) - r;
        si.xmaxr = max(Ax, Bx) + r;
        si.ylo_vert = min(Ay, By);
        si.yhi_vert = max(Ay, By);
        S.push_back(si);
    }
    m = (int)S.size();
    if (m == 0) {
        cout.setf(std::ios::fixed); cout<<setprecision(7)<<0.0<<"\n";
        return 0;
    }
    double minX = 1e100, maxX = -1e100;
    for (int i = 0; i < n; ++i) {
        if (P[i].x < minX) minX = P[i].x;
        if (P[i].x > maxX) maxX = P[i].x;
    }
    double left = minX - r;
    double right = maxX + r;
    if (left > right) swap(left, right);
    double width = right - left;
    if (width <= 1e-12) {
        // Degenerate width; fallback to trivial scan with small offset
        left -= r;
        right += r;
        width = right - left;
    }

    // Decide number of sample points for Simpson's rule
    int Nmax = 4097; // maximum points
    int Nmin = 33;   // minimum points
    long long denom = (long long)max(1, m);
    long long target = 20000000LL; // aim Nx * m <= 2e7
    int N = (int)(target / denom);
    if (N > Nmax) N = Nmax;
    if (N < Nmin) N = Nmin;
    if ((N & 1) == 0) N += 1; // make it odd for Simpson
    double dx = width / (N - 1);

    vector<pair<double,double>> intervals;
    intervals.reserve(min(m, 100000));

    auto compute_length = [&](double x0)->double {
        intervals.clear();
        const double eps = 1e-12;
        for (int i = 0; i < m; ++i) {
            const SegInfo &sg = S[i];
            if (x0 < sg.xminr - eps || x0 > sg.xmaxr + eps) continue;
            double lo = 1e300, hi = -1e300;
            // Endcap at A
            double dxA = x0 - sg.Ax;
            double t2 = r*r - dxA*dxA;
            if (t2 >= -1e-12) {
                if (t2 < 0) t2 = 0;
                double t = sqrt(t2);
                double y1 = sg.Ay - t;
                double y2 = sg.Ay + t;
                if (y1 < lo) lo = y1;
                if (y2 > hi) hi = y2;
            }
            // Endcap at B
            double dxB = x0 - sg.Bx;
            t2 = r*r - dxB*dxB;
            if (t2 >= -1e-12) {
                if (t2 < 0) t2 = 0;
                double t = sqrt(t2);
                double y1 = sg.By - t;
                double y2 = sg.By + t;
                if (y1 < lo) lo = y1;
                if (y2 > hi) hi = y2;
            }
            // Cylinder
            if (fabs(sg.ux) >= 1e-15) {
                // two offset lines
                double Ax_p = sg.Ax + r * sg.nx;
                double Ax_m = sg.Ax - r * sg.nx;
                double s1 = (x0 - Ax_p) / sg.ux;
                double s2 = (x0 - Ax_m) / sg.ux;
                if (s1 >= -1e-12 && s1 <= sg.L + 1e-12) {
                    if (s1 < 0) s1 = 0;
                    if (s1 > sg.L) s1 = sg.L;
                    double y = sg.Ay + s1 * sg.uy + r * sg.ny;
                    if (y < lo) lo = y;
                    if (y > hi) hi = y;
                }
                if (s2 >= -1e-12 && s2 <= sg.L + 1e-12) {
                    if (s2 < 0) s2 = 0;
                    if (s2 > sg.L) s2 = sg.L;
                    double y = sg.Ay + s2 * sg.uy - r * sg.ny;
                    if (y < lo) lo = y;
                    if (y > hi) hi = y;
                }
            } else {
                // Vertical segment case
                if (fabs(x0 - sg.Ax) <= r + 1e-12) {
                    if (sg.ylo_vert < lo) lo = sg.ylo_vert;
                    if (sg.yhi_vert > hi) hi = sg.yhi_vert;
                }
            }
            if (hi > lo + 1e-12) {
                intervals.emplace_back(lo, hi);
            }
        }
        if (intervals.empty()) return 0.0;
        sort(intervals.begin(), intervals.end(), [](const pair<double,double>&a, const pair<double,double>&b){
            if (a.first == b.first) return a.second < b.second;
            return a.first < b.first;
        });
        double total = 0.0;
        double curL = intervals[0].first;
        double curR = intervals[0].second;
        for (size_t i = 1; i < intervals.size(); ++i) {
            double a = intervals[i].first;
            double b = intervals[i].second;
            if (b <= curR) continue;
            if (a > curR) {
                total += (curR - curL);
                curL = a; curR = b;
            } else {
                curR = b;
            }
        }
        total += (curR - curL);
        return total;
    };

    double sum = 0.0;
    for (int i = 0; i < N; ++i) {
        double x0 = left + dx * i;
        double Lx = compute_length(x0);
        if (i == 0 || i == N - 1) sum += Lx;
        else if (i & 1) sum += 4.0 * Lx;
        else sum += 2.0 * Lx;
    }
    double area = sum * dx / 3.0;

    cout.setf(std::ios::fixed);
    cout << setprecision(7) << area << "\n";
    return 0;
}