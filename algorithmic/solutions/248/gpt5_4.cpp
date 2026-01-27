#include <bits/stdc++.h>
using namespace std;

struct City {
    int id;
    int x;
    vector<int> y;
    double yRep;
};

static const double K_WEIGHT = 0.6;
static const double INF = 1e100;

double computeMedian(const vector<int>& v) {
    int n = (int)v.size();
    vector<int> a = v;
    nth_element(a.begin(), a.begin() + n/2, a.end());
    if (n % 2 == 1) return (double)a[n/2];
    int mid1 = a[n/2];
    nth_element(a.begin(), a.begin() + n/2 - 1, a.end());
    int mid0 = a[n/2 - 1];
    return 0.5 * (mid0 + mid1);
}

vector<int> nearestNeighborRoute(const vector<City>& cities, const vector<vector<double>>& distMat) {
    int N = (int)cities.size();
    vector<int> route;
    route.reserve(N);
    vector<char> used(N, 0);
    // start at city with minimal x (tie: minimal yRep)
    int start = 0;
    for (int i = 1; i < N; ++i) {
        if (cities[i].x < cities[start].x || (cities[i].x == cities[start].x && cities[i].yRep < cities[start].yRep)) {
            start = i;
        }
    }
    route.push_back(start);
    used[start] = 1;
    for (int k = 1; k < N; ++k) {
        int last = route.back();
        int best = -1;
        double bestd = numeric_limits<double>::infinity();
        for (int j = 0; j < N; ++j) if (!used[j]) {
            double d = distMat[last][j];
            if (d < bestd) {
                bestd = d;
                best = j;
            }
        }
        route.push_back(best);
        used[best] = 1;
    }
    return route;
}

void twoOptRoute(vector<int>& route, const vector<vector<double>>& distMat, double timeLimitSec) {
    int N = (int)route.size();
    auto startTime = chrono::steady_clock::now();
    const double EPS = 1e-12;
    bool improved = true;
    while (improved) {
        improved = false;
        for (int i = 0; i < N && !improved; ++i) {
            int i1 = (i + 1) % N;
            for (int j = i + 2; j < N; ++j) {
                int j1 = (j + 1) % N;
                if (i == 0 && j == N - 1) continue;
                int a = route[i], b = route[i1], c = route[j], d = route[j1];
                double oldCost = distMat[a][b] + distMat[c][d];
                double newCost = distMat[a][c] + distMat[b][d];
                if (newCost + EPS < oldCost) {
                    reverse(route.begin() + i1, route.begin() + j + 1);
                    improved = true;
                    break;
                }
            }
        }
        if (chrono::duration<double>(chrono::steady_clock::now() - startTime).count() > timeLimitSec) break;
    }
}

double evaluateOrderAndSelectY(const vector<City>& cities, const vector<int>& order, double alpha, double beta, vector<int>& bestChoiceOut) {
    int N = (int)order.size();
    vector<int> nList(N);
    for (int i = 0; i < N; ++i) nList[i] = (int)cities[order[i]].y.size();

    // Precompute cost matrices for each adjacent pair (i -> i+1)
    vector<vector<vector<double>>> costMat(N);
    for (int i = 0; i < N; ++i) {
        int aIdx = order[i];
        int bIdx = order[(i + 1) % N];
        const auto& ya = cities[aIdx].y;
        const auto& yb = cities[bIdx].y;
        int na = (int)ya.size();
        int nb = (int)yb.size();
        costMat[i].assign(na, vector<double>(nb, 0.0));
        int dxAbs = abs(cities[aIdx].x - cities[bIdx].x);
        double dx = (double)dxAbs;
        for (int p = 0; p < na; ++p) {
            for (int q = 0; q < nb; ++q) {
                double dy = (double)yb[q] - (double)ya[p];
                double dist = hypot(dx, dy);
                double ascend;
                if (dxAbs == 0) {
                    ascend = (dy > 0.0) ? INF : 0.0;
                } else {
                    ascend = (dy > 0.0) ? (dy / dx) : 0.0;
                }
                costMat[i][p][q] = alpha * dist + beta * ascend;
            }
        }
    }

    int n0 = nList[0];
    double bestTotal = INF;
    vector<int> bestChoice(N, 0);

    vector<double> dpPrev, dpCurr;
    vector<vector<int>> par(N);
    for (int s = 0; s < n0; ++s) {
        dpPrev.assign(n0, INF);
        dpPrev[s] = 0.0;
        for (int idx = 1; idx < N; ++idx) {
            int prevN = nList[idx - 1];
            int currN = nList[idx];
            par[idx].assign(currN, -1);
            dpCurr.assign(currN, INF);
            const auto& mat = costMat[idx - 1]; // prevN x currN
            for (int j = 0; j < currN; ++j) {
                double bestVal = INF;
                int bestP = -1;
                for (int p = 0; p < prevN; ++p) {
                    double v = dpPrev[p] + mat[p][j];
                    if (v < bestVal) { bestVal = v; bestP = p; }
                }
                dpCurr[j] = bestVal;
                par[idx][j] = bestP;
            }
            dpPrev.swap(dpCurr);
        }
        // close the cycle
        int lastN = nList[N - 1];
        const auto& closeMat = costMat[N - 1]; // lastN x n0
        double bestCycle = INF;
        int bestLast = -1;
        for (int t = 0; t < lastN; ++t) {
            double v = dpPrev[t] + closeMat[t][s];
            if (v < bestCycle) { bestCycle = v; bestLast = t; }
        }
        if (bestCycle < bestTotal) {
            bestTotal = bestCycle;
            vector<int> choice(N, 0);
            choice[N - 1] = bestLast;
            for (int idx = N - 1; idx >= 1; --idx) {
                choice[idx - 1] = par[idx][choice[idx]];
            }
            choice[0] = s;
            bestChoice = choice;
        }
    }

    bestChoiceOut = bestChoice;
    return bestTotal;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    double base;
    if (!(cin >> base)) {
        return 0;
    }
    int M;
    cin >> M;
    vector<City> cities(M);
    for (int i = 0; i < M; ++i) {
        int n, x;
        cin >> n >> x;
        vector<int> y(n);
        for (int j = 0; j < n; ++j) cin >> y[j];
        cities[i].id = i + 1;
        cities[i].x = x;
        cities[i].y = move(y);
        cities[i].yRep = computeMedian(cities[i].y);
    }
    double D_orig, S_orig;
    cin >> D_orig >> S_orig;

    // Weights
    double alpha = (1.0 - K_WEIGHT) / D_orig;
    double beta = (K_WEIGHT) / S_orig;

    int N = M;
    vector<double> X(N), Y(N);
    for (int i = 0; i < N; ++i) {
        X[i] = (double)cities[i].x;
        Y[i] = cities[i].yRep;
    }

    // Precompute distance matrix for TSP heuristic on representative points
    vector<vector<double>> distMat(N, vector<double>(N, 0.0));
    for (int i = 0; i < N; ++i) {
        distMat[i][i] = 0.0;
        for (int j = i + 1; j < N; ++j) {
            double dx = X[i] - X[j];
            double dy = Y[i] - Y[j];
            double d = hypot(dx, dy);
            distMat[i][j] = distMat[j][i] = d;
        }
    }

    // Initial route via nearest neighbor
    vector<int> order = nearestNeighborRoute(cities, distMat);

    // 2-opt improvement on representative geometry
    double twoOptTimeLimitSec = 1.5; // modest time limit
    twoOptRoute(order, distMat, twoOptTimeLimitSec);

    // DP to select best landing points for fixed order
    vector<int> bestChoice;
    evaluateOrderAndSelectY(cities, order, alpha, beta, bestChoice);

    // Output in required format: (city_id, landing_point_index) separated by "@"
    for (int i = 0; i < N; ++i) {
        int cityIdx = order[i];
        int cityId = cities[cityIdx].id;
        int lpIdx = bestChoice[i] + 1; // 1-based
        cout << "(" << cityId << "," << lpIdx << ")";
        if (i + 1 < N) cout << "@";
    }
    cout << "\n";
    return 0;
}