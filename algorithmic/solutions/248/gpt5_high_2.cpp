#include <bits/stdc++.h>
using namespace std;

struct City {
    int id;
    int x;
    vector<int> ys;
};

struct YResult {
    vector<int> selectedByCity; // index per city id
    double cost;
};

static inline double hypot_d(double dx, double dy) {
    return sqrt(dx*dx + dy*dy);
}

struct Timer {
    chrono::steady_clock::time_point st;
    Timer() { st = chrono::steady_clock::now(); }
    double elapsed() const {
        auto now = chrono::steady_clock::now();
        return chrono::duration<double>(now - st).count();
    }
};

const double INF = 1e100;
const double EPS = 1e-12;

static inline double edgeCostBetween(const City& A, int idxA, const City& B, int idxB, double wDist, double wSlope) {
    int dx = abs(A.x - B.x);
    int yA = A.ys[idxA], yB = B.ys[idxB];
    int dy = yB - yA;
    double dist = hypot_d((double)dx, (double)abs(dy));
    if (dy > 0 && dx == 0 && wSlope > 0) {
        return INF;
    }
    double slope = 0.0;
    if (dy > 0) {
        if (dx == 0) slope = 0.0;
        else slope = (double)dy / (double)dx;
    }
    double c = wDist * dist + wSlope * slope;
    return c;
}

YResult optimizeY(const vector<City>& cities, const vector<int>& order, double wDist, double wSlope) {
    int M = (int)order.size();
    vector<int> nopts(M);
    for (int i = 0; i < M; ++i) nopts[i] = (int)cities[order[i]].ys.size();

    // Precompute pairwise cost matrices for edges along the cycle
    vector<vector<vector<double>>> costPair(M);
    for (int p = 0; p < M; ++p) {
        int aIdx = order[p];
        int bIdx = order[(p + 1) % M];
        int na = (int)cities[aIdx].ys.size();
        int nb = (int)cities[bIdx].ys.size();
        costPair[p].assign(na, vector<double>(nb, 0.0));
        for (int a = 0; a < na; ++a) {
            for (int b = 0; b < nb; ++b) {
                costPair[p][a][b] = edgeCostBetween(cities[aIdx], a, cities[bIdx], b, wDist, wSlope);
            }
        }
    }

    double bestTotal = INF;
    int bestStart = -1;

    // Enumerate start option for city 0
    int n0 = nopts[0];
    for (int s = 0; s < n0; ++s) {
        // Initialize dp for position 1 (cost from 0->1)
        if (M == 1) {
            // Single city (though constraints say M>=2)
            double total = costPair[0][s][s];
            if (total < bestTotal) {
                bestTotal = total;
                bestStart = s;
            }
            continue;
        }
        int n1 = nopts[1];
        vector<double> dp(n1, INF);
        for (int b = 0; b < n1; ++b) {
            dp[b] = costPair[0][s][b];
        }
        // Forward DP through positions 1..M-2
        for (int p = 1; p <= M - 2; ++p) {
            int n_prev = nopts[p];
            int n_next = nopts[p + 1];
            vector<double> ndp(n_next, INF);
            // Cost pair at edge p (p -> p+1)
            auto& mat = costPair[p];
            for (int a = 0; a < n_prev; ++a) {
                double base = dp[a];
                if (base >= INF/2) continue;
                for (int b = 0; b < n_next; ++b) {
                    double cand = base + mat[a][b];
                    if (cand < ndp[b]) {
                        ndp[b] = cand;
                    }
                }
            }
            dp.swap(ndp);
        }
        // Close the cycle: last -> first
        int n_last = nopts[M - 1];
        auto& closeMat = costPair[M - 1]; // dims [n_last][n0]
        double total = INF;
        for (int a = 0; a < n_last; ++a) {
            double cand = dp[a] + closeMat[a][s];
            if (cand < total) total = cand;
        }
        if (total < bestTotal) {
            bestTotal = total;
            bestStart = s;
        }
    }

    // Reconstruct assignment for bestStart
    vector<int> assignPos(M, 0);
    if (bestStart == -1) {
        // Fallback: choose arbitrary minimal distance assignment sequentially
        // This shouldn't happen often; we'll just pick first option for each
        for (int i = 0; i < M; ++i) assignPos[i] = 0;
    } else {
        int s = bestStart;
        if (M == 1) {
            assignPos[0] = s;
        } else {
            int n1 = nopts[1];
            vector<double> dp(n1, INF);
            vector<vector<int>> prevIdx(M);
            prevIdx[0] = vector<int>(nopts[0], -1);
            prevIdx[1] = vector<int>(nopts[1], -1);
            for (int b = 0; b < n1; ++b) {
                dp[b] = costPair[0][s][b];
                prevIdx[1][b] = s;
            }
            // Forward DP with backpointers
            for (int p = 1; p <= M - 2; ++p) {
                int n_prev = nopts[p];
                int n_next = nopts[p + 1];
                vector<double> ndp(n_next, INF);
                prevIdx[p + 1] = vector<int>(n_next, -1);
                auto& mat = costPair[p];
                for (int a = 0; a < n_prev; ++a) {
                    double base = dp[a];
                    if (base >= INF/2) continue;
                    for (int b = 0; b < n_next; ++b) {
                        double cand = base + mat[a][b];
                        if (cand < ndp[b] - 1e-15) {
                            ndp[b] = cand;
                            prevIdx[p + 1][b] = a;
                        }
                    }
                }
                dp.swap(ndp);
            }
            // Closing step
            int bestLast = -1;
            double bestClose = INF;
            auto& closeMat = costPair[M - 1];
            for (int a = 0; a < nopts[M - 1]; ++a) {
                double cand = dp[a] + closeMat[a][s];
                if (cand < bestClose) {
                    bestClose = cand;
                    bestLast = a;
                }
            }
            // Reconstruct
            assignPos[M - 1] = bestLast;
            for (int p = M - 1; p >= 2; --p) {
                int a = assignPos[p];
                assignPos[p - 1] = prevIdx[p][a];
            }
            assignPos[0] = s;
        }
    }

    // Map to city id index
    vector<int> selectedByCity(cities.size(), 0);
    for (int pos = 0; pos < M; ++pos) {
        int cid = order[pos];
        selectedByCity[cid] = assignPos[pos];
    }

    // Compute final cost with these selections
    double totalCost = 0.0;
    for (int i = 0; i < M; ++i) {
        int aIdx = order[i];
        int bIdx = order[(i + 1) % M];
        int aOpt = selectedByCity[aIdx];
        int bOpt = selectedByCity[bIdx];
        double c = edgeCostBetween(cities[aIdx], aOpt, cities[bIdx], bOpt, wDist, wSlope);
        totalCost += c;
    }

    return { selectedByCity, totalCost };
}

vector<int> buildOrderSortedX(const vector<City>& cities, bool ascending) {
    int M = (int)cities.size();
    vector<int> ord(M);
    iota(ord.begin(), ord.end(), 0);
    sort(ord.begin(), ord.end(), [&](int a, int b){
        if (cities[a].x != cities[b].x) return ascending ? cities[a].x < cities[b].x : cities[a].x > cities[b].x;
        return cities[a].id < cities[b].id;
    });
    return ord;
}

vector<int> buildOrderNearestNeighbor(const vector<City>& cities, int start, const vector<double>& yRep) {
    int M = (int)cities.size();
    vector<int> order;
    order.reserve(M);
    vector<char> vis(M, 0);
    int cur = start;
    order.push_back(cur);
    vis[cur] = 1;

    while ((int)order.size() < M) {
        int best = -1;
        double bestd = 1e300;
        for (int j = 0; j < M; ++j) {
            if (vis[j]) continue;
            double dx = (double)abs(cities[cur].x - cities[j].x);
            double dy = fabs(yRep[cur] - yRep[j]);
            double d = hypot_d(dx, dy);
            if (d < bestd) {
                bestd = d;
                best = j;
            }
        }
        if (best == -1) break;
        order.push_back(best);
        vis[best] = 1;
        cur = best;
    }
    // In case of any unvisited due to some issue
    for (int i = 0; i < M; ++i) if (!vis[i]) order.push_back(i);
    return order;
}

double edgeCostFixedY(const vector<City>& cities, const vector<int>& order, const vector<int>& selByCity, int i, int j, double wDist, double wSlope) {
    const City& A = cities[order[i]];
    const City& B = cities[order[j]];
    int idxA = selByCity[A.id];
    int idxB = selByCity[B.id];
    return edgeCostBetween(A, idxA, B, idxB, wDist, wSlope);
}

bool twoOptPass(const vector<City>& cities, vector<int>& order, const vector<int>& selByCity, double wDist, double wSlope, Timer& timer, double timeLimit) {
    int M = (int)order.size();
    if (M < 4) return false;
    for (int i = 0; i < M; ++i) {
        if (timer.elapsed() > timeLimit) return false;
        int i1 = i;
        int i2 = (i + 1) % M;
        double c_i = edgeCostFixedY(cities, order, selByCity, i1, i2, wDist, wSlope);
        for (int j = i + 2; j < M; ++j) {
            if (i == 0 && j == M - 1) continue;
            int j1 = j;
            int j2 = (j + 1) % M;
            double c_j = edgeCostFixedY(cities, order, selByCity, j1, j2, wDist, wSlope);
            double c_new1 = edgeCostFixedY(cities, order, selByCity, i1, j1, wDist, wSlope);
            if (c_new1 >= INF/2) continue;
            double c_new2 = edgeCostFixedY(cities, order, selByCity, i2, j2, wDist, wSlope);
            if (c_new2 >= INF/2) continue;
            double delta = (c_new1 + c_new2) - (c_i + c_j);
            if (delta < -1e-12) {
                reverse(order.begin() + i + 1, order.begin() + j + 1);
                return true;
            }
        }
    }
    return false;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    double base;
    if (!(cin >> base)) {
        return 0;
    }

    int M;
    if (!(cin >> M)) {
        return 0;
    }

    vector<City> cities(M);
    for (int i = 0; i < M; ++i) {
        int n, x;
        cin >> n >> x;
        vector<int> ys(n);
        for (int j = 0; j < n; ++j) cin >> ys[j];
        cities[i].id = i;
        cities[i].x = x;
        cities[i].ys = move(ys);
    }

    double D_in, S_in;
    if (!(cin >> D_in >> S_in)) {
        // Fallback defaults if not provided
        D_in = 1.0;
        S_in = 1.0;
    }

    const double k = 0.6;
    double wDist = (D_in > 0 ? (1.0 - k) / D_in : (1.0 - k));
    double wSlope = (S_in > 0 ? k / S_in : k);

    // Representative y per city for initial construction (median)
    vector<double> yRep(M, 0.0);
    for (int i = 0; i < M; ++i) {
        vector<int> tmp = cities[i].ys;
        nth_element(tmp.begin(), tmp.begin() + tmp.size()/2, tmp.end());
        yRep[i] = (double)tmp[tmp.size()/2];
    }

    // Build initial candidate orders
    vector<vector<int>> candidates;
    candidates.push_back(buildOrderSortedX(cities, true));
    candidates.push_back(buildOrderSortedX(cities, false));

    // Nearest neighbor from different starts
    // leftmost, rightmost, median x, and two random starts (if time permits)
    vector<int> ordByX = buildOrderSortedX(cities, true);
    int startL = ordByX.front();
    int startR = ordByX.back();
    int startM = ordByX[ordByX.size()/2];
    candidates.push_back(buildOrderNearestNeighbor(cities, startL, yRep));
    candidates.push_back(buildOrderNearestNeighbor(cities, startR, yRep));
    candidates.push_back(buildOrderNearestNeighbor(cities, startM, yRep));

    // Random starts
    mt19937 rng((uint32_t)chrono::high_resolution_clock::now().time_since_epoch().count());
    uniform_int_distribution<int> distIdx(0, M - 1);
    for (int t = 0; t < 2; ++t) {
        int rs = distIdx(rng);
        candidates.push_back(buildOrderNearestNeighbor(cities, rs, yRep));
    }

    // Evaluate candidates with DP on y
    double bestCost = INF;
    vector<int> bestOrder;
    vector<int> bestSelByCity;

    for (auto& ord : candidates) {
        YResult res = optimizeY(cities, ord, wDist, wSlope);
        if (res.cost < bestCost) {
            bestCost = res.cost;
            bestOrder = ord;
            bestSelByCity = res.selectedByCity;
        }
    }

    // Improvement phase with 2-opt and re-optimizing y
    Timer timer;
    double timeLimit = 14.5; // seconds

    // If no candidates (shouldn't happen), fall back to sorted by x
    if (bestOrder.empty()) {
        bestOrder = buildOrderSortedX(cities, true);
        YResult res = optimizeY(cities, bestOrder, wDist, wSlope);
        bestSelByCity = res.selectedByCity;
        bestCost = res.cost;
    }

    // Iterative improvement
    while (timer.elapsed() < timeLimit) {
        bool improved = false;

        // Multiple 2-opt passes with fixed y
        while (timer.elapsed() < timeLimit) {
            bool any = twoOptPass(cities, bestOrder, bestSelByCity, wDist, wSlope, timer, timeLimit);
            if (!any) break;
            improved = true;
        }

        // Re-optimize y for the new order
        YResult newRes = optimizeY(cities, bestOrder, wDist, wSlope);
        if (newRes.cost + 1e-9 < bestCost) {
            bestCost = newRes.cost;
            bestSelByCity = newRes.selectedByCity;
            improved = true;
        }

        if (!improved) break;
    }

    // Ensure final y optimization on final order
    {
        YResult finalRes = optimizeY(cities, bestOrder, wDist, wSlope);
        bestSelByCity = finalRes.selectedByCity;
        bestCost = finalRes.cost;
    }

    // Output in required format
    // (city_id, landing_point_index) joined by "@"
    for (int i = 0; i < (int)bestOrder.size(); ++i) {
        int cid0 = bestOrder[i];
        int yidx = bestSelByCity[cid0];
        cout << "(" << (cid0 + 1) << "," << (yidx + 1) << ")";
        if (i + 1 < (int)bestOrder.size()) cout << "@";
    }
    cout << "\n";

    return 0;
}