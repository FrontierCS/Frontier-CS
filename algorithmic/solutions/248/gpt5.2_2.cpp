#include <bits/stdc++.h>
using namespace std;

struct City {
    int x;
    vector<int> y;
};

static constexpr double K = 0.6;
static constexpr double INF = 1e100;

struct Solution {
    double cost = INF;
    vector<int> order;   // city indices (0-based)
    vector<int> pick;    // landing point indices per order position (0-based)
};

static inline double edgeCost(const City& a, int ia, const City& b, int ib, double wD, double wS) {
    double dx = (double)std::abs(b.x - a.x);
    double dy = (double)b.y[ib] - (double)a.y[ia];
    double dist = std::hypot(dx, dy);
    double slope = 0.0;
    if (dy > 0.0) {
        double h = (dx > 0.0) ? dx : 1e-6;
        slope = dy / h;
    }
    return wD * dist + wS * slope;
}

static Solution solveForOrder(const vector<City>& cities, const vector<int>& ord, double wD, double wS) {
    int m = (int)ord.size();
    vector<int> ns(m);
    for (int i = 0; i < m; ++i) ns[i] = (int)cities[ord[i]].y.size();

    // Precompute edge cost matrices for consecutive edges and the closing edge.
    vector<vector<double>> costEdge(m - 1);
    for (int i = 0; i < m - 1; ++i) {
        int ni = ns[i], nj = ns[i + 1];
        costEdge[i].assign((size_t)ni * (size_t)nj, 0.0);
        const City& ci = cities[ord[i]];
        const City& cj = cities[ord[i + 1]];
        for (int a = 0; a < ni; ++a) {
            for (int b = 0; b < nj; ++b) {
                costEdge[i][(size_t)a * (size_t)nj + (size_t)b] = edgeCost(ci, a, cj, b, wD, wS);
            }
        }
    }

    int n0 = ns[0];
    int nLast = ns[m - 1];
    vector<double> closeCost((size_t)nLast * (size_t)n0, 0.0);
    {
        const City& cl = cities[ord[m - 1]];
        const City& c0 = cities[ord[0]];
        for (int b = 0; b < nLast; ++b) {
            for (int a = 0; a < n0; ++a) {
                closeCost[(size_t)b * (size_t)n0 + (size_t)a] = edgeCost(cl, b, c0, a, wD, wS);
            }
        }
    }

    Solution best;
    best.order = ord;

    for (int start = 0; start < n0; ++start) {
        vector<double> dp(ns[0], INF);
        dp[start] = 0.0;

        vector<vector<int>> par(m);
        par[0].assign(ns[0], -1);

        for (int i = 0; i < m - 1; ++i) {
            int ni = ns[i], nj = ns[i + 1];
            vector<double> nxt(nj, INF);
            par[i + 1].assign(nj, -1);

            const auto& mat = costEdge[i];
            for (int a = 0; a < ni; ++a) {
                double base = dp[a];
                if (base >= INF / 4) continue;
                size_t rowOff = (size_t)a * (size_t)nj;
                for (int b = 0; b < nj; ++b) {
                    double cand = base + mat[rowOff + (size_t)b];
                    if (cand < nxt[b]) {
                        nxt[b] = cand;
                        par[i + 1][b] = a;
                    }
                }
            }
            dp.swap(nxt);
        }

        for (int end = 0; end < nLast; ++end) {
            double total = dp[end] + closeCost[(size_t)end * (size_t)n0 + (size_t)start];
            if (total < best.cost) {
                best.cost = total;
                best.pick.assign(m, 0);
                best.pick[m - 1] = end;
                for (int i = m - 1; i >= 1; --i) {
                    best.pick[i - 1] = par[i][best.pick[i]];
                }
            }
        }
    }

    return best;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    double base;
    if (!(cin >> base)) return 0;

    int M;
    cin >> M;

    vector<City> cities(M);
    for (int i = 0; i < M; ++i) {
        int n, x;
        cin >> n >> x;
        cities[i].x = x;
        cities[i].y.resize(n);
        for (int j = 0; j < n; ++j) cin >> cities[i].y[j];
    }

    double D0, S0;
    cin >> D0 >> S0;
    if (D0 <= 0) D0 = 1;
    if (S0 <= 0) S0 = 1;

    double wD = (1.0 - K) / D0;
    double wS = K / S0;

    vector<int> ordAsc(M);
    iota(ordAsc.begin(), ordAsc.end(), 0);
    stable_sort(ordAsc.begin(), ordAsc.end(), [&](int a, int b) {
        if (cities[a].x != cities[b].x) return cities[a].x < cities[b].x;
        return a < b;
    });

    vector<int> ordDesc = ordAsc;
    reverse(ordDesc.begin(), ordDesc.end());

    Solution sol1 = solveForOrder(cities, ordAsc, wD, wS);
    Solution sol2 = solveForOrder(cities, ordDesc, wD, wS);
    const Solution& sol = (sol2.cost < sol1.cost) ? sol2 : sol1;

    for (int i = 0; i < M; ++i) {
        if (i) cout << "@";
        int cityId = sol.order[i] + 1;
        int pointId = sol.pick[i] + 1;
        cout << "(" << cityId << "," << pointId << ")";
    }
    cout << "\n";
    return 0;
}