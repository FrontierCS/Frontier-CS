#include <bits/stdc++.h>
using namespace std;

struct City {
    int x;
    vector<int> y;
};

static constexpr double K_WEIGHT = 0.6;
static constexpr double INF_SLOPE = 1e12;
static constexpr double EPS_IMPROVE = 1e-12;

int M;
vector<City> cities;
vector<vector<double>> dx; // horizontal distance abs(xi - xj)

double Dnorm = 1.0, Snorm = 1.0;
double alpha_w = 1.0, beta_w = 1.0;

vector<int> order_cur, posOf_cur, idxSel_cur;
double totalCost_cur = 0.0;

vector<int> order_best, idxSel_best;
double totalCost_best = numeric_limits<double>::infinity();

inline int prevPos(int p) { return (p == 0) ? (M - 1) : (p - 1); }
inline int nextPos(int p) { return (p + 1 == M) ? 0 : (p + 1); }

inline double edgeCost(int fromCity, int fromIdx, int toCity, int toIdx) {
    double dxv = dx[fromCity][toCity];
    double dy = (double)cities[toCity].y[toIdx] - (double)cities[fromCity].y[fromIdx];
    double dist = sqrt(dxv * dxv + dy * dy);
    double slope = 0.0;
    if (dy > 0) {
        slope = (dxv > 0.0) ? (dy / dxv) : INF_SLOPE;
    }
    return alpha_w * dist + beta_w * slope;
}

double computeTotalCost(const vector<int>& order, const vector<int>& idxSel) {
    double s = 0.0;
    for (int i = 0; i < M; ++i) {
        int u = order[i];
        int v = order[nextPos(i)];
        s += edgeCost(u, idxSel[u], v, idxSel[v]);
    }
    return s;
}

void setOrder(const vector<int>& ord) {
    order_cur = ord;
    posOf_cur.assign(M, -1);
    for (int i = 0; i < M; ++i) posOf_cur[order_cur[i]] = i;
}

void initIdxMinY(vector<int>& idxSel) {
    idxSel.assign(M, 0);
    for (int i = 0; i < M; ++i) {
        int best = 0;
        int bestY = cities[i].y[0];
        for (int j = 1; j < (int)cities[i].y.size(); ++j) {
            if (cities[i].y[j] < bestY) {
                bestY = cities[i].y[j];
                best = j;
            }
        }
        idxSel[i] = best;
    }
}

bool improveCityPoint(int cid, vector<int>& idxSel, double& totalCost) {
    int pos = posOf_cur[cid];
    int preC = order_cur[prevPos(pos)];
    int nxtC = order_cur[nextPos(pos)];
    int curIdx = idxSel[cid];

    double oldCost = edgeCost(preC, idxSel[preC], cid, curIdx) + edgeCost(cid, curIdx, nxtC, idxSel[nxtC]);

    double bestCost = oldCost;
    int bestIdx = curIdx;

    const vector<int>& ys = cities[cid].y;
    for (int j = 0; j < (int)ys.size(); ++j) {
        if (j == curIdx) continue;
        double cst = edgeCost(preC, idxSel[preC], cid, j) + edgeCost(cid, j, nxtC, idxSel[nxtC]);
        if (cst + EPS_IMPROVE < bestCost) {
            bestCost = cst;
            bestIdx = j;
        }
    }

    if (bestIdx != curIdx) {
        idxSel[cid] = bestIdx;
        totalCost += (bestCost - oldCost);
        return true;
    }
    return false;
}

void improvePointsAll(vector<int>& idxSel, double& totalCost, int maxPasses = 10) {
    for (int pass = 0; pass < maxPasses; ++pass) {
        bool improved = false;
        for (int i = 0; i < M; ++i) {
            int cid = order_cur[i];
            improved |= improveCityPoint(cid, idxSel, totalCost);
        }
        if (!improved) break;
    }
}

void improvePointsLocal(const vector<int>& citySet, vector<int>& idxSel, double& totalCost, int rounds = 2) {
    // make a unique list
    vector<int> cs = citySet;
    sort(cs.begin(), cs.end());
    cs.erase(unique(cs.begin(), cs.end()), cs.end());
    for (int r = 0; r < rounds; ++r) {
        bool improved = false;
        for (int cid : cs) {
            improved |= improveCityPoint(cid, idxSel, totalCost);
        }
        if (!improved) break;
    }
}

double calcSwapDelta(int p, int q, const vector<int>& order, const vector<int>& idxSel) {
    if (p == q) return 0.0;
    int prevP = prevPos(p);
    int prevQ = prevPos(q);
    vector<int> S = {prevP, p, prevQ, q};
    sort(S.begin(), S.end());
    S.erase(unique(S.begin(), S.end()), S.end());

    auto cityAfterAt = [&](int pos)->int {
        if (pos == p) return order[q];
        if (pos == q) return order[p];
        return order[pos];
    };

    double oldSum = 0.0, newSum = 0.0;

    for (int s : S) {
        int to = nextPos(s);
        int fromOld = order[s];
        int toOld = order[to];
        oldSum += edgeCost(fromOld, idxSel[fromOld], toOld, idxSel[toOld]);

        int fromNew = cityAfterAt(s);
        int toNew = cityAfterAt(to);
        newSum += edgeCost(fromNew, idxSel[fromNew], toNew, idxSel[toNew]);
    }
    return newSum - oldSum;
}

void applySwap(int p, int q, vector<int>& order, vector<int>& posOf) {
    int A = order[p], B = order[q];
    swap(order[p], order[q]);
    posOf[A] = q;
    posOf[B] = p;
}

void localImproveAfterSwap(int p, int q, vector<int>& idxSel, double& totalCost) {
    // Build local city set around p and q after swap
    vector<int> posList;
    posList.reserve(8);
    posList.push_back(prevPos(p));
    posList.push_back(p);
    posList.push_back(nextPos(p));
    posList.push_back(prevPos(q));
    posList.push_back(q);
    posList.push_back(nextPos(q));
    vector<int> citySet;
    citySet.reserve(12);
    for (int pos : posList) {
        citySet.push_back(order_cur[pos]);
    }
    // also include neighbors of these cities (2-depth local)
    vector<int> more;
    for (int pos : posList) {
        int a = order_cur[prevPos(pos)];
        int b = order_cur[nextPos(pos)];
        more.push_back(a);
        more.push_back(b);
    }
    citySet.insert(citySet.end(), more.begin(), more.end());
    improvePointsLocal(citySet, idxSel, totalCost, 3);
}

void swapImprovementSweep(vector<int>& idxSel, double& totalCost, double timeLimitMs, chrono::steady_clock::time_point startTime) {
    bool improvedAny = true;
    int passCount = 0;
    while (improvedAny) {
        improvedAny = false;
        ++passCount;
        for (int p = 0; p < M; ++p) {
            for (int q = p + 1; q < M; ++q) {
                auto now = chrono::steady_clock::now();
                double ms = chrono::duration<double, milli>(now - startTime).count();
                if (ms > timeLimitMs) return;

                double delta = calcSwapDelta(p, q, order_cur, idxSel);
                if (delta < -EPS_IMPROVE) {
                    totalCost += delta;
                    applySwap(p, q, order_cur, posOf_cur);
                    localImproveAfterSwap(p, q, idxSel, totalCost);
                    improvedAny = true;
                }
            }
        }
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    double base;
    if (!(cin >> base)) {
        return 0;
    }
    cin >> M;
    cities.resize(M);
    for (int i = 0; i < M; ++i) {
        int n, x;
        cin >> n >> x;
        cities[i].x = x;
        cities[i].y.resize(n);
        for (int j = 0; j < n; ++j) cin >> cities[i].y[j];
    }
    // Read normalization D and S (original)
    double D_original = 1.0, S_original = 1.0;
    if (!(cin >> D_original >> S_original)) {
        D_original = 1.0;
        S_original = 1.0;
    }
    // Preprocess weights consistent with scoring
    // userCost = total_dist * ((1-k)/D_original) + total_slope * (k/S_original)
    alpha_w = (1.0 - K_WEIGHT) / D_original;
    beta_w = K_WEIGHT / S_original;

    dx.assign(M, vector<double>(M, 0.0));
    for (int i = 0; i < M; ++i) {
        for (int j = 0; j < M; ++j) {
            dx[i][j] = fabs((double)cities[i].x - (double)cities[j].x);
        }
    }

    // Build initial orders: by x ascending and descending
    vector<int> ordAsc(M);
    iota(ordAsc.begin(), ordAsc.end(), 0);
    sort(ordAsc.begin(), ordAsc.end(), [&](int a, int b) {
        if (cities[a].x != cities[b].x) return cities[a].x < cities[b].x;
        return a < b;
    });
    vector<int> ordDesc = ordAsc;
    reverse(ordDesc.begin(), ordDesc.end());

    // Time management
    auto startTime = chrono::steady_clock::now();
    double totalTimeLimitMs = 14800.0; // 14.8 seconds
    double prepTimeMs = 1200.0; // reserve for finishing

    // Evaluate both orders
    vector<vector<int>> candidatesOrders = {ordAsc, ordDesc};

    for (size_t oidx = 0; oidx < candidatesOrders.size(); ++oidx) {
        setOrder(candidatesOrders[oidx]);
        initIdxMinY(idxSel_cur);
        totalCost_cur = computeTotalCost(order_cur, idxSel_cur);
        improvePointsAll(idxSel_cur, totalCost_cur, 10);

        // Swap improvements with limited time
        auto now = chrono::steady_clock::now();
        double elapsed = chrono::duration<double, milli>(now - startTime).count();
        double remaining = max(0.0, totalTimeLimitMs - elapsed - prepTimeMs);
        if (remaining > 50.0) {
            swapImprovementSweep(idxSel_cur, totalCost_cur, elapsed + remaining, startTime);
        }

        // Record best
        if (totalCost_cur + EPS_IMPROVE < totalCost_best) {
            totalCost_best = totalCost_cur;
            order_best = order_cur;
            idxSel_best = idxSel_cur;
        }
    }

    // Optional random restarts if time permits
    std::mt19937_64 rng(chrono::high_resolution_clock::now().time_since_epoch().count());
    int randomRestarts = 2;
    for (int r = 0; r < randomRestarts; ++r) {
        auto now = chrono::steady_clock::now();
        double elapsed = chrono::duration<double, milli>(now - startTime).count();
        if (elapsed > totalTimeLimitMs - prepTimeMs) break;

        vector<int> ordRandom = ordAsc;
        shuffle(ordRandom.begin(), ordRandom.end(), rng);
        setOrder(ordRandom);
        initIdxMinY(idxSel_cur);
        totalCost_cur = computeTotalCost(order_cur, idxSel_cur);
        improvePointsAll(idxSel_cur, totalCost_cur, 8);

        now = chrono::steady_clock::now();
        elapsed = chrono::duration<double, milli>(now - startTime).count();
        double remaining = max(0.0, totalTimeLimitMs - elapsed - prepTimeMs);
        if (remaining > 50.0) {
            swapImprovementSweep(idxSel_cur, totalCost_cur, elapsed + remaining, startTime);
        }

        if (totalCost_cur + EPS_IMPROVE < totalCost_best) {
            totalCost_best = totalCost_cur;
            order_best = order_cur;
            idxSel_best = idxSel_cur;
        }
    }

    // Output best solution
    // Format: (city_id, landing_point_index) separated by "@"
    // city_id and landing_point_index are 1-based
    for (int i = 0; i < M; ++i) {
        int cid = order_best[i];
        int lid = idxSel_best[cid];
        cout << "(" << (cid + 1) << "," << (lid + 1) << ")";
        if (i + 1 < M) cout << "@";
    }
    cout << "\n";
    return 0;
}