#include <bits/stdc++.h>
using namespace std;

struct City {
    int x;
    vector<int> ys;
};

struct ParsedData {
    bool ok = false;
    double base = 0.0;
    int M = 0;
    vector<City> cities;
    double Dnorm = 1.0;
    double Snorm = 1.0;
};

static double wDist, wSlope;
static vector<City> cities;

// Robust token parsing helpers
bool parseDoubleTok(const string &s, double &val) {
    char *endptr = nullptr;
    errno = 0;
    const char *cstr = s.c_str();
    val = strtod(cstr, &endptr);
    if (endptr == cstr || *endptr != '\0' || errno == ERANGE) return false;
    return true;
}

bool parseIntTok(const string &s, long long &val) {
    char *endptr = nullptr;
    errno = 0;
    const char *cstr = s.c_str();
    val = strtoll(cstr, &endptr, 10);
    if (endptr == cstr || *endptr != '\0' || errno == ERANGE) return false;
    return true;
}

ParsedData attemptParse(const vector<string> &tok, bool withBase) {
    ParsedData res;
    size_t idx = 0;
    size_t N = tok.size();

    if (N == 0) return res;

    if (withBase) {
        if (idx >= N) return res;
        if (!parseDoubleTok(tok[idx++], res.base)) return res;
    } else {
        res.base = 0.0;
    }

    long long tmp;
    if (idx >= N || !parseIntTok(tok[idx++], tmp)) return res;
    res.M = (int)tmp;
    if (res.M <= 0 || res.M > 200) return res;

    res.cities.clear();
    res.cities.reserve(res.M);

    for (int ci = 0; ci < res.M; ++ci) {
        if (idx + 1 >= N) return res;
        long long nll, xll;
        if (!parseIntTok(tok[idx++], nll) || !parseIntTok(tok[idx++], xll))
            return res;
        int n = (int)nll;
        int x = (int)xll;
        if (n < 1 || n > 20) return res;
        if (idx + n > N) return res;

        City c;
        c.x = x;
        c.ys.resize(n);
        for (int j = 0; j < n; ++j) {
            long long yll;
            if (!parseIntTok(tok[idx++], yll)) return res;
            c.ys[j] = (int)yll;
        }
        res.cities.push_back(std::move(c));
    }

    if (idx + 2 != N) return res;
    long long Dll, Sll;
    if (!parseIntTok(tok[idx++], Dll) || !parseIntTok(tok[idx++], Sll))
        return res;

    res.Dnorm = (double)Dll;
    res.Snorm = (double)Sll;
    res.ok = true;
    return res;
}

// Cost between two concrete points
inline double computeEdgeCostPts(int x1, double y1, int x2, double y2) {
    double dx = (double)(x2 - x1);
    double dy = y2 - y1;
    double dist = sqrt(dx * dx + dy * dy);
    double slope = 0.0;
    if (y2 > y1) {
        double horiz = fabs((double)(x2 - x1));
        if (horiz < 1e-9) horiz = 1e-9;
        slope = (y2 - y1) / horiz;
    }
    return wDist * dist + wSlope * slope;
}

// Cost between two cities using current selections
inline double computeEdgeCostCity(int ci, int cj, const vector<int> &sel) {
    if (ci == cj) return 0.0;
    int x1 = cities[ci].x;
    int x2 = cities[cj].x;
    double y1 = (double)cities[ci].ys[sel[ci]];
    double y2 = (double)cities[cj].ys[sel[cj]];
    return computeEdgeCostPts(x1, y1, x2, y2);
}

double totalTourCost(const vector<int> &ord, const vector<int> &sel) {
    int n = (int)ord.size();
    if (n <= 1) return 0.0;
    double sum = 0.0;
    for (int i = 0; i < n; ++i) {
        int a = ord[i];
        int b = ord[(i + 1) % n];
        sum += computeEdgeCostCity(a, b, sel);
    }
    return sum;
}

// Optimize landing-point selections for fixed order using coordinate descent
void optimizeSelections(const vector<int> &order, vector<int> &sel, int maxSweeps) {
    int m = (int)order.size();
    if (m == 0) return;
    const double EPS = 1e-12;

    for (int sweep = 0; sweep < maxSweeps; ++sweep) {
        bool changed = false;

        for (int pos = 0; pos < m; ++pos) {
            int cidx = order[pos];
            City &c = cities[cidx];
            int npts = (int)c.ys.size();
            if (npts <= 1) continue;

            int prevIdx = order[(pos - 1 + m) % m];
            int nextIdx = order[(pos + 1) % m];

            int x_prev = cities[prevIdx].x;
            double y_prev = (double)cities[prevIdx].ys[sel[prevIdx]];

            int x_next = cities[nextIdx].x;
            double y_next = (double)cities[nextIdx].ys[sel[nextIdx]];

            int x_c = c.x;
            double y_curr = (double)c.ys[sel[cidx]];

            double oldIn = computeEdgeCostPts(x_prev, y_prev, x_c, y_curr);
            double oldOut = computeEdgeCostPts(x_c, y_curr, x_next, y_next);
            double oldTotal = oldIn + oldOut;

            double bestCost = oldTotal;
            int bestIndex = sel[cidx];

            for (int j = 0; j < npts; ++j) {
                if (j == sel[cidx]) continue;
                double y_cand = (double)c.ys[j];
                double newIn = computeEdgeCostPts(x_prev, y_prev, x_c, y_cand);
                double newOut = computeEdgeCostPts(x_c, y_cand, x_next, y_next);
                double newTotal = newIn + newOut;
                if (newTotal + EPS < bestCost) {
                    bestCost = newTotal;
                    bestIndex = j;
                }
            }

            if (bestIndex != sel[cidx]) {
                sel[cidx] = bestIndex;
                changed = true;
            }
        }

        if (!changed) break;
    }
}

// 2-opt for directed cost metric using precomputed cost matrix
void twoOpt(vector<int> &ord, const vector<int> &sel) {
    int n = (int)ord.size();
    if (n <= 2) return;
    int m = (int)cities.size();

    // Precompute cost matrix between cities with current selections
    vector<vector<double>> cost(m, vector<double>(m, 0.0));
    for (int i = 0; i < m; ++i) {
        int xi = cities[i].x;
        double yi = (double)cities[i].ys[sel[i]];
        for (int j = 0; j < m; ++j) {
            if (i == j) {
                cost[i][j] = 0.0;
            } else {
                int xj = cities[j].x;
                double yj = (double)cities[j].ys[sel[j]];
                cost[i][j] = computeEdgeCostPts(xi, yi, xj, yj);
            }
        }
    }

    const double EPS = 1e-12;
    bool improved = true;

    while (improved) {
        improved = false;

        for (int i = 0; i < n && !improved; ++i) {
            int a = ord[i];
            int b = ord[(i + 1) % n];
            double old_ab = cost[a][b];

            double oldForward = 0.0;
            double newReverse = 0.0;

            for (int j = i + 2; j < n; ++j) {
                int cPrev = ord[j - 1];
                int c = ord[j];

                oldForward += cost[cPrev][c];
                newReverse += cost[c][cPrev];

                int d = ord[(j + 1) % n];

                double old_cd = cost[c][d];
                double new_ac = cost[a][c];
                double new_bd = cost[b][d];

                double before = old_ab + oldForward + old_cd;
                double after = new_ac + newReverse + new_bd;

                if (after + EPS < before) {
                    reverse(ord.begin() + i + 1, ord.begin() + j + 1);
                    improved = true;
                    break;
                }
            }
        }
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    // Read all tokens
    vector<string> tok;
    string s;
    while (cin >> s) tok.push_back(s);
    if (tok.empty()) return 0;

    ParsedData parsed = attemptParse(tok, true);
    if (!parsed.ok) parsed = attemptParse(tok, false);
    if (!parsed.ok) return 0;

    cities = parsed.cities;
    int M = parsed.M;
    double Dnorm = parsed.Dnorm;
    double Snorm = parsed.Snorm;

    double k = 0.6;
    if (Dnorm == 0.0) Dnorm = 1.0;
    if (Snorm == 0.0) Snorm = 1.0;
    wDist = (1.0 - k) / Dnorm;
    wSlope = k / Snorm;

    // Initial landing point selection: global median height
    vector<int> sel(M, 0);
    vector<int> allY;
    allY.reserve(4000);
    for (const auto &c : cities) {
        for (int y : c.ys) allY.push_back(y);
    }
    sort(allY.begin(), allY.end());
    int Hglobal = allY[allY.size() / 2];

    for (int i = 0; i < M; ++i) {
        const auto &ys = cities[i].ys;
        int bestIdx = 0;
        int bestDiff = abs(ys[0] - Hglobal);
        for (int j = 1; j < (int)ys.size(); ++j) {
            int diff = abs(ys[j] - Hglobal);
            if (diff < bestDiff) {
                bestDiff = diff;
                bestIdx = j;
            }
        }
        sel[i] = bestIdx;
    }

    // Initial order: sort cities by x, try both directions
    vector<int> order(M);
    iota(order.begin(), order.end(), 0);
    sort(order.begin(), order.end(), [&](int a, int b) {
        if (cities[a].x != cities[b].x) return cities[a].x < cities[b].x;
        return a < b;
    });

    vector<int> orderRev = order;
    reverse(orderRev.begin(), orderRev.end());

    double costAsc = totalTourCost(order, sel);
    double costDesc = totalTourCost(orderRev, sel);
    if (costDesc < costAsc) order = orderRev;

    // Alternate between selection optimization and 2-opt
    const int outerIters = 3;
    for (int it = 0; it < outerIters; ++it) {
        optimizeSelections(order, sel, 5);
        twoOpt(order, sel);
    }
    optimizeSelections(order, sel, 10);

    // Output route
    for (int i = 0; i < M; ++i) {
        int cid = order[i] + 1;
        int pid = sel[order[i]] + 1;
        cout << '(' << cid << ',' << pid << ')';
        if (i + 1 < M) cout << '@';
    }
    cout << '\n';

    return 0;
}