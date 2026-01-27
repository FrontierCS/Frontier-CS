#include <bits/stdc++.h>
using namespace std;

struct City {
    int id;
    int x;
    vector<int> ys;
};

struct Solution {
    vector<int> order; // indices into cities vector
    vector<int> landingIdx; // per position in order, landing point index (0-based)
    double cost;
};

static inline double edge_cost(const City& a, int ia, const City& b, int ib, double wdist, double wslope) {
    double x1 = a.x, y1 = a.ys[ia];
    double x2 = b.x, y2 = b.ys[ib];
    double dx = fabs(x2 - x1);
    double dy = fabs(y2 - y1);
    double dist = sqrt(dx * dx + dy * dy);
    double slope = 0.0;
    if (dx == 0.0) {
        if (y2 > y1) slope = 1e9; // penalize pure upward vertical move heavily
        else slope = 0.0;
    } else {
        double s = (y2 - y1) / dx;
        if (s > 0) slope = s;
    }
    return wdist * dist + wslope * slope;
}

Solution solve_order(const vector<City>& cities, const vector<int>& ord, double wdist, double wslope) {
    int M = (int)ord.size();
    // sizes per city
    vector<int> sz(M);
    for (int i = 0; i < M; ++i) sz[i] = (int)cities[ord[i]].ys.size();

    Solution bestSol;
    bestSol.cost = numeric_limits<double>::infinity();

    // For each starting landing point option
    for (int start_idx = 0; start_idx < sz[0]; ++start_idx) {
        // dp[i][j]: min cost up to city i choosing landing j at i
        vector<vector<double>> dp(M, vector<double>());
        vector<vector<int>> par(M, vector<int>());
        dp[0].assign(sz[0], numeric_limits<double>::infinity());
        par[0].assign(sz[0], -1);
        dp[0][start_idx] = 0.0;

        for (int i = 1; i < M; ++i) {
            dp[i].assign(sz[i], numeric_limits<double>::infinity());
            par[i].assign(sz[i], -1);
            const City& prevC = cities[ord[i-1]];
            const City& curC = cities[ord[i]];
            for (int jb = 0; jb < sz[i]; ++jb) {
                double bestVal = numeric_limits<double>::infinity();
                int bestA = -1;
                for (int ja = 0; ja < sz[i-1]; ++ja) {
                    if (dp[i-1][ja] == numeric_limits<double>::infinity()) continue;
                    double w = edge_cost(prevC, ja, curC, jb, wdist, wslope);
                    double val = dp[i-1][ja] + w;
                    if (val < bestVal) {
                        bestVal = val;
                        bestA = ja;
                    }
                }
                dp[i][jb] = bestVal;
                par[i][jb] = bestA;
            }
        }

        // add closure cost
        const City& lastC = cities[ord[M-1]];
        const City& firstC = cities[ord[0]];
        double bestTotal = numeric_limits<double>::infinity();
        int bestEnd = -1;
        for (int end_idx = 0; end_idx < sz[M-1]; ++end_idx) {
            if (dp[M-1][end_idx] == numeric_limits<double>::infinity()) continue;
            double closeCost = edge_cost(lastC, end_idx, firstC, start_idx, wdist, wslope);
            double total = dp[M-1][end_idx] + closeCost;
            if (total < bestTotal) {
                bestTotal = total;
                bestEnd = end_idx;
            }
        }

        if (bestEnd >= 0 && bestTotal < bestSol.cost) {
            bestSol.cost = bestTotal;
            bestSol.order = ord;
            bestSol.landingIdx.assign(M, -1);
            // reconstruct
            int cur = bestEnd;
            for (int i = M-1; i >= 1; --i) {
                bestSol.landingIdx[i] = cur;
                cur = par[i][cur];
                if (cur < 0) break;
            }
            bestSol.landingIdx[0] = start_idx;
        }
    }

    return bestSol;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    // Read input
    double base;
    if (!(cin >> base)) {
        return 0;
    }
    int M;
    if (!(cin >> M)) {
        // If format without base, treat 'base' as M and set base dummy
        M = (int)base;
        base = 0.0;
    }

    vector<City> cities;
    cities.reserve(M);
    for (int i = 0; i < M; ++i) {
        int n, x;
        cin >> n >> x;
        vector<int> ys(n);
        for (int j = 0; j < n; ++j) cin >> ys[j];
        cities.push_back(City{i+1, x, move(ys)});
    }
    double Dnorm, Snorm;
    if (!(cin >> Dnorm >> Snorm)) {
        // Default to 1 if missing
        Dnorm = 1.0; Snorm = 1.0;
    }

    double k = 0.6;
    double wdist = (1.0 - k) / (Dnorm == 0.0 ? 1.0 : Dnorm);
    double wslope = k / (Snorm == 0.0 ? 1.0 : Snorm);

    // Two orders: increasing x and decreasing x (tie-break by city id)
    vector<int> ord_inc(M), ord_dec(M);
    iota(ord_inc.begin(), ord_inc.end(), 0);
    stable_sort(ord_inc.begin(), ord_inc.end(), [&](int a, int b){
        if (cities[a].x != cities[b].x) return cities[a].x < cities[b].x;
        return cities[a].id < cities[b].id;
    });
    ord_dec = ord_inc;
    reverse(ord_dec.begin(), ord_dec.end());

    Solution sol_inc = solve_order(cities, ord_inc, wdist, wslope);
    Solution sol_dec = solve_order(cities, ord_dec, wdist, wslope);
    Solution best = (sol_inc.cost <= sol_dec.cost ? sol_inc : sol_dec);

    // Output route: (city_id, landing_point_index) joined by @
    // landing_point_index is 1-based
    for (int i = 0; i < M; ++i) {
        int cityIdx = best.order[i];
        int landing = best.landingIdx[i];
        if (landing < 0) landing = 0;
        cout << "(" << cities[cityIdx].id << "," << (landing + 1) << ")";
        if (i + 1 < M) cout << "@";
    }
    return 0;
}