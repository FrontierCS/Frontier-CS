#include <bits/stdc++.h>
using namespace std;

struct City {
    int id;
    int x;
    vector<int> ys;
    int n;
};

const double K_WEIGHT = 0.6;
const double INF = 1e100;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    double base;
    if(!(cin >> base)) {
        return 0;
    }
    int M;
    if(!(cin >> M)) {
        return 0;
    }
    
    vector<City> cities(M);
    for (int i = 0; i < M; ++i) {
        int n, x;
        cin >> n >> x;
        cities[i].id = i + 1;
        cities[i].x = x;
        cities[i].n = n;
        cities[i].ys.resize(n);
        for (int j = 0; j < n; ++j) cin >> cities[i].ys[j];
    }
    double D_in, S_in;
    cin >> D_in >> S_in;
    
    // Weights for combined cost
    double WD = (1.0 - K_WEIGHT) / D_in;
    double WS = (K_WEIGHT) / S_in;
    
    // Precompute pairwise weights for all (i->j) and all landing pairs
    vector<int> nSize(M);
    for (int i = 0; i < M; ++i) nSize[i] = cities[i].n;
    
    vector<vector<double*>> wMat(M, vector<double*>(M, nullptr));
    vector<vector<double>> dxAbs(M, vector<double>(M, 0.0));
    for (int i = 0; i < M; ++i) {
        for (int j = 0; j < M; ++j) {
            double dx = abs(cities[j].x - cities[i].x);
            dxAbs[i][j] = dx;
            if (i == j) continue;
            int ni = nSize[i], nj = nSize[j];
            double* arr = new double[ (size_t)ni * (size_t)nj ];
            // Precompute cost for all landing pairs (ai -> bj)
            for (int ai = 0; ai < ni; ++ai) {
                for (int bj = 0; bj < nj; ++bj) {
                    double dy = (double)cities[j].ys[bj] - (double)cities[i].ys[ai];
                    double dist = hypot(dx, dy);
                    double slope = 0.0;
                    if (dy > 0) {
                        if (dx > 0) slope = dy / dx;
                        else slope = INF; // prohibit vertical upward when dx == 0
                    }
                    double cost = WD * dist + WS * slope;
                    arr[(size_t)ai * (size_t)nj + (size_t)bj] = cost;
                }
            }
            wMat[i][j] = arr;
        }
    }
    
    auto compute_dp_for_order = [&](const vector<int>& perm, vector<int>& selection_out) -> double {
        int m = (int)perm.size();
        int firstCity = perm[0];
        int n0 = nSize[firstCity];
        double bestCycleCost = INF;
        int bestStartIdx = -1;

        // First pass: find best starting landing index s by cost (without storing preds)
        for (int s = 0; s < n0; ++s) {
            // Initialize dp for layer 1
            int city1 = perm[1];
            int n1 = nSize[city1];
            const double* w01 = wMat[firstCity][city1];
            vector<double> dpPrev(n1, INF);
            for (int j = 0; j < n1; ++j) {
                dpPrev[j] = w01[(size_t)s * (size_t)n1 + (size_t)j];
            }
            // Forward DP for layers 2..m-1
            for (int l = 2; l < m; ++l) {
                int prevCity = perm[l-1];
                int curCity = perm[l];
                int np = nSize[prevCity];
                int nc = nSize[curCity];
                const double* w = wMat[prevCity][curCity];
                vector<double> dpCurr(nc, INF);
                for (int j = 0; j < nc; ++j) {
                    double best = INF;
                    for (int k = 0; k < np; ++k) {
                        double cand = dpPrev[k] + w[(size_t)k * (size_t)nc + (size_t)j];
                        if (cand < best) best = cand;
                    }
                    dpCurr[j] = best;
                }
                dpPrev.swap(dpCurr);
            }
            // Close the cycle: last -> first(s)
            int lastCity = perm[m-1];
            int nl = nSize[lastCity];
            const double* wClose = wMat[lastCity][firstCity];
            double bestClose = INF;
            for (int j = 0; j < nl; ++j) {
                double cand = dpPrev[j] + wClose[(size_t)j * (size_t)n0 + (size_t)s];
                if (cand < bestClose) bestClose = cand;
            }
            if (bestClose < bestCycleCost) {
                bestCycleCost = bestClose;
                bestStartIdx = s;
            }
        }

        // Second pass: reconstruct selection with best start index
        // If no feasible (infinite) cost found, pick arbitrary selection
        selection_out.assign(m, 0);
        if (bestStartIdx == -1 || !(bestCycleCost < INF/2)) {
            // Fallback: choose first landing point for each city
            for (int i = 0; i < m; ++i) selection_out[i] = 0;
            return INF;
        } else {
            int s = bestStartIdx;
            // Initialize dp and preds for reconstruction
            int city1 = perm[1];
            int n1 = nSize[city1];
            const double* w01 = wMat[firstCity][city1];
            vector<double> dpPrev(n1, INF);
            vector<vector<int>> preds(m);
            preds[1].assign(n1, s);
            for (int j = 0; j < n1; ++j) {
                dpPrev[j] = w01[(size_t)s * (size_t)n1 + (size_t)j];
            }
            // Forward DP while storing predecessors
            for (int l = 2; l < m; ++l) {
                int prevCity = perm[l-1];
                int curCity = perm[l];
                int np = nSize[prevCity];
                int nc = nSize[curCity];
                const double* w = wMat[prevCity][curCity];
                vector<double> dpCurr(nc, INF);
                vector<int> pred(nc, -1);
                for (int j = 0; j < nc; ++j) {
                    double best = INF;
                    int bestk = -1;
                    for (int k = 0; k < np; ++k) {
                        double cand = dpPrev[k] + w[(size_t)k * (size_t)nc + (size_t)j];
                        if (cand < best) {
                            best = cand;
                            bestk = k;
                        }
                    }
                    dpCurr[j] = best;
                    pred[j] = bestk;
                }
                dpPrev.swap(dpCurr);
                preds[l] = move(pred);
            }
            // Choose last index minimizing close
            int lastCity = perm[m-1];
            int nl = nSize[lastCity];
            const double* wClose = wMat[lastCity][firstCity];
            double bestClose = INF;
            int bestLastIdx = -1;
            for (int j = 0; j < nl; ++j) {
                double cand = dpPrev[j] + wClose[(size_t)j * (size_t)n0 + (size_t)s];
                if (cand < bestClose) {
                    bestClose = cand;
                    bestLastIdx = j;
                }
            }
            // Reconstruct
            selection_out[m-1] = bestLastIdx;
            for (int l = m-1; l >= 2; --l) {
                selection_out[l-1] = preds[l][ selection_out[l] ];
            }
            selection_out[0] = s;
            return bestClose;
        }
    };
    
    // Build initial orders: ascending x and descending x
    vector<int> orderAsc(M), orderDesc(M);
    vector<int> idxs(M);
    iota(idxs.begin(), idxs.end(), 0);
    sort(idxs.begin(), idxs.end(), [&](int a, int b){
        if (cities[a].x != cities[b].x) return cities[a].x < cities[b].x;
        return cities[a].id < cities[b].id;
    });
    for (int i = 0; i < M; ++i) {
        orderAsc[i] = idxs[i];
        orderDesc[i] = idxs[M-1 - i];
    }
    
    vector<int> selAsc, selDesc;
    double costAsc = compute_dp_for_order(orderAsc, selAsc);
    double costDesc = compute_dp_for_order(orderDesc, selDesc);
    
    vector<int> bestOrder;
    vector<int> bestSel;
    double bestCost;
    if (costAsc <= costDesc) {
        bestOrder = move(orderAsc);
        bestSel = move(selAsc);
        bestCost = costAsc;
    } else {
        bestOrder = move(orderDesc);
        bestSel = move(selDesc);
        bestCost = costDesc;
    }
    
    // Output in required format
    // Pairs: (city_id,landing_point_index) with 1-based indices
    for (int i = 0; i < M; ++i) {
        int cityIdx = bestOrder[i];
        int landingIdx = bestSel[i] + 1;
        cout << "(" << cities[cityIdx].id << "," << landingIdx << ")";
        if (i + 1 < M) cout << "@";
    }
    cout << "\n";
    
    // Cleanup
    for (int i = 0; i < M; ++i) {
        for (int j = 0; j < M; ++j) {
            if (wMat[i][j]) {
                delete[] wMat[i][j];
            }
        }
    }
    return 0;
}