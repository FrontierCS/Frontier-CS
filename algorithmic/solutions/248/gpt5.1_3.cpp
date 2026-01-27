#include <bits/stdc++.h>
using namespace std;

struct City {
    double x;
    vector<double> ys;
    double yAvg;
};

static const int MAX_K = 20;
static const double K_WEIGHT = 0.6;
static const double EPS = 1e-9;

uint64_t rng_state = 123456789ULL;
uint32_t nextRand() {
    rng_state ^= rng_state << 7;
    rng_state ^= rng_state >> 9;
    return (uint32_t)rng_state;
}
int randInt(int l, int r) {
    return l + (int)(nextRand() % (uint32_t)(r - l + 1));
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    double base;
    if (!(cin >> base)) return 0; // base is unused but read
    int M;
    cin >> M;

    vector<City> cities(M);
    for (int i = 0; i < M; ++i) {
        int n;
        double x;
        cin >> n >> x;
        cities[i].x = x;
        cities[i].ys.resize(n);
        double sumY = 0.0;
        for (int j = 0; j < n; ++j) {
            cin >> cities[i].ys[j];
            sumY += cities[i].ys[j];
        }
        cities[i].yAvg = sumY / n;
    }

    double D0, S0;
    cin >> D0 >> S0;

    double distWeight = (1.0 - K_WEIGHT) / (fabs(D0) < EPS ? 1.0 : D0);
    double slopeWeight = K_WEIGHT / (fabs(S0) < EPS ? 1.0 : S0);

    auto edgeCost = [&](int cityA, int idxA, int cityB, int idxB) -> double {
        const City &A = cities[cityA];
        const City &B = cities[cityB];
        double dx = fabs(B.x - A.x);
        double dy = B.ys[idxB] - A.ys[idxA];
        double dist = sqrt(dx * dx + dy * dy);
        double dxEff = dx < EPS ? EPS : dx;
        double slope = dy > 0.0 ? (dy / dxEff) : 0.0;
        return dist * distWeight + slope * slopeWeight;
    };

    // Precompute approximate distances between city centers (x, yAvg)
    vector<vector<double>> approxDist(M, vector<double>(M, 0.0));
    for (int i = 0; i < M; ++i) {
        for (int j = i + 1; j < M; ++j) {
            double dx = cities[i].x - cities[j].x;
            double dy = cities[i].yAvg - cities[j].yAvg;
            double d = sqrt(dx * dx + dy * dy);
            approxDist[i][j] = approxDist[j][i] = d;
        }
    }

    vector<int> baseOrder(M);
    for (int i = 0; i < M; ++i) baseOrder[i] = i;

    vector<int> orderAsc = baseOrder;
    sort(orderAsc.begin(), orderAsc.end(),
         [&](int a, int b) {
             if (cities[a].x != cities[b].x) return cities[a].x < cities[b].x;
             return a < b;
         });
    vector<int> orderDesc = orderAsc;
    reverse(orderDesc.begin(), orderDesc.end());

    auto twoOptImprove = [&](const vector<int>& initOrder) -> vector<int> {
        vector<int> route = initOrder;
        bool improved = true;
        int iter = 0;
        while (improved && iter < 1000) {
            improved = false;
            ++iter;
            for (int i = 0; i < M - 1; ++i) {
                for (int k = i + 2; k < M; ++k) {
                    if (i == 0 && k == M - 1) continue; // do not break the cycle
                    int a = route[i];
                    int b = route[i + 1];
                    int c = route[k];
                    int d = (k + 1 < M) ? route[k + 1] : route[0];
                    double oldCost = approxDist[a][b] + approxDist[c][d];
                    double newCost = approxDist[a][c] + approxDist[b][d];
                    if (newCost + 1e-9 < oldCost) {
                        reverse(route.begin() + i + 1, route.begin() + k + 1);
                        improved = true;
                    }
                }
            }
        }
        return route;
    };

    auto buildNearestNeighbor = [&](int startCity) -> vector<int> {
        vector<int> route;
        route.reserve(M);
        vector<char> used(M, 0);
        int cur = startCity;
        used[cur] = 1;
        route.push_back(cur);
        for (int step = 1; step < M; ++step) {
            int best = -1;
            double bestD = 1e100;
            for (int v = 0; v < M; ++v) {
                if (!used[v]) {
                    double d = approxDist[cur][v];
                    if (d < bestD) {
                        bestD = d;
                        best = v;
                    }
                }
            }
            used[best] = 1;
            route.push_back(best);
            cur = best;
        }
        return route;
    };

    vector<vector<int>> candidateOrders;

    auto addOrder = [&](const vector<int>& ord) {
        for (const auto& ex : candidateOrders) {
            if (ex.size() != ord.size()) continue;
            bool same = true;
            for (int i = 0; i < (int)ord.size(); ++i) {
                if (ex[i] != ord[i]) { same = false; break; }
            }
            if (same) return;
        }
        candidateOrders.push_back(ord);
    };

    addOrder(orderAsc);
    addOrder(orderDesc);

    vector<int> order2Opt = twoOptImprove(orderAsc);
    addOrder(order2Opt);
    vector<int> order2OptRev = order2Opt;
    reverse(order2OptRev.begin(), order2OptRev.end());
    addOrder(order2OptRev);

    vector<int> xOrder = orderAsc;
    int NN_count = min(M, 10);
    for (int i = 0; i < NN_count; ++i) {
        int start = xOrder[i];
        addOrder(buildNearestNeighbor(start));
    }
    for (int i = 0; i < NN_count; ++i) {
        int start = xOrder[M - 1 - i];
        addOrder(buildNearestNeighbor(start));
    }

    int randNN = 8;
    for (int i = 0; i < randNN; ++i) {
        int start = randInt(0, M - 1);
        addOrder(buildNearestNeighbor(start));
    }

    int randPerm = 8;
    for (int i = 0; i < randPerm; ++i) {
        vector<int> perm = baseOrder;
        for (int j = M - 1; j > 0; --j) {
            int k = randInt(0, j);
            swap(perm[j], perm[k]);
        }
        addOrder(perm);
    }

    double globalBestCost = 1e100;
    vector<int> bestOrder;
    vector<int> bestStates;

    for (const auto& order : candidateOrders) {
        int K0 = (int)cities[order[0]].ys.size();
        vector<int> K(M);
        for (int i = 0; i < M; ++i) K[i] = (int)cities[order[i]].ys.size();

        vector<vector<array<int16_t, MAX_K>>> prev(K0, vector<array<int16_t, MAX_K>>(M));
        vector<int> lastStateForS0(K0, -1);
        vector<double> dp_prev(MAX_K), dp_cur(MAX_K);

        double bestCostForOrder = 1e100;
        int bestS0 = 0;

        for (int s0 = 0; s0 < K0; ++s0) {
            for (int i = 0; i < K[0]; ++i) dp_prev[i] = 1e100;
            dp_prev[s0] = 0.0;

            for (int pos = 1; pos < M; ++pos) {
                int Kp = K[pos - 1];
                int Kc = K[pos];
                for (int sj = 0; sj < Kc; ++sj) {
                    double bestC = 1e100;
                    int bestPrev = -1;
                    for (int si = 0; si < Kp; ++si) {
                        double c = dp_prev[si] + edgeCost(order[pos - 1], si, order[pos], sj);
                        if (c < bestC) {
                            bestC = c;
                            bestPrev = si;
                        }
                    }
                    dp_cur[sj] = bestC;
                    prev[s0][pos][sj] = (int16_t)bestPrev;
                }
                // swap dp_prev and dp_cur
                for (int i = 0; i < Kc; ++i) dp_prev[i] = dp_cur[i];
            }

            int Klast = K[M - 1];
            double bestCycle = 1e100;
            int bestLast = -1;
            for (int sl = 0; sl < Klast; ++sl) {
                double tot = dp_prev[sl] + edgeCost(order[M - 1], sl, order[0], s0);
                if (tot < bestCycle) {
                    bestCycle = tot;
                    bestLast = sl;
                }
            }
            lastStateForS0[s0] = bestLast;

            if (bestCycle < bestCostForOrder) {
                bestCostForOrder = bestCycle;
                bestS0 = s0;
            }
        }

        if (bestCostForOrder < globalBestCost) {
            globalBestCost = bestCostForOrder;
            bestOrder = order;
            bestStates.assign(M, 0);
            bestStates[M - 1] = lastStateForS0[bestS0];
            for (int pos = M - 1; pos >= 1; --pos) {
                int curState = bestStates[pos];
                int prevState = prev[bestS0][pos][curState];
                bestStates[pos - 1] = prevState;
            }
        }
    }

    // Output the best route
    for (int i = 0; i < M; ++i) {
        int cityId = bestOrder[i] + 1;
        int landingIdx = bestStates[i] + 1;
        cout << "(" << cityId << "," << landingIdx << ")";
        if (i + 1 < M) cout << "@";
    }
    cout << '\n';

    return 0;
}