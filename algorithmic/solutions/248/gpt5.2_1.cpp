#include <bits/stdc++.h>
using namespace std;

struct City {
    int id;
    double x;
    vector<double> y;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    double base;
    if (!(cin >> base)) return 0;

    int M;
    cin >> M;
    vector<City> cities(M);

    for (int i = 0; i < M; i++) {
        int n;
        double x;
        cin >> n >> x;
        cities[i].id = i + 1;
        cities[i].x = x;
        cities[i].y.resize(n);
        for (int j = 0; j < n; j++) cin >> cities[i].y[j];
    }

    double Dorig, Sorig;
    cin >> Dorig >> Sorig;

    const double k = 0.6;
    double wD = (Dorig > 0 ? (1.0 - k) / Dorig : (1.0 - k));
    double wS = (Sorig > 0 ? k / Sorig : 0.0);

    vector<int> ord(M);
    iota(ord.begin(), ord.end(), 0);
    stable_sort(ord.begin(), ord.end(), [&](int a, int b) {
        if (cities[a].x != cities[b].x) return cities[a].x < cities[b].x;
        return cities[a].id < cities[b].id;
    });

    vector<int> sel(M, 0);
    for (int i = 0; i < M; i++) {
        const auto &ys = cities[i].y;
        double avg = 0.0;
        for (double v : ys) avg += v;
        avg /= max<size_t>(1, ys.size());
        int best = 0;
        double bestAbs = fabs(ys[0] - avg);
        for (int j = 1; j < (int)ys.size(); j++) {
            double a = fabs(ys[j] - avg);
            if (a < bestAbs) {
                bestAbs = a;
                best = j;
            }
        }
        sel[i] = best;
    }

    auto edgeCost = [&](int a, int b, int ia, int ib) -> double {
        double dx = fabs(cities[a].x - cities[b].x);
        double dy = cities[b].y[ib] - cities[a].y[ia];
        double dist = hypot(dx, dy);
        double slope = 0.0;
        if (dy > 0) {
            double denom = max(dx, 1e-9);
            slope = dy / denom;
        }
        return dist * wD + slope * wS;
    };

    const int maxIter = 100;
    for (int it = 0; it < maxIter; it++) {
        bool changed = false;
        for (int pos = 0; pos < M; pos++) {
            int ci = ord[pos];
            int pi = ord[(pos - 1 + M) % M];
            int ni = ord[(pos + 1) % M];

            int cur = sel[ci];
            int best = cur;
            double bestCost = edgeCost(pi, ci, sel[pi], cur) + edgeCost(ci, ni, cur, sel[ni]);

            for (int cand = 0; cand < (int)cities[ci].y.size(); cand++) {
                double c = edgeCost(pi, ci, sel[pi], cand) + edgeCost(ci, ni, cand, sel[ni]);
                if (c + 1e-12 < bestCost) {
                    bestCost = c;
                    best = cand;
                }
            }
            if (best != cur) {
                sel[ci] = best;
                changed = true;
            }
        }
        if (!changed) break;
    }

    for (int pos = 0; pos < M; pos++) {
        int ci = ord[pos];
        if (pos) cout << "@";
        cout << "(" << cities[ci].id << "," << (sel[ci] + 1) << ")";
    }
    cout << "\n";
    return 0;
}