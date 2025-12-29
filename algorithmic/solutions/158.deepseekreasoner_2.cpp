#include <iostream>
#include <vector>
#include <algorithm>
#include <set>
#include <cmath>
#include <cstdlib>
#include <ctime>

using namespace std;

struct State {
    int m, n;
    vector<int> v; // vertical lines (x coordinates)
    vector<int> h; // horizontal lines (y coordinates)
    const vector<pair<int, int>>& points;
    const set<int>& set_x;
    const set<int>& set_y;
    const vector<int>& a; // a[1..10]

    State(int m, int n, const vector<int>& v, const vector<int>& h,
          const vector<pair<int, int>>& points,
          const set<int>& set_x, const set<int>& set_y,
          const vector<int>& a)
        : m(m), n(n), v(v), h(h), points(points),
          set_x(set_x), set_y(set_y), a(a) {}

    // compute score for given lines
    int compute_score(const vector<int>& vv, const vector<int>& hh) const {
        int mv = vv.size();
        int mh = hh.size();
        vector<vector<int>> cnt(mv+1, vector<int>(mh+1, 0));
        for (const auto& p : points) {
            int xi = lower_bound(vv.begin(), vv.end(), p.first) - vv.begin();
            int yi = lower_bound(hh.begin(), hh.end(), p.second) - hh.begin();
            cnt[xi][yi]++;
        }
        vector<int> b(11, 0);
        for (int i = 0; i <= mv; ++i) {
            for (int j = 0; j <= mh; ++j) {
                int c = cnt[i][j];
                if (c >= 1 && c <= 10) b[c]++;
            }
        }
        int score = 0;
        for (int d = 1; d <= 10; ++d) {
            score += min(a[d], b[d]);
        }
        return score;
    }

    // hill climbing with limited iterations
    void hill_climb(int iterations) {
        int cur_score = compute_score(v, h);
        for (int iter = 0; iter < iterations; ++iter) {
            bool improved = false;
            // try vertical lines
            for (int idx = 0; idx < m; ++idx) {
                int old_v = v[idx];
                for (int delta : {-100, -10, -1, 1, 10, 100}) {
                    int new_v = old_v + delta;
                    int left = (idx > 0) ? v[idx-1] : -10000;
                    int right = (idx+1 < m) ? v[idx+1] : 10000;
                    if (new_v <= left || new_v >= right) continue;
                    if (set_x.count(new_v)) continue;
                    vector<int> new_vv = v;
                    new_vv[idx] = new_v;
                    int new_score = compute_score(new_vv, h);
                    if (new_score > cur_score) {
                        v = new_vv;
                        cur_score = new_score;
                        improved = true;
                        break;
                    }
                }
                if (improved) break;
            }
            if (improved) continue;
            // try horizontal lines
            for (int idx = 0; idx < n; ++idx) {
                int old_h = h[idx];
                for (int delta : {-100, -10, -1, 1, 10, 100}) {
                    int new_h = old_h + delta;
                    int down = (idx > 0) ? h[idx-1] : -10000;
                    int up = (idx+1 < n) ? h[idx+1] : 10000;
                    if (new_h <= down || new_h >= up) continue;
                    if (set_y.count(new_h)) continue;
                    vector<int> new_hh = h;
                    new_hh[idx] = new_h;
                    int new_score = compute_score(v, new_hh);
                    if (new_score > cur_score) {
                        h = new_hh;
                        cur_score = new_score;
                        improved = true;
                        break;
                    }
                }
                if (improved) break;
            }
            if (!improved) break;
        }
    }
};

// generate m lines (vertical or horizontal) avoiding forbidden coordinates
vector<int> generate_lines(int m, const set<int>& forbidden, int minb, int maxb) {
    vector<int> lines;
    if (m == 0) return lines;
    double step = (maxb - minb) / (double)(m + 1);
    int prev = minb;
    for (int i = 1; i <= m; ++i) {
        int cand = minb + (int)round(i * step);
        if (cand <= prev) cand = prev + 1;
        while (forbidden.count(cand)) {
            cand++;
            if (cand >= maxb) {
                cand = maxb - 1;
                break;
            }
        }
        if (cand >= maxb) cand = maxb - 1;
        if (cand <= prev) {
            // search for any integer between prev+1 and maxb-1 not in forbidden
            bool found = false;
            for (int x = prev + 1; x < maxb; ++x) {
                if (!forbidden.count(x)) {
                    cand = x;
                    found = true;
                    break;
                }
            }
            if (!found) cand = prev + 1; // fallback, may hit a point but unlikely
        }
        lines.push_back(cand);
        prev = cand;
    }
    return lines;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, K;
    cin >> N >> K;
    vector<int> a(11, 0); // a[1..10]
    for (int d = 1; d <= 10; ++d) cin >> a[d];

    vector<pair<int, int>> points(N);
    set<int> set_x, set_y;
    for (int i = 0; i < N; ++i) {
        int x, y;
        cin >> x >> y;
        points[i] = {x, y};
        set_x.insert(x);
        set_y.insert(y);
    }

    // bounds for lines to actually cut the circle
    const int minb = -9999;
    const int maxb = 9999;

    // candidate (m,n) configurations: m vertical, n horizontal, m+n<=100
    vector<pair<int, int>> configs = {
        {50, 50}, {40, 60}, {60, 40}, {30, 70}, {70, 30},
        {20, 80}, {80, 20}, {10, 90}, {90, 10}, {0, 100}, {100, 0}
    };

    int best_score = -1;
    vector<int> best_v, best_h;
    int best_m = 0, best_n = 0;

    for (auto [m, n] : configs) {
        if (m + n > K) continue; // K=100, but just in case
        vector<int> v = generate_lines(m, set_x, minb, maxb);
        vector<int> h = generate_lines(n, set_y, minb, maxb);
        if ((int)v.size() != m || (int)h.size() != n) continue; // generation failed

        State state(m, n, v, h, points, set_x, set_y, a);
        int score = state.compute_score(v, h);
        state.hill_climb(5); // limited iterations

        score = state.compute_score(state.v, state.h);
        if (score > best_score) {
            best_score = score;
            best_v = state.v;
            best_h = state.h;
            best_m = m;
            best_n = n;
        }
    }

    // output
    int k = best_m + best_n;
    cout << k << "\n";
    for (int x : best_v) {
        cout << x << " " << 0 << " " << x << " " << 1 << "\n";
    }
    for (int y : best_h) {
        cout << 0 << " " << y << " " << 1 << " " << y << "\n";
    }

    return 0;
}