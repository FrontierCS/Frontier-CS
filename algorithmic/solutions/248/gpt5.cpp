#include <bits/stdc++.h>
using namespace std;

struct City {
    int id;
    int x;
    vector<int> ys;
};

static const double K_WEIGHT = 0.6;
static const double INF = 1e300;
static const double EPS = 1e-12;

double wDist = 1.0, wSlope = 1.0;
vector<City> cities;

// Edge cost from city a to city b, choosing indices ya and yb
inline double edgeCost(int a, int b, int ya, int yb) {
    const City& A = cities[a];
    const City& B = cities[b];
    int dx_i = abs(A.x - B.x);
    double dx = (double)dx_i;
    double dy = (double)B.ys[yb] - (double)A.ys[ya];
    double dist = hypot(dx, dy);
    double slope = 0.0;
    if (dy > 0) {
        if (dx_i == 0) return INF; // infinite slope if climbing with zero horizontal distance
        slope = dy / dx;
    }
    return wDist * dist + wSlope * slope;
}

// Optimize landing point indices for a fixed order using DP over the cycle
pair<double, vector<int>> optimizeYForOrder(const vector<int>& ord) {
    int M = (int)ord.size();
    // Break the cycle at position 0, enumerate start landing choice
    const int n0 = (int)cities[ord[0]].ys.size();
    double bestTotal = INF;
    int bestStart = -1;
    int bestLast = -1;
    vector<vector<int>> bestPred; // pred indices for best start

    // To reduce reallocations
    vector<vector<int>> pred(M);
    for (int i = 0; i < M; ++i) pred[i].assign((int)cities[ord[i]].ys.size(), -1);

    vector<double> dp_prev, dp_curr;
    vector<int> nsz(M);
    for (int i = 0; i < M; ++i) nsz[i] = (int)cities[ord[i]].ys.size();

    for (int s = 0; s < n0; ++s) {
        // initialize
        dp_prev.assign(nsz[0], INF);
        for (int j = 0; j < nsz[0]; ++j) dp_prev[j] = (j == s ? 0.0 : INF);
        for (int i = 1; i < M; ++i) {
            int ni = nsz[i];
            int nip = nsz[i-1];
            dp_curr.assign(ni, INF);
            for (int k = 0; k < ni; ++k) {
                double best = INF;
                int arg = -1;
                for (int j = 0; j < nip; ++j) {
                    double prev = dp_prev[j];
                    if (prev >= INF/2) continue;
                    double c = prev + edgeCost(ord[i-1], ord[i], j, k);
                    if (c < best) {
                        best = c;
                        arg = j;
                    }
                }
                dp_curr[k] = best;
                pred[i][k] = arg;
            }
            dp_prev.swap(dp_curr);
        }
        // close the cycle with edge from last to start
        double bestEnd = INF;
        int bestEndIdx = -1;
        for (int l = 0; l < nsz[M-1]; ++l) {
            double prev = dp_prev[l];
            if (prev >= INF/2) continue;
            double c = prev + edgeCost(ord[M-1], ord[0], l, s);
            if (c < bestEnd) {
                bestEnd = c;
                bestEndIdx = l;
            }
        }
        if (bestEnd < bestTotal) {
            bestTotal = bestEnd;
            bestStart = s;
            bestLast = bestEndIdx;
            bestPred = pred; // save predecessors for reconstruction
        }
    }

    vector<int> ySel(M, 0);
    if (bestStart == -1) {
        // Fallback: choose first landing point for all (should rarely happen)
        for (int i = 0; i < M; ++i) ySel[i] = 0;
        return {INF, ySel};
    }
    ySel[M-1] = bestLast;
    for (int i = M-1; i >= 1; --i) {
        int prev = bestPred[i][ ySel[i] ];
        if (prev < 0) prev = 0;
        ySel[i-1] = prev;
    }
    // ensure starting matches bestStart (numerical safety)
    ySel[0] = bestStart;

    return {bestTotal, ySel};
}

// Compute total cost for an order and a given y selection
double totalCostForOrderY(const vector<int>& ord, const vector<int>& ySel) {
    int M = (int)ord.size();
    double sum = 0.0;
    for (int i = 0; i < M; ++i) {
        int a = ord[i];
        int b = ord[(i+1)%M];
        sum += edgeCost(a, b, ySel[i], ySel[(i+1)%M]);
        if (sum >= INF/2) return sum;
    }
    return sum;
}

// Recompute edge costs for a given order and ySel
void recomputeEdgeCosts(const vector<int>& ord, const vector<int>& ySel, vector<double>& edCost, double& approxCost) {
    int M = (int)ord.size();
    edCost.assign(M, 0.0);
    double sum = 0.0;
    for (int i = 0; i < M; ++i) {
        int a = ord[i];
        int b = ord[(i+1)%M];
        double c = edgeCost(a, b, ySel[i], ySel[(i+1)%M]);
        edCost[i] = c;
        sum += c;
    }
    approxCost = sum;
}

// Perform one 2-opt pass (segment reversal) for ATSP cost using fixed ySel. Returns true if improved.
bool twoOptPass(vector<int>& ord, const vector<int>& ySel, vector<double>& edCost, double& approxCost, chrono::steady_clock::time_point deadline) {
    int M = (int)ord.size();
    // First-improvement strategy
    for (int i = 0; i < M; ++i) {
        if (chrono::steady_clock::now() > deadline) return false;
        for (int j = i + 2; j < M; ++j) {
            if (i == 0 && j == M-1) continue; // don't break the cycle edge (M-1 -> 0)
            // Compute delta
            int i1 = i + 1;
            int j1 = j + 1;

            // Old boundary edges
            double old1 = edCost[i];   // ord[i] -> ord[i+1]
            double old2 = edCost[j];   // ord[j] -> ord[j+1]

            // Sum old inside edges between i+1..j-1
            double sumOldInside = 0.0;
            for (int k = i+1; k <= j-1; ++k) sumOldInside += edCost[k];

            // New boundary edges
            double new1 = edgeCost(ord[i], ord[j], ySel[i], ySel[j]);
            double new2 = edgeCost(ord[i1], ord[j1 % M], ySel[i1], ySel[j1 % M]);

            // New inside edges: reversed orientation
            double sumNewInside = 0.0;
            for (int k = i+1; k <= j-1; ++k) {
                // edge becomes ord[k+1] -> ord[k]
                sumNewInside += edgeCost(ord[k+1], ord[k], ySel[k+1], ySel[k]);
            }

            double delta = (new1 + new2 + sumNewInside) - (old1 + old2 + sumOldInside);
            if (delta < -1e-9) {
                // perform reversal
                reverse(ord.begin() + i1, ord.begin() + j + 1);
                // recompute edCost and approxCost fully for simplicity
                recomputeEdgeCosts(ord, ySel, edCost, approxCost);
                return true;
            }
        }
    }
    return false;
}

bool parseWithMode(const string& s, bool withBase, double& base, vector<City>& outCities, double& D, double& S) {
    stringstream ss(s);
    if (withBase) {
        if (!(ss >> base)) return false;
    } else {
        base = 0.0;
    }
    int M;
    if (!(ss >> M)) return false;
    vector<City> cs;
    cs.reserve(M);
    for (int i = 0; i < M; ++i) {
        long long nll, xll;
        if (!(ss >> nll >> xll)) return false;
        City c;
        c.id = i + 1;
        c.x = (int)xll;
        c.ys.resize((size_t)nll);
        for (int j = 0; j < nll; ++j) {
            long long yll;
            if (!(ss >> yll)) return false;
            c.ys[j] = (int)yll;
        }
        cs.push_back(std::move(c));
    }
    double Dd, Sd;
    if (!(ss >> Dd >> Sd)) return false;
    outCities = std::move(cs);
    D = Dd;
    S = Sd;
    return true;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    // Read entire input into string to handle both formats robustly
    string inputData((istreambuf_iterator<char>(cin)), istreambuf_iterator<char>());
    if (inputData.empty()) return 0;

    double baseVal = 0.0;
    double D_orig = 1.0, S_orig = 1.0;
    vector<City> parsedCities;

    if (!parseWithMode(inputData, true, baseVal, parsedCities, D_orig, S_orig)) {
        // Try without base
        if (!parseWithMode(inputData, false, baseVal, parsedCities, D_orig, S_orig)) {
            return 0; // cannot parse
        }
    }

    cities = parsedCities;

    // Weights
    wDist = (1.0 - K_WEIGHT) / D_orig;
    wSlope = (K_WEIGHT) / S_orig;

    int M = (int)cities.size();

    // Prepare initial orders: by x ascending and descending
    vector<int> idx(M);
    iota(idx.begin(), idx.end(), 0);
    stable_sort(idx.begin(), idx.end(), [&](int a, int b){ 
        if (cities[a].x != cities[b].x) return cities[a].x < cities[b].x;
        return cities[a].id < cities[b].id;
    });

    vector<int> idxRev = idx;
    reverse(idxRev.begin(), idxRev.end());

    // Optimize y for both and pick better
    auto resAsc = optimizeYForOrder(idx);
    auto resDesc = optimizeYForOrder(idxRev);

    vector<int> ord, ySel;
    double bestCost;
    if (resAsc.first <= resDesc.first) {
        ord = idx;
        ySel = resAsc.second;
        bestCost = resAsc.first;
    } else {
        ord = idxRev;
        ySel = resDesc.second;
        bestCost = resDesc.first;
    }

    // Local search with time budget
    auto startTime = chrono::steady_clock::now();
    // Allow up to ~2 seconds for local optimization
    auto deadline = startTime + chrono::milliseconds(1900);

    vector<double> edCost;
    double approxCost = 0.0;
    recomputeEdgeCosts(ord, ySel, edCost, approxCost);

    // Iterate: 2-opt passes using fixed y, then re-optimize y
    int iter = 0;
    while (chrono::steady_clock::now() < deadline) {
        bool improved = false;
        // Perform 2-opt passes until no further improvement or time up
        while (chrono::steady_clock::now() < deadline) {
            bool changed = twoOptPass(ord, ySel, edCost, approxCost, deadline);
            if (!changed) break;
            improved = true;
        }
        // Re-optimize y selection for current order
        auto res = optimizeYForOrder(ord);
        if (res.first + 1e-9 < bestCost) {
            bestCost = res.first;
            ySel = res.second;
            recomputeEdgeCosts(ord, ySel, edCost, approxCost);
            improved = true;
        }
        if (!improved) break;
        iter++;
    }

    // Output the route
    // Format: (city_id,landing_point_index)@...
    for (int i = 0; i < M; ++i) {
        if (i) cout << "@";
        int cityId = cities[ord[i]].id;
        int lpIndex = ySel[i] + 1;
        cout << "(" << cityId << "," << lpIndex << ")";
    }
    cout << "\n";
    return 0;
}