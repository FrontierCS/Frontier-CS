#include <bits/stdc++.h>
using namespace std;

struct CostMatrix {
    int ni = 0, nj = 0;
    vector<double> cAB; // i -> j
    vector<double> cBA; // j -> i
};

const double INF = 1e100;
const double LARGE_SLOPE = 1e9;
const int MAX_M = 205;
const int MAX_N = 21;

double dpArr[MAX_M][MAX_N];
int prvArr[MAX_M][MAX_N];

struct EdgeInfo {
    int nPrev;
    int nCurr;
    const double *cost;
    int stride;
};

double computeBestAssignmentForPerm(
    const vector<int>& perm,
    const vector<int>& n,
    const vector<vector<CostMatrix>>& cost,
    vector<int>& bestLanding
) {
    int M = (int)perm.size();
    int firstCity = perm[0];
    int n0 = n[firstCity];

    // Precompute edge info for consecutive cities (forward edges)
    vector<EdgeInfo> edges(M); // edges[1..M-1] used
    for (int pos = 1; pos < M; ++pos) {
        int prevCity = perm[pos - 1];
        int currCity = perm[pos];
        EdgeInfo e;
        e.nPrev = n[prevCity];
        e.nCurr = n[currCity];
        if (prevCity < currCity) {
            const CostMatrix &cm = cost[prevCity][currCity];
            e.cost = cm.cAB.data();
            e.stride = e.nCurr; // n_curr
        } else {
            const CostMatrix &cm = cost[currCity][prevCity];
            e.cost = cm.cBA.data();
            e.stride = e.nCurr; // n_curr
        }
        edges[pos] = e;
    }

    // Closing edge from last city back to first city
    int lastCity = perm[M - 1];
    int nLast = n[lastCity];
    const double *closingCost = nullptr;
    int closingStride = n0; // stride over start state
    if (lastCity < firstCity) {
        const CostMatrix &cm = cost[lastCity][firstCity];
        closingCost = cm.cAB.data(); // last -> first
    } else {
        const CostMatrix &cm = cost[firstCity][lastCity];
        closingCost = cm.cBA.data(); // last -> first
    }

    double globalBest = INF;
    int bestStart = -1;
    int bestLast = -1;

    // Enumerate starting landing point at first city
    for (int s = 0; s < n0; ++s) {
        // Initialize dp for position 0
        for (int j = 0; j < n0; ++j) dpArr[0][j] = INF;
        dpArr[0][s] = 0.0;

        // Forward DP along the cycle
        for (int pos = 1; pos < M; ++pos) {
            EdgeInfo &e = edges[pos];
            int nPrev = e.nPrev;
            int nCurr = e.nCurr;
            for (int curr = 0; curr < nCurr; ++curr) {
                double bestVal = INF;
                for (int prev = 0; prev < nPrev; ++prev) {
                    double prevCost = dpArr[pos - 1][prev];
                    if (prevCost == INF) continue;
                    double val = prevCost + e.cost[prev * e.stride + curr];
                    if (val < bestVal) bestVal = val;
                }
                dpArr[pos][curr] = bestVal;
            }
        }

        // Add closing edge from last city back to first city (state s)
        double bestCycleForStart = INF;
        int bestLastForStart = -1;
        for (int last = 0; last < nLast; ++last) {
            double pathCost = dpArr[M - 1][last];
            if (pathCost == INF) continue;
            double total = pathCost + closingCost[last * closingStride + s];
            if (total < bestCycleForStart) {
                bestCycleForStart = total;
                bestLastForStart = last;
            }
        }

        if (bestCycleForStart < globalBest) {
            globalBest = bestCycleForStart;
            bestStart = s;
            bestLast = bestLastForStart;
        }
    }

    // Re-run DP for bestStart to record predecessors
    if (bestStart == -1) {
        // Should not happen; fallback: choose first landing everywhere
        bestLanding.assign(M, 0);
        return INF;
    }

    for (int j = 0; j < n0; ++j) dpArr[0][j] = INF;
    dpArr[0][bestStart] = 0.0;

    for (int pos = 1; pos < M; ++pos) {
        EdgeInfo &e = edges[pos];
        int nPrev = e.nPrev;
        int nCurr = e.nCurr;
        for (int curr = 0; curr < nCurr; ++curr) {
            double bestVal = INF;
            int bestPrev = -1;
            for (int prev = 0; prev < nPrev; ++prev) {
                double prevCost = dpArr[pos - 1][prev];
                if (prevCost == INF) continue;
                double val = prevCost + e.cost[prev * e.stride + curr];
                if (val < bestVal) {
                    bestVal = val;
                    bestPrev = prev;
                }
            }
            dpArr[pos][curr] = bestVal;
            prvArr[pos][curr] = bestPrev;
        }
    }

    // Backtrack landing choices
    bestLanding.assign(M, 0);
    bestLanding[M - 1] = bestLast;
    for (int pos = M - 1; pos >= 1; --pos) {
        int curr = bestLanding[pos];
        int prev = prvArr[pos][curr];
        bestLanding[pos - 1] = prev;
    }
    bestLanding[0] = bestStart;

    return globalBest;
}

// 2-opt improvement on symmetric pseudo-cost matrix
vector<int> twoOptImprove(const vector<int>& startPerm, const vector<vector<double>>& pseudoCost) {
    int M = (int)startPerm.size();
    vector<int> perm = startPerm;

    auto routeCost = [&]() {
        double tot = 0.0;
        for (int i = 0; i < M; ++i) {
            int a = perm[i];
            int b = perm[(i + 1) % M];
            tot += pseudoCost[a][b];
        }
        return tot;
    };

    double bestCost = routeCost();
    bool improved = true;

    while (improved) {
        improved = false;
        for (int i = 0; i < M; ++i) {
            int iNext = (i + 1) % M;
            for (int j = i + 2; j < M; ++j) {
                if (i == 0 && j == M - 1) continue; // would break same edge
                int jNext = (j + 1) % M;

                int a = perm[i];
                int b = perm[iNext];
                int c = perm[j];
                int d = perm[jNext];

                double delta = -pseudoCost[a][b] - pseudoCost[c][d]
                               + pseudoCost[a][c] + pseudoCost[b][d];
                if (delta < -1e-9) {
                    // reverse segment (iNext .. j)
                    if (iNext < j) {
                        reverse(perm.begin() + iNext, perm.begin() + j + 1);
                    }
                    bestCost += delta;
                    improved = true;
                    goto next_iteration;
                }
            }
        }
    next_iteration:
        ;
    }

    return perm;
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

    vector<int> n(M), x(M);
    vector<vector<int>> ys(M);

    for (int i = 0; i < M; ++i) {
        int ni, xi;
        cin >> ni >> xi;
        n[i] = ni;
        x[i] = xi;
        ys[i].resize(ni);
        for (int j = 0; j < ni; ++j) {
            cin >> ys[i][j];
        }
    }

    double D0, S0;
    cin >> D0 >> S0;

    const double k = 0.6;
    double weightDist = (1.0 - k) / D0;
    double weightSlope = k / S0;

    // Precompute cost matrices between city pairs
    vector<vector<CostMatrix>> cost(M, vector<CostMatrix>(M));

    for (int i = 0; i < M; ++i) {
        for (int j = i + 1; j < M; ++j) {
            int ni = n[i];
            int nj = n[j];
            CostMatrix cm;
            cm.ni = ni;
            cm.nj = nj;
            cm.cAB.assign((size_t)ni * nj, 0.0);
            cm.cBA.assign((size_t)nj * ni, 0.0);

            double dx = (double)x[j] - x[i];
            double adx = fabs(dx);
            bool dxZero = adx < 1e-9;
            double sqDx = adx * adx;
            double invDx = dxZero ? 0.0 : 1.0 / adx;

            for (int a = 0; a < ni; ++a) {
                double yi = (double)ys[i][a];
                for (int b = 0; b < nj; ++b) {
                    double yj = (double)ys[j][b];
                    double dy = yj - yi;
                    double dist = sqrt(sqDx + dy * dy);

                    double slopeIJ, slopeJI;
                    if (!dxZero) {
                        if (dy > 0) {
                            slopeIJ = dy * invDx;
                            slopeJI = 0.0;
                        } else if (dy < 0) {
                            slopeIJ = 0.0;
                            slopeJI = -dy * invDx;
                        } else {
                            slopeIJ = 0.0;
                            slopeJI = 0.0;
                        }
                    } else {
                        if (dy > 0) {
                            slopeIJ = LARGE_SLOPE;
                            slopeJI = 0.0;
                        } else if (dy < 0) {
                            slopeIJ = 0.0;
                            slopeJI = LARGE_SLOPE;
                        } else {
                            slopeIJ = 0.0;
                            slopeJI = 0.0;
                        }
                    }

                    double costIJ = weightDist * dist + weightSlope * slopeIJ;
                    double costJI = weightDist * dist + weightSlope * slopeJI;

                    cm.cAB[a * nj + b] = costIJ;
                    cm.cBA[b * ni + a] = costJI;
                }
            }

            cost[i][j] = std::move(cm);
        }
    }

    // Compute pseudo-cost matrix for building permutations
    vector<double> midY(M);
    for (int i = 0; i < M; ++i) {
        double sum = 0.0;
        for (int yv : ys[i]) sum += (double)yv;
        midY[i] = sum / n[i];
    }

    vector<vector<double>> pseudoCost(M, vector<double>(M, 0.0));
    for (int i = 0; i < M; ++i) {
        for (int j = i + 1; j < M; ++j) {
            double dx = (double)x[j] - x[i];
            double adx = fabs(dx);
            double dy = midY[j] - midY[i];
            double dist = sqrt(adx * adx + dy * dy);
            double slopeSym = (adx > 1e-9) ? fabs(dy) / adx : 0.0;
            double c = weightDist * dist + weightSlope * slopeSym;
            pseudoCost[i][j] = pseudoCost[j][i] = c;
        }
    }

    // Build initial permutations
    vector<vector<int>> candidatePerms;

    // 1) Sort by x coordinate
    {
        vector<int> perm(M);
        iota(perm.begin(), perm.end(), 0);
        sort(perm.begin(), perm.end(), [&](int a, int b) {
            if (x[a] != x[b]) return x[a] < x[b];
            return a < b;
        });
        perm = twoOptImprove(perm, pseudoCost);
        candidatePerms.push_back(perm);
        vector<int> revPerm = perm;
        reverse(revPerm.begin(), revPerm.end());
        candidatePerms.push_back(revPerm);
    }

    // 2) Nearest neighbor from leftmost city
    {
        int startCity = 0;
        for (int i = 1; i < M; ++i) {
            if (x[i] < x[startCity] || (x[i] == x[startCity] && i < startCity)) {
                startCity = i;
            }
        }
        vector<int> perm(M);
        vector<char> used(M, 0);
        perm[0] = startCity;
        used[startCity] = 1;
        for (int pos = 1; pos < M; ++pos) {
            int prev = perm[pos - 1];
            double bestC = INF;
            int bestCity = -1;
            for (int j = 0; j < M; ++j) {
                if (!used[j]) {
                    double c = pseudoCost[prev][j];
                    if (c < bestC) {
                        bestC = c;
                        bestCity = j;
                    }
                }
            }
            if (bestCity == -1) {
                // fallback: pick any unused
                for (int j = 0; j < M; ++j) {
                    if (!used[j]) {
                        bestCity = j;
                        break;
                    }
                }
            }
            perm[pos] = bestCity;
            used[bestCity] = 1;
        }
        perm = twoOptImprove(perm, pseudoCost);
        candidatePerms.push_back(perm);
        vector<int> revPerm = perm;
        reverse(revPerm.begin(), revPerm.end());
        candidatePerms.push_back(revPerm);
    }

    // Evaluate candidates with full DP and pick best
    double bestTotalCost = INF;
    vector<int> bestPerm;
    vector<int> bestLandingGlobal;

    for (const auto& perm : candidatePerms) {
        vector<int> landing;
        double costVal = computeBestAssignmentForPerm(perm, n, cost, landing);
        if (costVal < bestTotalCost) {
            bestTotalCost = costVal;
            bestPerm = perm;
            bestLandingGlobal = landing;
        }
    }

    if (bestPerm.empty()) {
        // Fallback: trivial solution picking first landing of each city in input order
        bestPerm.resize(M);
        iota(bestPerm.begin(), bestPerm.end(), 0);
        bestLandingGlobal.assign(M, 0);
    }

    // Output format: (city_id,landing_point_index) separated by '@'
    for (int i = 0; i < M; ++i) {
        if (i > 0) cout << "@";
        int cityId = bestPerm[i] + 1;
        int landingIdx = bestLandingGlobal[i] + 1;
        cout << "(" << cityId << "," << landingIdx << ")";
    }
    cout << "\n";

    return 0;
}