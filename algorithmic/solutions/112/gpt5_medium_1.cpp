#include <bits/stdc++.h>
using namespace std;

struct P {
    double x, y, z;
};

static const double PI = acos(-1.0);
static const double EPS = 1e-12;

int count_grid(double s) {
    if (s <= 0) return 0;
    int m = (int)floor(1.0 / s + 1e-12);
    int cnt = 0;
    for (int i = -m; i <= m; ++i) {
        double x = i * s;
        double x2 = x * x;
        if (x2 > 1.0 + EPS) continue;
        double r2x = 1.0 - x2;
        int mj = (int)floor(sqrt(max(0.0, r2x)) / s + 1e-12);
        for (int j = -mj; j <= mj; ++j) {
            double y = j * s;
            double y2 = y * y;
            if (x2 + y2 > 1.0 + EPS) continue;
            double r2xy = 1.0 - x2 - y2;
            int mk = (int)floor(sqrt(max(0.0, r2xy)) / s + 1e-12);
            cnt += 2 * mk + 1;
        }
    }
    return cnt;
}

vector<P> generate_grid(double s) {
    vector<P> pts;
    int m = (int)floor(1.0 / s + 1e-12);
    for (int i = -m; i <= m; ++i) {
        double x = i * s;
        double x2 = x * x;
        if (x2 > 1.0 + 1e-9) continue;
        double r2x = 1.0 - x2;
        int mj = (int)floor(sqrt(max(0.0, r2x)) / s + 1e-12);
        for (int j = -mj; j <= mj; ++j) {
            double y = j * s;
            double y2 = y * y;
            if (x2 + y2 > 1.0 + 1e-9) continue;
            double r2xy = 1.0 - x2 - y2;
            int mk = (int)floor(sqrt(max(0.0, r2xy)) / s + 1e-12);
            for (int k = -mk; k <= mk; ++k) {
                double z = k * s;
                double r2 = x2 + y2 + z * z;
                if (r2 <= 1.0 + 1e-9) pts.push_back({x, y, z});
            }
        }
    }
    return pts;
}

vector<P> spherical_fibonacci(int n) {
    vector<P> pts;
    pts.reserve(n);
    const double phi = (1.0 + sqrt(5.0)) * 0.5;
    const double ga = 2.0 * PI / (phi * phi); // golden angle
    for (int i = 0; i < n; ++i) {
        double z = 1.0 - 2.0 * (i + 0.5) / n;
        double r = sqrt(max(0.0, 1.0 - z * z));
        double theta = i * ga;
        double x = r * cos(theta);
        double y = r * sin(theta);
        pts.push_back({x, y, z});
    }
    return pts;
}

vector<P> special_points(int n) {
    vector<P> pts;
    if (n == 2) {
        pts.push_back({0, 0, 1});
        pts.push_back({0, 0, -1});
    } else if (n == 3) {
        for (int k = 0; k < 3; ++k) {
            double ang = 2 * PI * k / 3.0;
            pts.push_back({cos(ang), sin(ang), 0});
        }
    } else if (n == 4) {
        double t = 1.0 / sqrt(3.0);
        pts.push_back({ t,  t,  t});
        pts.push_back({-t, -t,  t});
        pts.push_back({-t,  t, -t});
        pts.push_back({ t, -t, -t});
    } else if (n == 5) {
        // Triangular dipyramid: poles + 3 on equator
        pts.push_back({0, 0, 1});
        pts.push_back({0, 0, -1});
        for (int k = 0; k < 3; ++k) {
            double ang = 2 * PI * k / 3.0;
            pts.push_back({cos(ang), sin(ang), 0});
        }
    } else if (n == 6) {
        pts.push_back({ 1, 0, 0});
        pts.push_back({-1, 0, 0});
        pts.push_back({0,  1, 0});
        pts.push_back({0, -1, 0});
        pts.push_back({0, 0,  1});
        pts.push_back({0, 0, -1});
    }
    return pts;
}

double compute_min_dist(const vector<P>& pts) {
    int n = (int)pts.size();
    double minD2 = 1e300;
    for (int i = 0; i < n; ++i) {
        for (int j = i + 1; j < n; ++j) {
            double dx = pts[i].x - pts[j].x;
            double dy = pts[i].y - pts[j].y;
            double dz = pts[i].z - pts[j].z;
            double d2 = dx*dx + dy*dy + dz*dz;
            if (d2 < minD2) minD2 = d2;
        }
    }
    return sqrt(max(0.0, minD2));
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n;
    if (!(cin >> n)) return 0;

    vector<P> result;

    if (n <= 6) {
        result = special_points(n);
        // Fallback to Fibonacci if something goes wrong
        if ((int)result.size() != n) result = spherical_fibonacci(n);
    } else {
        // Grid-based volumetric distribution + farthest-point sampling
        double V = 4.0 * PI / 3.0;
        double s = pow(V / n, 1.0 / 3.0);
        // Bracket feasible/infeasible
        double low, high;
        int c = count_grid(s);
        if (c < n) {
            double prev = s;
            // shrink until feasible
            for (int it = 0; it < 100 && c < n; ++it) {
                prev = s;
                s *= 0.95;
                c = count_grid(s);
            }
            low = s;
            high = prev;
        } else {
            double prev = s;
            // expand until infeasible
            for (int it = 0; it < 100 && c >= n && s < 2.0; ++it) {
                prev = s;
                s *= 1.05;
                c = count_grid(s);
            }
            low = prev;
            high = s;
        }
        // Binary search maximum s with count >= n
        for (int it = 0; it < 40; ++it) {
            double mid = 0.5 * (low + high);
            int cnt = count_grid(mid);
            if (cnt >= n) low = mid;
            else high = mid;
        }
        double s_star = low;

        vector<P> cand = generate_grid(s_star);
        int m = (int)cand.size();
        if (m <= n) {
            result = cand;
            // If still less than n due to numerical issues, complement with Fibonacci points
            if ((int)result.size() < n) {
                vector<P> fib = spherical_fibonacci(n - (int)result.size());
                result.insert(result.end(), fib.begin(), fib.end());
            }
        } else {
            // Farthest-point sampling
            vector<char> used(m, false);
            vector<double> bestDist2(m, 1e300);
            int start = 0;
            double bestR = -1.0;
            for (int i = 0; i < m; ++i) {
                double r2 = cand[i].x*cand[i].x + cand[i].y*cand[i].y + cand[i].z*cand[i].z;
                if (r2 > bestR) {
                    bestR = r2;
                    start = i;
                }
            }
            vector<int> sel;
            sel.reserve(n);
            used[start] = true;
            sel.push_back(start);

            for (int it = 1; it < n; ++it) {
                int last = sel.back();
                // Update distances to the set using the last added point
                for (int j = 0; j < m; ++j) {
                    if (used[j]) continue;
                    double dx = cand[j].x - cand[last].x;
                    double dy = cand[j].y - cand[last].y;
                    double dz = cand[j].z - cand[last].z;
                    double d2 = dx*dx + dy*dy + dz*dz;
                    if (d2 < bestDist2[j]) bestDist2[j] = d2;
                }
                // Choose the farthest
                int pick = -1;
                double bestVal = -1.0;
                for (int j = 0; j < m; ++j) {
                    if (used[j]) continue;
                    if (bestDist2[j] > bestVal) {
                        bestVal = bestDist2[j];
                        pick = j;
                    }
                }
                if (pick == -1) break;
                used[pick] = true;
                sel.push_back(pick);
            }
            result.reserve(n);
            for (int idx : sel) result.push_back(cand[idx]);
            // If somehow not enough (shouldn't happen), fill with Fibonacci
            if ((int)result.size() < n) {
                vector<P> fib = spherical_fibonacci(n - (int)result.size());
                result.insert(result.end(), fib.begin(), fib.end());
            }
        }
    }

    // Ensure points are within unit sphere
    for (auto &p : result) {
        double r2 = p.x*p.x + p.y*p.y + p.z*p.z;
        if (r2 > 1.0) {
            double r = sqrt(r2);
            p.x /= r;
            p.y /= r;
            p.z /= r;
        }
    }

    // Compute and output min distance
    double minDist = compute_min_dist(result);

    cout.setf(std::ios::fixed); 
    cout << setprecision(15) << minDist << "\n";
    for (auto &p : result) {
        cout << setprecision(15) << p.x << " " << p.y << " " << p.z << "\n";
    }
    return 0;
}