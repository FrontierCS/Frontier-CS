#include <bits/stdc++.h>
using namespace std;

struct City {
    int x;
    vector<int> ys;
};

struct Solution {
    vector<int> order;     // permutation of city indices [0..M-1]
    vector<int> pickIdx;   // chosen landing point index per city [0..n_i-1]
    double cost;
};

double baseVal;
int M;
vector<City> cities;
double Dnorm, Snorm;
const double k_weight = 0.6;
double alphaW, betaW;

inline double edgeCost_pair(int ci, int yi_idx, int cj, int yj_idx) {
    const City& A = cities[ci];
    const City& B = cities[cj];
    double x1 = A.x, y1 = A.ys[yi_idx];
    double x2 = B.x, y2 = B.ys[yj_idx];
    double dx = x2 - x1;
    double dy = y2 - y1;
    double dist = hypot(dx, dy);
    double slope = 0.0;
    double adx = fabs(dx);
    if (dy > 0) {
        if (adx == 0.0) slope = 1e9;
        else slope = dy / adx;
    }
    return alphaW * dist + betaW * slope;
}

double tourCost(const vector<int>& order, const vector<int>& pickIdx) {
    int n = order.size();
    double sum = 0.0;
    for (int i = 0; i < n; ++i) {
        int a = order[i];
        int b = order[(i + 1) % n];
        sum += edgeCost_pair(a, pickIdx[a], b, pickIdx[b]);
    }
    return sum;
}

void optimizeY_givenOrder(const vector<int>& order, vector<int>& pickIdx, int passes = 8) {
    int n = order.size();
    // Initialize if uninitialized
    for (int i = 0; i < n; ++i) {
        int c = order[i];
        if (pickIdx[c] < 0) pickIdx[c] = 0;
    }
    for (int it = 0; it < passes; ++it) {
        bool changed = false;
        for (int idx = 0; idx < n; ++idx) {
            int cur = order[idx];
            int prev = order[(idx - 1 + n) % n];
            int next = order[(idx + 1) % n];
            int bestK = pickIdx[cur];
            double bestCost = 1e300;
            for (int k = 0; k < (int)cities[cur].ys.size(); ++k) {
                double c1 = edgeCost_pair(prev, pickIdx[prev], cur, k);
                double c2 = edgeCost_pair(cur, k, next, pickIdx[next]);
                double csum = c1 + c2;
                if (csum < bestCost) {
                    bestCost = csum;
                    bestK = k;
                }
            }
            if (bestK != pickIdx[cur]) {
                pickIdx[cur] = bestK;
                changed = true;
            }
        }
        if (!changed) break;
    }
}

double edgeCost_byOrderPos(const vector<int>& order, const vector<int>& pickIdx, int i, int j) {
    return edgeCost_pair(order[i], pickIdx[order[i]], order[j], pickIdx[order[j]]);
}

bool twoOptImprove(vector<int>& order, vector<int>& pickIdx) {
    int n = order.size();
    bool improved = false;
    // Precompute nothing; compute on the fly
    while (true) {
        bool any = false;
        for (int i = 0; i < n; ++i) {
            int i2 = (i + 1) % n;
            for (int k = i + 2; k < n; ++k) {
                int k2 = (k + 1) % n;
                if (k2 == i) continue; // don't break the tour length 2
                double a = edgeCost_byOrderPos(order, pickIdx, i, i2);
                double b = edgeCost_byOrderPos(order, pickIdx, k, k2);
                double c = edgeCost_byOrderPos(order, pickIdx, i, k);
                double d = edgeCost_byOrderPos(order, pickIdx, i2, k2);
                double delta = (c + d) - (a + b);
                if (delta < -1e-12) {
                    // reverse segment (i2..k)
                    if (i2 < k) {
                        reverse(order.begin() + i2, order.begin() + k + 1);
                    } else {
                        // If wrap-around (shouldn't happen because k>i+1 and linear indexing), but safe
                        vector<int> seg1(order.begin() + i2, order.end());
                        vector<int> seg2(order.begin(), order.begin() + k + 1);
                        reverse(seg1.begin(), seg1.end());
                        reverse(seg2.begin(), seg2.end());
                        vector<int> newOrder;
                        newOrder.insert(newOrder.end(), order.begin(), order.begin() + i2);
                        newOrder.insert(newOrder.end(), seg1.begin(), seg1.end());
                        newOrder.insert(newOrder.end(), seg2.begin(), seg2.end());
                        newOrder.insert(newOrder.end(), order.begin() + k + 1, order.begin() + i2);
                        order.swap(newOrder);
                    }
                    any = true;
                }
            }
        }
        if (!any) break;
        improved = true;
    }
    return improved;
}

Solution buildSolutionFromOrder(vector<int> order) {
    Solution sol;
    sol.order = move(order);
    sol.pickIdx.assign(M, -1);
    // Initialize pick by median y to avoid extreme slopes
    for (int i = 0; i < M; ++i) sol.pickIdx[i] = (int)cities[i].ys.size() / 2;

    optimizeY_givenOrder(sol.order, sol.pickIdx, 10);
    bool improved = true;
    int iter = 0;
    while (improved && iter < 5) {
        improved = twoOptImprove(sol.order, sol.pickIdx);
        optimizeY_givenOrder(sol.order, sol.pickIdx, 6);
        iter++;
    }
    // Final polish: one more Y optimization
    optimizeY_givenOrder(sol.order, sol.pickIdx, 10);
    sol.cost = tourCost(sol.order, sol.pickIdx);
    return sol;
}

vector<int> orderByX(bool ascending=true) {
    vector<int> idx(M);
    iota(idx.begin(), idx.end(), 0);
    sort(idx.begin(), idx.end(), [&](int a, int b){
        if (ascending) return cities[a].x < cities[b].x;
        else return cities[a].x > cities[b].x;
    });
    return idx;
}

vector<int> nearestNeighborOrder(int start) {
    int n = M;
    vector<int> order;
    order.reserve(n);
    vector<char> used(n, 0);
    int cur = start;
    order.push_back(cur);
    used[cur] = 1;
    // For NN, to avoid dependence on y, use x-distance only as heuristic
    for (int t = 1; t < n; ++t) {
        int best = -1;
        int xcur = cities[cur].x;
        int bestdx = INT_MAX;
        for (int j = 0; j < n; ++j) if (!used[j]) {
            int dx = abs(cities[j].x - xcur);
            if (dx < bestdx) {
                bestdx = dx;
                best = j;
            }
        }
        if (best == -1) {
            for (int j = 0; j < n; ++j) if (!used[j]) { best = j; break; }
        }
        order.push_back(best);
        used[best] = 1;
        cur = best;
    }
    return order;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    if (!(cin >> baseVal)) {
        return 0;
    }
    if (!(cin >> M)) {
        return 0;
    }
    cities.resize(M);
    for (int i = 0; i < M; ++i) {
        int n, x;
        cin >> n >> x;
        cities[i].x = x;
        cities[i].ys.resize(n);
        for (int j = 0; j < n; ++j) cin >> cities[i].ys[j];
    }
    cin >> Dnorm >> Snorm;
    alphaW = (1.0 - k_weight) / Dnorm;
    betaW  = (k_weight) / Snorm;

    // Build multiple starting orders
    vector<vector<int>> starts;
    starts.push_back(orderByX(true));
    starts.push_back(orderByX(false));
    // Start from three NN seeds: min x, max x, middle x
    int minx = 0, maxx = 0;
    for (int i = 1; i < M; ++i) {
        if (cities[i].x < cities[minx].x) minx = i;
        if (cities[i].x > cities[maxx].x) maxx = i;
    }
    vector<int> idx(M);
    iota(idx.begin(), idx.end(), 0);
    sort(idx.begin(), idx.end(), [&](int a, int b){ return cities[a].x < cities[b].x; });
    int midx = idx[M/2];

    starts.push_back(nearestNeighborOrder(minx));
    starts.push_back(nearestNeighborOrder(maxx));
    starts.push_back(nearestNeighborOrder(midx));

    Solution bestSol;
    bestSol.cost = 1e300;

    for (auto &ord : starts) {
        Solution s = buildSolutionFromOrder(ord);
        if (s.cost < bestSol.cost) bestSol = move(s);
    }

    // Output
    // Format: (city_id, landing_point_index) joined by "@"
    for (int i = 0; i < M; ++i) {
        int cityId = bestSol.order[i] + 1;
        int lpIdx = bestSol.pickIdx[bestSol.order[i]] + 1;
        cout << "(" << cityId << "," << lpIdx << ")";
        if (i + 1 < M) cout << "@";
    }
    cout << "\n";
    return 0;
}