#include <bits/stdc++.h>
using namespace std;

struct City {
    int id; // 1-based
    int x;
    vector<int> ys;
    double y_rep;
};

static inline vector<long long> parseInts(const string &s) {
    vector<long long> res;
    string tmp;
    for (size_t i = 0; i < s.size(); ++i) {
        if (!isspace((unsigned char)s[i])) {
            tmp.push_back(s[i]);
        } else {
            if (!tmp.empty()) {
                res.push_back(stoll(tmp));
                tmp.clear();
            }
        }
    }
    if (!tmp.empty()) res.push_back(stoll(tmp));
    return res;
}

static inline int tokenCount(const string &s) {
    int cnt = 0;
    bool in = false;
    for (char c : s) {
        if (!isspace((unsigned char)c)) {
            if (!in) { in = true; cnt++; }
        } else {
            in = false;
        }
    }
    return cnt;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    vector<string> lines;
    string line;
    while (getline(cin, line)) {
        // trim
        bool allspace = true;
        for (char c : line) if (!isspace((unsigned char)c)) { allspace = false; break; }
        if (!allspace) lines.push_back(line);
    }
    if (lines.size() < 2) {
        return 0;
    }

    bool basePresent = (tokenCount(lines[1]) == 1);
    double base = 0.0;
    int M = 0;
    size_t idx = 0;
    if (basePresent) {
        base = stod(lines[0]);
        M = stoi(lines[1]);
        idx = 2;
    } else {
        M = stoi(lines[0]);
        idx = 1;
    }
    if (M <= 0) return 0;

    vector<City> cities;
    cities.reserve(M);
    for (int i = 0; i < M; ++i) {
        if (idx + 1 >= lines.size()) return 0;
        auto v1 = parseInts(lines[idx]);
        auto v2 = parseInts(lines[idx+1]);
        idx += 2;
        if (v1.size() < 2) return 0;
        int n = (int)v1[0];
        int x = (int)v1[1];
        vector<int> ys;
        ys.reserve(n);
        for (int k = 0; k < n && k < (int)v2.size(); ++k) ys.push_back((int)v2[k]);
        // If insufficient y's, pad with last or zeros
        while ((int)ys.size() < n) ys.push_back(ys.empty() ? 0 : ys.back());
        City c;
        c.id = i + 1;
        c.x = x;
        c.ys = move(ys);
        double sumy = 0;
        for (int y : c.ys) sumy += y;
        c.y_rep = sumy / c.ys.size();
        cities.push_back(move(c));
    }
    if (idx >= lines.size()) return 0;
    auto last = parseInts(lines[idx]);
    int D_orig = 1, S_orig = 1;
    if (last.size() >= 2) {
        D_orig = (int)last[0];
        S_orig = (int)last[1];
        if (D_orig == 0) D_orig = 1;
        if (S_orig == 0) S_orig = 1;
    }
    const double k = 0.6;
    const double wDist = (1.0 - k) / (double)D_orig;
    const double wSlope = k / (double)S_orig;

    auto edgeWeightedCost = [&](int xi, int yi, int xj, int yj) -> double {
        double dx = (double)abs(xj - xi);
        double dy = (double)yj - (double)yi;
        double dist = hypot(dx, dy);
        double slope = 0.0;
        if (dx == 0.0) {
            if (dy > 0.0) slope = 1e9; else slope = 0.0;
        } else {
            if (dy > 0.0) slope = dy / dx; else slope = 0.0;
        }
        return wDist * dist + wSlope * slope;
    };

    // Approximate cost matrix between cities using representative y
    int N = M;
    vector<vector<double>> approxCost(N, vector<double>(N, 0.0));
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            if (i == j) { approxCost[i][j] = 1e18; continue; }
            int xi = cities[i].x, xj = cities[j].x;
            double yi = cities[i].y_rep, yj = cities[j].y_rep;
            double dx = (double)abs(xj - xi);
            double dy = yj - yi;
            double dist = hypot(dx, dy);
            double slope = 0.0;
            if (dx == 0.0) slope = (dy > 0.0) ? 1e9 : 0.0;
            else slope = (dy > 0.0) ? dy / dx : 0.0;
            approxCost[i][j] = wDist * dist + wSlope * slope;
        }
    }

    auto buildOrderX = [&](bool incX, bool tieDescY) {
        vector<int> idxs(N);
        iota(idxs.begin(), idxs.end(), 0);
        sort(idxs.begin(), idxs.end(), [&](int a, int b) {
            if (cities[a].x != cities[b].x) return incX ? (cities[a].x < cities[b].x) : (cities[a].x > cities[b].x);
            if (tieDescY) return cities[a].y_rep > cities[b].y_rep;
            return cities[a].y_rep < cities[b].y_rep;
        });
        return idxs;
    };

    auto nearestNeighbor = [&](int start) {
        vector<int> order;
        order.reserve(N);
        vector<char> used(N, 0);
        int cur = start;
        used[cur] = 1;
        order.push_back(cur);
        for (int step = 1; step < N; ++step) {
            double best = 1e300;
            int bestj = -1;
            for (int j = 0; j < N; ++j) {
                if (used[j]) continue;
                double c = approxCost[cur][j];
                if (c < best) { best = c; bestj = j; }
            }
            if (bestj == -1) break;
            used[bestj] = 1;
            order.push_back(bestj);
            cur = bestj;
        }
        // In case of any unvisited (shouldn't happen), append them
        for (int j = 0; j < N; ++j) if (!used[j]) order.push_back(j);
        return order;
    };

    auto tourApproxCost = [&](const vector<int>& ord) {
        double cost = 0.0;
        for (int i = 0; i < N; ++i) {
            int a = ord[i];
            int b = ord[(i+1)%N];
            cost += approxCost[a][b];
        }
        return cost;
    };

    auto twoOptImprove = [&](vector<int>& ord, int maxPasses) {
        if (N <= 3) return;
        bool improved = true;
        int passes = 0;
        while (improved && passes < maxPasses) {
            improved = false;
            ++passes;
            for (int i = 0; i < N; ++i) {
                int i1 = (i + 1) % N;
                for (int j = i + 2; j < N; ++j) {
                    int j1 = (j + 1) % N;
                    if (i == j1) continue; // adjacent in cycle
                    int a = ord[i], b = ord[i1];
                    int c = ord[j], d = ord[j1];
                    double before = approxCost[a][b] + approxCost[c][d];
                    double after  = approxCost[a][c] + approxCost[b][d];
                    if (after + 1e-12 < before) {
                        // reverse segment b..c
                        if (i1 < j) {
                            reverse(ord.begin() + i1, ord.begin() + j + 1);
                        } else {
                            // wrap-around: handle by rotating to make i1 < j
                            // To simplify, skip wrap-around 2-opt to keep determinism and simplicity
                            continue;
                        }
                        improved = true;
                    }
                }
            }
        }
    };

    // DP to select landing points for a given city order and compute weighted cost
    auto solveAssignmentForOrder = [&](const vector<int>& ord, vector<int>& chosenIdx) -> double {
        int m = (int)ord.size();
        // Build cost matrices between consecutive cities
        vector<int> nstates(m);
        for (int i = 0; i < m; ++i) nstates[i] = (int)cities[ord[i]].ys.size();

        // Precompute cost matrices
        vector<vector<vector<double>>> costMat(m);
        for (int i = 0; i < m; ++i) {
            int j = (i + 1) % m;
            int ni = nstates[i], nj = nstates[j];
            costMat[i].assign(ni, vector<double>(nj, 0.0));
            int xi = cities[ord[i]].x, xj = cities[ord[j]].x;
            for (int a = 0; a < ni; ++a) {
                int yi = cities[ord[i]].ys[a];
                for (int b = 0; b < nj; ++b) {
                    int yj = cities[ord[j]].ys[b];
                    costMat[i][a][b] = edgeWeightedCost(xi, yi, xj, yj);
                }
            }
        }

        double bestTotal = 1e300;
        vector<int> bestAssign(m, 0);

        int n0 = nstates[0];
        // dp arrays
        vector<vector<int>> prevIdx(m);
        vector<double> prevDP, currDP;

        for (int s0 = 0; s0 < n0; ++s0) {
            prevIdx.assign(m, vector<int>());
            prevIdx[0].assign(n0, -1); // unused
            prevDP.assign(n0, 1e300);
            prevDP[s0] = 0.0;

            // Forward DP
            for (int i = 1; i < m; ++i) {
                int ni_prev = nstates[i-1];
                int ni_curr = nstates[i];
                currDP.assign(ni_curr, 1e300);
                prevIdx[i].assign(ni_curr, -1);
                for (int s = 0; s < ni_curr; ++s) {
                    double bestVal = 1e300;
                    int bestT = -1;
                    for (int t = 0; t < ni_prev; ++t) {
                        double val = prevDP[t] + costMat[i-1][t][s];
                        if (val < bestVal) {
                            bestVal = val;
                            bestT = t;
                        }
                    }
                    currDP[s] = bestVal;
                    prevIdx[i][s] = bestT;
                }
                prevDP.swap(currDP);
            }
            // Close cycle
            int n_last = nstates[m-1];
            double bestEnd = 1e300;
            int bestLastState = -1;
            for (int s = 0; s < n_last; ++s) {
                double val = prevDP[s] + costMat[m-1][s][s0];
                if (val < bestEnd) {
                    bestEnd = val;
                    bestLastState = s;
                }
            }
            if (bestEnd < bestTotal) {
                bestTotal = bestEnd;
                // reconstruct
                vector<int> assign(m, 0);
                assign[m-1] = bestLastState;
                for (int i = m-1; i >= 1; --i) {
                    int prevs = prevIdx[i][assign[i]];
                    assign[i-1] = prevs;
                }
                // Here assign[0] should be s0
                bestAssign.swap(assign);
            }
        }

        chosenIdx = move(bestAssign);
        return bestTotal;
    };

    // Build candidate orders
    vector<vector<int>> candidates;

    // Order by x asc, tie y desc/asc
    candidates.push_back(buildOrderX(true, true));
    candidates.push_back(buildOrderX(true, false));
    // Reverse
    candidates.push_back(buildOrderX(false, true));
    candidates.push_back(buildOrderX(false, false));

    // NN seeds
    // Leftmost x, rightmost x, lowest yrep, highest yrep
    int leftmost = 0, rightmost = 0, lowy = 0, highy = 0;
    for (int i = 1; i < N; ++i) {
        if (cities[i].x < cities[leftmost].x) leftmost = i;
        if (cities[i].x > cities[rightmost].x) rightmost = i;
        if (cities[i].y_rep < cities[lowy].y_rep) lowy = i;
        if (cities[i].y_rep > cities[highy].y_rep) highy = i;
    }
    vector<int> seeds;
    seeds.push_back(leftmost);
    if (rightmost != leftmost) seeds.push_back(rightmost);
    if (lowy != leftmost && lowy != rightmost) seeds.push_back(lowy);
    if (highy != leftmost && highy != rightmost && highy != lowy) seeds.push_back(highy);
    // De-duplicate
    sort(seeds.begin(), seeds.end());
    seeds.erase(unique(seeds.begin(), seeds.end()), seeds.end());
    for (int s : seeds) {
        auto ord = nearestNeighbor(s);
        twoOptImprove(ord, 3);
        candidates.push_back(ord);
    }

    // Evaluate candidates with DP
    double bestCost = 1e300;
    vector<int> bestOrder;
    vector<int> bestAssign;
    for (auto &ord : candidates) {
        vector<int> assign;
        double cost = solveAssignmentForOrder(ord, assign);
        if (cost < bestCost) {
            bestCost = cost;
            bestOrder = ord;
            bestAssign = assign;
        }
    }

    // Fallback if something went wrong
    if (bestOrder.empty()) {
        bestOrder.resize(N);
        iota(bestOrder.begin(), bestOrder.end(), 0);
        bestAssign.assign(N, 0);
    }

    // Output
    // Format: (city_id, landing_point_index)@(city_id, landing_point_index)@...
    // landing_point_index is 1-based within that city
    for (int i = 0; i < N; ++i) {
        int idxCity = bestOrder[i];
        int landingIdx = (bestAssign.size() == (size_t)N ? bestAssign[i] : 0);
        if (landingIdx < 0 || landingIdx >= (int)cities[idxCity].ys.size()) landingIdx = 0;
        cout << "(" << cities[idxCity].id << "," << (landingIdx + 1) << ")";
        if (i + 1 < N) cout << "@";
    }
    cout << "\n";

    return 0;
}