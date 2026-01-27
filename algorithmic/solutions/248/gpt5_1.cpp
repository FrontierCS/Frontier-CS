#include <bits/stdc++.h>
using namespace std;

static inline double hypot2(double dx, double dy) {
    return sqrt(dx*dx + dy*dy);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    // Input
    double base;
    if (!(cin >> base)) {
        return 0;
    }
    int M;
    cin >> M;
    vector<int> x(M);
    vector<vector<int>> ys(M);
    for (int i = 0; i < M; ++i) {
        int n, xi;
        cin >> n >> xi;
        x[i] = xi;
        ys[i].resize(n);
        for (int j = 0; j < n; ++j) cin >> ys[i][j];
    }
    double Dorig, Sorig;
    cin >> Dorig >> Sorig;
    double k = 0.6;
    double w1 = (1.0 - k) / Dorig;
    double w2 = k / Sorig;
    
    const double INF = 1e100;
    const double BIGSLOPE = 1e12; // Large penalty when dx == 0 and ascending
    
    // Precompute directed minimal costs between cities (over landing points)
    vector<vector<double>> dirCost(M, vector<double>(M, INF));
    for (int i = 0; i < M; ++i) {
        for (int j = 0; j < M; ++j) if (i != j) {
            int dx = abs(x[i] - x[j]);
            double best = INF;
            const auto &Yi = ys[i];
            const auto &Yj = ys[j];
            for (int a = 0; a < (int)Yi.size(); ++a) {
                int yi = Yi[a];
                for (int b = 0; b < (int)Yj.size(); ++b) {
                    int yj = Yj[b];
                    int dy = yj - yi;
                    double dist = hypot2((double)dx, (double)dy);
                    double slope = 0.0;
                    if (dy > 0) {
                        if (dx > 0) slope = (double)dy / (double)dx;
                        else slope = BIGSLOPE;
                    } else slope = 0.0;
                    double cost = w1 * dist + w2 * slope;
                    if (cost < best) best = cost;
                }
            }
            dirCost[i][j] = best;
        }
    }
    // Symmetric cost for building/optimizing order (heuristic)
    vector<vector<double>> symCost(M, vector<double>(M, INF));
    for (int i = 0; i < M; ++i) {
        for (int j = i+1; j < M; ++j) {
            double c = min(dirCost[i][j], dirCost[j][i]);
            symCost[i][j] = symCost[j][i] = c;
        }
        symCost[i][i] = INF;
    }
    
    auto tourCostSym = [&](const vector<int> &ord)->double{
        double s = 0.0;
        int m = ord.size();
        for (int i = 0; i < m; ++i) {
            int a = ord[i];
            int b = ord[(i+1)%m];
            s += symCost[a][b];
        }
        return s;
    };
    
    // Build initial candidates
    vector<vector<int>> candidates;
    // By x increasing
    vector<int> order(M);
    iota(order.begin(), order.end(), 0);
    sort(order.begin(), order.end(), [&](int a, int b){ if (x[a] != x[b]) return x[a] < x[b]; return a < b; });
    candidates.push_back(order);
    // By x decreasing
    vector<int> order2 = order;
    reverse(order2.begin(), order2.end());
    candidates.push_back(order2);
    // Nearest neighbor from seeds
    auto nearest_neighbor = [&](int start)->vector<int>{
        vector<int> ord;
        ord.reserve(M);
        vector<char> vis(M, 0);
        int cur = start;
        ord.push_back(cur);
        vis[cur] = 1;
        for (int t = 1; t < M; ++t) {
            int best = -1;
            double bestc = INF;
            for (int j = 0; j < M; ++j) if (!vis[j]) {
                double c = symCost[cur][j];
                if (c < bestc) {
                    bestc = c;
                    best = j;
                }
            }
            if (best == -1) {
                for (int j = 0; j < M; ++j) if (!vis[j]) { best = j; break; }
            }
            cur = best;
            vis[cur] = 1;
            ord.push_back(cur);
        }
        return ord;
    };
    // Seeds: min x, max x, minimal row sum, random seeds
    int minx_idx = int(min_element(x.begin(), x.end()) - x.begin());
    int maxx_idx = int(max_element(x.begin(), x.end()) - x.begin());
    candidates.push_back(nearest_neighbor(minx_idx));
    candidates.push_back(nearest_neighbor(maxx_idx));
    // minimal row sum
    vector<double> rowSum(M, 0.0);
    for (int i = 0; i < M; ++i) {
        double s = 0.0;
        for (int j = 0; j < M; ++j) if (i != j) s += symCost[i][j];
        rowSum[i] = s;
    }
    int minRowIdx = int(min_element(rowSum.begin(), rowSum.end()) - rowSum.begin());
    candidates.push_back(nearest_neighbor(minRowIdx));
    // Random seeds
    std::mt19937_64 rng(std::chrono::steady_clock::now().time_since_epoch().count());
    for (int t = 0; t < 2; ++t) {
        int s = rng() % M;
        candidates.push_back(nearest_neighbor(s));
    }
    
    // Pick best initial by sym cost
    double bestSym = 1e300;
    vector<int> bestOrder;
    for (auto &cand : candidates) {
        double c = tourCostSym(cand);
        if (c < bestSym) {
            bestSym = c;
            bestOrder = cand;
        }
    }
    if (bestOrder.empty()) {
        bestOrder.resize(M);
        iota(bestOrder.begin(), bestOrder.end(), 0);
    }
    
    // 2-Opt improvement on symmetric cost
    auto tStart = chrono::steady_clock::now();
    auto secondsElapsed = [&](){
        return chrono::duration<double>(chrono::steady_clock::now() - tStart).count();
    };
    const double max2OptTime = 2.5; // seconds
    if (M >= 4) {
        bool improved = true;
        while (improved && secondsElapsed() < max2OptTime) {
            improved = false;
            for (int i = 0; i < M - 1; ++i) {
                int a = bestOrder[i];
                int b = bestOrder[i+1];
                for (int k = i + 2; k < M; ++k) {
                    if (i == 0 && k == M - 1) continue;
                    int c = bestOrder[k];
                    int d = bestOrder[(k + 1) % M];
                    double delta = - symCost[a][b] - symCost[c][d] + symCost[a][c] + symCost[b][d];
                    if (delta < -1e-12) {
                        reverse(bestOrder.begin() + i + 1, bestOrder.begin() + k + 1);
                        improved = true;
                        break;
                    }
                }
                if (improved) {
                    if (secondsElapsed() >= max2OptTime) break;
                }
            }
        }
    }
    
    // DP to choose landing points for the final order
    int m = M;
    vector<int> orderFinal = bestOrder;
    vector<int> nCity(m);
    for (int i = 0; i < m; ++i) nCity[i] = (int)ys[orderFinal[i]].size();
    // Precompute cost matrices for consecutive pairs along the order (including last->first)
    vector<vector<vector<double>>> costMat(m);
    for (int i = 0; i < m; ++i) {
        int ci = orderFinal[i];
        int cj = orderFinal[(i + 1) % m];
        int ni = nCity[i];
        int nj = nCity[(i + 1) % m];
        costMat[i].assign(ni, vector<double>(nj, 0.0));
        int dx = abs(x[ci] - x[cj]);
        for (int a = 0; a < ni; ++a) {
            int yi = ys[ci][a];
            for (int b = 0; b < nj; ++b) {
                int yj = ys[cj][b];
                int dy = yj - yi;
                double dist = hypot2((double)dx, (double)dy);
                double slope = 0.0;
                if (dy > 0) {
                    if (dx > 0) slope = (double)dy / (double)dx;
                    else slope = BIGSLOPE;
                } else slope = 0.0;
                costMat[i][a][b] = w1 * dist + w2 * slope;
            }
        }
    }
    
    // Ring DP over first city's possible landing point
    int n0 = nCity[0];
    vector<vector<vector<int>>> prevIndex(m); // prevIndex[i][u][s] = predecessor index at i-1 when reaching i:u with start s
    for (int i = 0; i < m; ++i) {
        prevIndex[i].assign(nCity[i], vector<int>(n0, -1));
    }
    vector<int> lastChoice(n0, -1);
    vector<double> bestForStart(n0, INF);
    
    vector<double> dp, ndp;
    for (int s = 0; s < n0; ++s) {
        dp.assign(n0, INF);
        dp[s] = 0.0;
        // forward DP through cities 1..m-1
        for (int i = 0; i < m - 1; ++i) {
            int ni = nCity[i];
            int nj = nCity[i+1];
            ndp.assign(nj, INF);
            for (int v = 0; v < ni; ++v) {
                double base = dp[v];
                if (!(base < INF/2)) continue;
                const vector<double> &row = costMat[i][v];
                for (int u = 0; u < nj; ++u) {
                    double val = base + row[u];
                    if (val < ndp[u]) {
                        ndp[u] = val;
                        prevIndex[i+1][u][s] = v;
                    }
                }
            }
            dp.swap(ndp);
        }
        // Close the cycle from city m-1 to city 0 (index s)
        double bestTot = INF;
        int bestU = -1;
        int nm1 = nCity[m-1];
        for (int u = 0; u < nm1; ++u) {
            double val = dp[u] + costMat[m-1][u][s];
            if (val < bestTot) {
                bestTot = val;
                bestU = u;
            }
        }
        bestForStart[s] = bestTot;
        lastChoice[s] = bestU;
    }
    // Choose best start index s
    int bestS = 0;
    double bestCycleCost = bestForStart[0];
    for (int s = 1; s < n0; ++s) {
        if (bestForStart[s] < bestCycleCost) {
            bestCycleCost = bestForStart[s];
            bestS = s;
        }
    }
    // Reconstruct selection
    vector<int> chosenIdx(m, 0);
    chosenIdx[0] = bestS;
    int cur = lastChoice[bestS];
    chosenIdx[m-1] = cur;
    for (int i = m - 1; i >= 1; --i) {
        int prev = prevIndex[i][cur][bestS];
        chosenIdx[i-1] = prev;
        cur = prev;
    }
    // Output
    // Format: (city_id, landing_point_index)@(city_id, landing_point_index)@...
    for (int i = 0; i < m; ++i) {
        if (i) cout << "@";
        int cityId = orderFinal[i] + 1;
        int lpIdx = chosenIdx[i] + 1;
        cout << "(" << cityId << "," << lpIdx << ")";
    }
    cout << "\n";
    return 0;
}