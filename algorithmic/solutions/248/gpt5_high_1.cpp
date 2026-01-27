#include <bits/stdc++.h>
using namespace std;

struct City {
    int id;
    int x;
    vector<int> y;
};

static const double K_WEIGHT = 0.6;
static const double INF = 1e100;

bool hasDecimalOrExp(const string& s) {
    for (char c : s) {
        if (c == '.' || c == 'e' || c == 'E') return true;
    }
    return false;
}

pair<double, vector<int>> solveOrder(const vector<City>& cities, const vector<int>& order, double wD, double wS) {
    int M = (int)order.size();
    if (M == 0) return {0.0, {}};

    // Precompute cost matrices for adjacent edges in the cycle
    vector<vector<vector<double>>> costMat(M);
    vector<int> sizes(M);
    for (int e = 0; e < M; ++e) {
        int ci = order[e];
        int cj = order[(e + 1) % M];
        int ni = (int)cities[ci].y.size();
        int nj = (int)cities[cj].y.size();
        sizes[e] = ni;
        costMat[e].assign(ni, vector<double>(nj, 0.0));
        double dx = abs(cities[ci].x - cities[cj].x);
        bool dxZero = (dx == 0.0);
        for (int ai = 0; ai < ni; ++ai) {
            double yi = (double)cities[ci].y[ai];
            for (int bj = 0; bj < nj; ++bj) {
                double yj = (double)cities[cj].y[bj];
                double dy = yj - yi;
                double dist = hypot(dx, dy);
                double slope = 0.0;
                if (dy > 0) {
                    if (dxZero) slope = INF / max(1.0, wS); // Very large to discourage impossible ascent at dx=0
                    else slope = dy / dx;
                }
                costMat[e][ai][bj] = wD * dist + wS * slope;
            }
        }
    }

    int n0 = (int)cities[order[0]].y.size();
    vector<vector<int>> prevBest(M); // Will store predecessors for the best start s
    for (int i = 0; i < M; ++i) prevBest[i].assign((int)cities[order[i]].y.size(), -1);

    double bestTotal = INF;
    int bestStart = -1;
    int bestEndIdx = -1;

    // DP arrays reused
    vector<double> dpPrev, dpNext;
    vector<vector<int>> prevFor(M); // temporary predecessors for current start s

    for (int s = 0; s < n0; ++s) {
        // Initialize predecessor storage for this start
        for (int i = 0; i < M; ++i)
            prevFor[i].assign((int)cities[order[i]].y.size(), -1);

        // Initialize dp for city 1 based on start choice s at city 0
        int n1 = (int)cities[order[1 % M]].y.size();
        dpPrev.assign(n1, INF);
        for (int j = 0; j < n1; ++j) {
            dpPrev[j] = costMat[0][s][j];
            prevFor[1][j] = s;
        }

        // Propagate for cities 2..M-1
        for (int i = 1; i <= M - 2; ++i) {
            int ni = (int)cities[order[i]].y.size();
            int nj = (int)cities[order[i + 1]].y.size();
            dpNext.assign(nj, INF);
            // Transition from city i -> city i+1
            const auto& cm = costMat[i]; // [ni][nj]
            for (int a = 0; a < ni; ++a) {
                double prevCost = dpPrev[a];
                if (prevCost >= INF/2) continue;
                for (int b = 0; b < nj; ++b) {
                    double v = prevCost + cm[a][b];
                    if (v < dpNext[b]) {
                        dpNext[b] = v;
                        prevFor[i + 1][b] = a;
                    }
                }
            }
            dpPrev.swap(dpNext);
        }

        // Close the cycle from city M-1 to city 0 (choice s)
        int nLast = (int)cities[order[M - 1]].y.size();
        double bestClose = INF;
        int bestJ = -1;
        const auto& cmClose = costMat[M - 1]; // [nLast][n0]
        for (int j = 0; j < nLast; ++j) {
            double v = dpPrev[j];
            if (v >= INF/2) continue;
            double total = v + cmClose[j][s];
            if (total < bestClose) {
                bestClose = total;
                bestJ = j;
            }
        }

        if (bestClose < bestTotal) {
            bestTotal = bestClose;
            bestStart = s;
            bestEndIdx = bestJ;
            // Save predecessors
            for (int i = 0; i < M; ++i) prevBest[i] = prevFor[i];
        }
    }

    // Reconstruct choices
    vector<int> sel(M, 0);
    if (bestStart == -1) {
        // Fallback: pick first option everywhere
        for (int i = 0; i < M; ++i) sel[i] = 0;
        return {INF, sel};
    }

    sel[M - 1] = bestEndIdx;
    for (int i = M - 1; i >= 1; --i) {
        sel[i - 1] = prevBest[i][sel[i]];
    }
    // sel[0] should be bestStart
    sel[0] = bestStart;

    return {bestTotal, sel};
}

vector<int> order_sorted_by_x(const vector<City>& cities) {
    int M = (int)cities.size();
    vector<int> idx(M);
    iota(idx.begin(), idx.end(), 0);
    sort(idx.begin(), idx.end(), [&](int a, int b){
        if (cities[a].x != cities[b].x) return cities[a].x < cities[b].x;
        return cities[a].id < cities[b].id;
    });
    return idx;
}

vector<int> order_alternating_extremes(const vector<int>& sorted) {
    vector<int> res;
    int l = 0, r = (int)sorted.size() - 1;
    while (l <= r) {
        res.push_back(sorted[l]);
        if (l < r) res.push_back(sorted[r]);
        ++l; --r;
    }
    return res;
}

vector<int> order_nearest_by_x(const vector<City>& cities, int start) {
    int M = (int)cities.size();
    vector<int> order;
    vector<char> used(M, 0);
    int cur = start;
    for (int t = 0; t < M; ++t) {
        order.push_back(cur);
        used[cur] = 1;
        if (t == M - 1) break;
        int best = -1;
        int bestDx = INT_MAX;
        for (int v = 0; v < M; ++v) {
            if (used[v]) continue;
            int dx = abs(cities[cur].x - cities[v].x);
            if (dx < bestDx || (dx == bestDx && cities[v].id < cities[best].id)) {
                bestDx = dx;
                best = v;
            }
        }
        cur = best;
    }
    return order;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    // Read first line robustly to detect presence of 'base'
    string firstLine;
    if (!getline(cin, firstLine)) return 0;
    while (firstLine.size() && (firstLine.back() == '\r' || firstLine.back() == '\n')) firstLine.pop_back();
    while (firstLine.size() && isspace((unsigned char)firstLine.back())) firstLine.pop_back();
    size_t p = 0;
    while (p < firstLine.size() && isspace((unsigned char)firstLine[p])) p++;
    string trimmed = firstLine.substr(p);

    double base = 0.0;
    int M;

    bool basePresent = hasDecimalOrExp(trimmed);
    if (basePresent) {
        base = stod(trimmed);
        if (!(cin >> M)) return 0;
    } else {
        // Treat first line as M
        M = stoi(trimmed);
    }

    vector<City> cities;
    cities.reserve(M);
    for (int i = 0; i < M; ++i) {
        int n, x;
        cin >> n >> x;
        vector<int> ys(n);
        for (int j = 0; j < n; ++j) cin >> ys[j];
        City c;
        c.id = i + 1;
        c.x = x;
        c.y = move(ys);
        cities.push_back(move(c));
    }
    int D_in, S_in;
    cin >> D_in >> S_in;

    // Weights
    double wD = (1.0 - K_WEIGHT) / max(1.0, (double)D_in);
    double wS = (K_WEIGHT) / max(1.0, (double)S_in);

    // Build candidate orders
    vector<vector<int>> candidates;
    auto add_candidate = [&](const vector<int>& ord) {
        // Avoid duplicates
        static unordered_set<string> seen;
        string key;
        key.reserve(ord.size() * 6);
        for (int v : ord) { key += to_string(v); key.push_back(','); }
        if (seen.insert(key).second) {
            candidates.push_back(ord);
        }
    };

    vector<int> ord_sorted = order_sorted_by_x(cities);
    vector<int> ord_sorted_rev = ord_sorted; reverse(ord_sorted_rev.begin(), ord_sorted_rev.end());
    vector<int> ord_alt = order_alternating_extremes(ord_sorted);
    vector<int> ord_alt_rev = ord_alt; reverse(ord_alt_rev.begin(), ord_alt_rev.end());

    add_candidate(ord_sorted);
    add_candidate(ord_sorted_rev);
    add_candidate(ord_alt);
    add_candidate(ord_alt_rev);

    // Nearest neighbor by x from leftmost and rightmost
    int leftmost = ord_sorted.front();
    int rightmost = ord_sorted.back();
    vector<int> ord_nn_left = order_nearest_by_x(cities, leftmost);
    vector<int> ord_nn_right = order_nearest_by_x(cities, rightmost);
    add_candidate(ord_nn_left);
    add_candidate(ord_nn_right);

    // Evaluate candidates and pick best
    double bestCost = INF;
    vector<int> bestOrder;
    vector<int> bestSel;

    for (auto& ord : candidates) {
        auto result = solveOrder(cities, ord, wD, wS);
        if (result.first < bestCost) {
            bestCost = result.first;
            bestOrder = ord;
            bestSel = result.second;
        }
    }

    // Fallback if something went wrong
    if (bestOrder.empty()) {
        bestOrder = ord_sorted;
        bestSel.assign(M, 0);
    }

    // Output as (city_id, landing_point_index) pairs joined by @
    for (int i = 0; i < M; ++i) {
        if (i) cout << "@";
        int cityIdx = bestOrder[i];
        int lpIdx = bestSel[i] + 1; // 1-based index
        cout << "(" << cities[cityIdx].id << "," << lpIdx << ")";
    }
    cout << "\n";
    return 0;
}