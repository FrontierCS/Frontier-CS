#include <bits/stdc++.h>
using namespace std;

struct City {
    int id; // 1-based
    int x;
    vector<int> ys;
    int maxY() const {
        return *max_element(ys.begin(), ys.end());
    }
};

static inline double slopeUp(int dy, int dxAbs) {
    if (dy <= 0) return 0.0;
    if (dxAbs == 0) return 1e9 + dy;
    return (double)dy / (double)dxAbs;
}

struct BestDP {
    double cost = 1e100;
    vector<int> opts; // 0-based landing index per position in order
};

struct Solver {
    double base = 0;
    int M = 0;
    vector<City> cities;
    int Dorig = 1, Sorig = 1;
    const double k = 0.6;
    double wDist = 0.4, wSlope = 0.6;

    vector<vector<double>> minCost; // city -> city directed optimistic min edge cost

    double edgeCost(int ci, int oi, int cj, int oj) const {
        const City &A = cities[ci];
        const City &B = cities[cj];
        int dx = abs(A.x - B.x);
        int dy = B.ys[oj] - A.ys[oi];
        double dist = sqrt((double)dx * (double)dx + (double)dy * (double)dy);
        double slope = slopeUp(dy, dx);
        return wDist * dist + wSlope * slope;
    }

    BestDP solveDP(const vector<int> &order) const {
        const double INF = 1e100;
        int startCity = order[0];
        int n0 = (int)cities[startCity].ys.size();

        BestDP best;
        best.opts.assign(M, 0);

        for (int s = 0; s < n0; s++) {
            vector<vector<int>> par(M);
            par[0].assign(n0, -1);

            vector<double> dpPrev(n0, INF), dpCur;
            dpPrev[s] = 0.0;

            for (int pos = 1; pos < M; pos++) {
                int prevCity = order[pos - 1];
                int curCity = order[pos];
                int np = (int)cities[prevCity].ys.size();
                int nc = (int)cities[curCity].ys.size();
                par[pos].assign(nc, -1);
                dpCur.assign(nc, INF);

                for (int b = 0; b < nc; b++) {
                    double bestVal = INF;
                    int bestA = -1;
                    for (int a = 0; a < np; a++) {
                        double val = dpPrev[a] + edgeCost(prevCity, a, curCity, b);
                        if (val < bestVal) {
                            bestVal = val;
                            bestA = a;
                        }
                    }
                    dpCur[b] = bestVal;
                    par[pos][b] = bestA;
                }
                dpPrev.swap(dpCur);
            }

            int lastCity = order[M - 1];
            int nLast = (int)cities[lastCity].ys.size();
            double bestTotal = INF;
            int bestLastOpt = -1;
            for (int a = 0; a < nLast; a++) {
                double total = dpPrev[a] + edgeCost(lastCity, a, startCity, s);
                if (total < bestTotal) {
                    bestTotal = total;
                    bestLastOpt = a;
                }
            }

            if (bestTotal < best.cost) {
                best.cost = bestTotal;
                vector<int> opts(M, 0);
                opts[M - 1] = bestLastOpt;
                for (int pos = M - 1; pos >= 1; pos--) {
                    opts[pos - 1] = par[pos][opts[pos]];
                }
                // opts[0] should be s
                best.opts.swap(opts);
            }
        }

        return best;
    }

    static void rotateToStart(vector<int> &order, int startCity) {
        int M = (int)order.size();
        int idx = -1;
        for (int i = 0; i < M; i++) {
            if (order[i] == startCity) {
                idx = i;
                break;
            }
        }
        if (idx <= 0) return;
        vector<int> rot;
        rot.reserve(M);
        for (int i = 0; i < M; i++) rot.push_back(order[(idx + i) % M]);
        order.swap(rot);
    }

    static double swapDelta(const vector<int> &order, int i, int j, const vector<vector<double>> &C) {
        int M = (int)order.size();
        if (i == j) return 0.0;
        if (i > j) swap(i, j);
        // i and j are positions, 0 <= i < j < M
        int a = order[(i - 1 + M) % M];
        int b = order[i];
        int c = order[(i + 1) % M];
        int d = order[(j - 1 + M) % M];
        int e = order[j];
        int f = order[(j + 1) % M];

        if (i + 1 == j) {
            // a -> b -> e -> f  becomes a -> e -> b -> f
            double oldCost = C[a][b] + C[b][e] + C[e][f];
            double newCost = C[a][e] + C[e][b] + C[b][f];
            return newCost - oldCost;
        } else {
            // a -> b -> c, d -> e -> f become a -> e -> c, d -> b -> f
            double oldCost = C[a][b] + C[b][c] + C[d][e] + C[e][f];
            double newCost = C[a][e] + C[e][c] + C[d][b] + C[b][f];
            return newCost - oldCost;
        }
    }

    static void improveBySwaps(vector<int> &order, const vector<vector<double>> &C, int maxPasses = 20) {
        const double EPS = 1e-12;
        int M = (int)order.size();
        for (int pass = 0; pass < maxPasses; pass++) {
            bool improved = false;
            for (int i = 1; i < M; i++) {
                for (int j = i + 1; j < M; j++) {
                    double d = swapDelta(order, i, j, C);
                    if (d < -EPS) {
                        swap(order[i], order[j]);
                        improved = true;
                    }
                }
            }
            if (!improved) break;
        }
    }

    vector<int> nearestNeighborTour(int start) const {
        const double INF = 1e100;
        vector<int> order;
        order.reserve(M);
        vector<char> vis(M, 0);
        int cur = start;
        vis[cur] = 1;
        order.push_back(cur);

        for (int step = 1; step < M; step++) {
            int bestJ = -1;
            double bestC = INF;
            for (int j = 0; j < M; j++) {
                if (vis[j]) continue;
                double c = minCost[cur][j];
                if (c < bestC) {
                    bestC = c;
                    bestJ = j;
                }
            }
            if (bestJ == -1) {
                for (int j = 0; j < M; j++) if (!vis[j]) { bestJ = j; break; }
            }
            vis[bestJ] = 1;
            order.push_back(bestJ);
            cur = bestJ;
        }
        return order;
    }

    void readInput() {
        ios::sync_with_stdio(false);
        cin.tie(nullptr);

        if (!(cin >> base)) exit(0);
        cin >> M;
        cities.resize(M);
        for (int i = 0; i < M; i++) {
            int n, x;
            cin >> n >> x;
            cities[i].id = i + 1;
            cities[i].x = x;
            cities[i].ys.resize(n);
            for (int j = 0; j < n; j++) cin >> cities[i].ys[j];
        }
        cin >> Dorig >> Sorig;
        if (Dorig <= 0) Dorig = 1;
        if (Sorig <= 0) Sorig = 1;
        wDist = (1.0 - k) / (double)Dorig;
        wSlope = k / (double)Sorig;
    }

    void buildMinCostMatrix() {
        const double INF = 1e100;
        minCost.assign(M, vector<double>(M, INF));
        for (int i = 0; i < M; i++) minCost[i][i] = INF;

        for (int i = 0; i < M; i++) {
            for (int j = i + 1; j < M; j++) {
                int dx = abs(cities[i].x - cities[j].x);
                double dx2 = (double)dx * (double)dx;
                double best_ij = INF;
                double best_ji = INF;
                const auto &Yi = cities[i].ys;
                const auto &Yj = cities[j].ys;

                for (int yi : Yi) {
                    for (int yj : Yj) {
                        int dy = yj - yi;
                        double dist = sqrt(dx2 + (double)dy * (double)dy);
                        double slope_ij = slopeUp(dy, dx);
                        double slope_ji = slopeUp(-dy, dx);
                        double c_ij = wDist * dist + wSlope * slope_ij;
                        double c_ji = wDist * dist + wSlope * slope_ji;
                        if (c_ij < best_ij) best_ij = c_ij;
                        if (c_ji < best_ji) best_ji = c_ji;
                    }
                }
                minCost[i][j] = best_ij;
                minCost[j][i] = best_ji;
            }
        }
    }

    pair<vector<int>, vector<int>> solve() {
        int start = 0;
        for (int i = 1; i < M; i++) {
            if (cities[i].x < cities[start].x) start = i;
            else if (cities[i].x == cities[start].x && cities[i].id < cities[start].id) start = i;
        }

        vector<int> xOrder(M);
        iota(xOrder.begin(), xOrder.end(), 0);
        sort(xOrder.begin(), xOrder.end(), [&](int a, int b) {
            if (cities[a].x != cities[b].x) return cities[a].x < cities[b].x;
            int ma = cities[a].maxY();
            int mb = cities[b].maxY();
            if (ma != mb) return ma > mb;
            return cities[a].id < cities[b].id;
        });

        vector<vector<int>> candidates;
        candidates.push_back(xOrder);
        {
            vector<int> rev = xOrder;
            reverse(rev.begin(), rev.end());
            candidates.push_back(rev);
        }
        {
            vector<int> nn = nearestNeighborTour(start);
            candidates.push_back(nn);
            vector<int> rev = nn;
            reverse(rev.begin(), rev.end());
            candidates.push_back(rev);
        }

        // Deduplicate candidates
        auto canonical = [&](vector<int> ord) {
            rotateToStart(ord, start);
            return ord;
        };
        vector<vector<int>> uniq;
        for (auto &c : candidates) {
            auto ord = canonical(c);
            bool seen = false;
            for (auto &u : uniq) if (u == ord) { seen = true; break; }
            if (!seen) uniq.push_back(ord);
        }

        double bestCost = 1e100;
        vector<int> bestOrder, bestOpts;

        for (auto &ord0 : uniq) {
            vector<int> ord = ord0;
            rotateToStart(ord, start);
            improveBySwaps(ord, minCost, 15);

            BestDP dp = solveDP(ord);
            if (dp.cost < bestCost) {
                bestCost = dp.cost;
                bestOrder = ord;
                bestOpts = dp.opts;
            }
        }

        if (bestOrder.empty()) {
            bestOrder = xOrder;
            rotateToStart(bestOrder, start);
            BestDP dp = solveDP(bestOrder);
            bestOpts = dp.opts;
        }

        return {bestOrder, bestOpts};
    }
};

int main() {
    Solver solver;
    solver.readInput();
    solver.buildMinCostMatrix();
    auto [order, opts] = solver.solve();

    for (int i = 0; i < (int)order.size(); i++) {
        int cityIdx = order[i];
        int landIdx = opts[i];
        cout << "(" << (cityIdx + 1) << "," << (landIdx + 1) << ")";
        if (i + 1 < (int)order.size()) cout << "@";
    }
    cout << "\n";
    return 0;
}