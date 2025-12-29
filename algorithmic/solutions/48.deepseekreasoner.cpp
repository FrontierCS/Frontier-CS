#include <bits/stdc++.h>
using namespace std;

struct Point {
    double x, y, z;
    Point(double x_ = 0, double y_ = 0, double z_ = 0) : x(x_), y(y_), z(z_) {}
};

double dist2(const Point& a, const Point& b) {
    double dx = a.x - b.x, dy = a.y - b.y, dz = a.z - b.z;
    return dx*dx + dy*dy + dz*dz;
}

double compute_r(const vector<Point>& pts) {
    int n = pts.size();
    double min_pair_dist2 = 1e100;
    for (int i = 0; i < n; ++i) {
        for (int j = i+1; j < n; ++j) {
            double d2 = dist2(pts[i], pts[j]);
            if (d2 < min_pair_dist2) min_pair_dist2 = d2;
        }
    }
    double min_pair_dist = sqrt(min_pair_dist2);
    double half_min_pair = min_pair_dist * 0.5;
    double min_bound_dist = 1e100;
    for (const Point& p : pts) {
        double dx = min(p.x, 1.0 - p.x);
        double dy = min(p.y, 1.0 - p.y);
        double dz = min(p.z, 1.0 - p.z);
        double d = min({dx, dy, dz});
        if (d < min_bound_dist) min_bound_dist = d;
    }
    return min(half_min_pair, min_bound_dist);
}

vector<Point> baseline_grid(int n) {
    int d = ceil(cbrt(n));
    vector<Point> pts;
    double s = 1.0 / d;
    for (int i = 0; i < d; ++i) {
        for (int j = 0; j < d; ++j) {
            for (int k = 0; k < d; ++k) {
                if ((int)pts.size() >= n) break;
                double x = (i + 0.5) * s;
                double y = (j + 0.5) * s;
                double z = (k + 0.5) * s;
                pts.emplace_back(x, y, z);
            }
            if ((int)pts.size() >= n) break;
        }
        if ((int)pts.size() >= n) break;
    }
    return pts;
}

vector<Point> fcc_candidate(int M, int n) {
    double a = 1.0 / (M + 1.0 / sqrt(2.0));
    double offset = a / (2.0 * sqrt(2.0));
    vector<Point> pts;
    // Type 0: (i,j,k)
    for (int i = 0; i <= M; ++i)
        for (int j = 0; j <= M; ++j)
            for (int k = 0; k <= M; ++k)
                pts.emplace_back(offset + i * a, offset + j * a, offset + k * a);
    // Type 1: (i+0.5, j+0.5, k)
    for (int i = 0; i <= M-1; ++i)
        for (int j = 0; j <= M-1; ++j)
            for (int k = 0; k <= M; ++k)
                pts.emplace_back(offset + (i + 0.5) * a, offset + (j + 0.5) * a, offset + k * a);
    // Type 2: (i+0.5, j, k+0.5)
    for (int i = 0; i <= M-1; ++i)
        for (int j = 0; j <= M; ++j)
            for (int k = 0; k <= M-1; ++k)
                pts.emplace_back(offset + (i + 0.5) * a, offset + j * a, offset + (k + 0.5) * a);
    // Type 3: (i, j+0.5, k+0.5)
    for (int i = 0; i <= M; ++i)
        for (int j = 0; j <= M-1; ++j)
            for (int k = 0; k <= M-1; ++k)
                pts.emplace_back(offset + i * a, offset + (j + 0.5) * a, offset + (k + 0.5) * a);

    // sort by distance to boundary descending
    vector<pair<double, int>> order;
    for (int i = 0; i < (int)pts.size(); ++i) {
        const Point& p = pts[i];
        double d = min({p.x, 1 - p.x, p.y, 1 - p.y, p.z, 1 - p.z});
        order.emplace_back(-d, i);
    }
    sort(order.begin(), order.end());
    vector<Point> selected;
    for (int idx = 0; idx < min(n, (int)order.size()); ++idx)
        selected.push_back(pts[order[idx].second]);
    return selected;
}

vector<Point> best_fcc(int n) {
    double best_r = 0;
    vector<Point> best_pts;
    for (int M = 1; M <= 15; ++M) {
        int total = (M + 1) * (4 * M * M + 2 * M + 1);
        if (total < n) continue;
        vector<Point> candidate = fcc_candidate(M, n);
        if ((int)candidate.size() < n) continue;
        double r = compute_r(candidate);
        if (r > best_r) {
            best_r = r;
            best_pts = move(candidate);
        }
    }
    return best_pts;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);

    int n;
    cin >> n;

    vector<Point> points;
    if (n == 2) {
        double r = (3.0 - sqrt(3.0)) / 4.0;
        points.emplace_back(r, r, r);
        points.emplace_back(1 - r, 1 - r, 1 - r);
    } else if (n == 3) {
        double r = 1.0 / (2.0 + sqrt(2.0));
        points.emplace_back(r, r, r);
        points.emplace_back(1 - r, 1 - r, r);
        points.emplace_back(1 - r, r, 1 - r);
    } else if (n == 4) {
        double r = 1.0 / (2.0 + sqrt(2.0));
        points.emplace_back(r, r, r);
        points.emplace_back(1 - r, 1 - r, r);
        points.emplace_back(1 - r, r, 1 - r);
        points.emplace_back(r, 1 - r, 1 - r);
    } else {
        vector<Point> baseline = baseline_grid(n);
        double r_base = compute_r(baseline);
        vector<Point> fcc_pts = best_fcc(n);
        double r_fcc = compute_r(fcc_pts);
        if (r_fcc > r_base) {
            points = move(fcc_pts);
        } else {
            points = move(baseline);
        }
    }

    cout << fixed << setprecision(12);
    for (const Point& p : points) {
        cout << p.x << " " << p.y << " " << p.z << "\n";
    }

    return 0;
}