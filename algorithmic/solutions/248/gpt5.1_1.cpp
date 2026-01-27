#include <bits/stdc++.h>
using namespace std;

const int MAX_M = 205;
const int MAX_P = 20;

struct City {
    int id;
    int x;
    vector<int> ys;
    double repY;
};

int M;
vector<City> cities;

double distApprox[MAX_M][MAX_M];
double costAdj[MAX_M][MAX_P][MAX_P];
double costWrap[MAX_P][MAX_P];
double dpArr[MAX_M][MAX_P];
int parentArr[MAX_P][MAX_M][MAX_P];

const double K_WEIGHT = 0.6;
double wDist, wSlope;

double edgeCost(int cityA, int pointA, int cityB, int pointB) {
    const City &A = cities[cityA];
    const City &B = cities[cityB];
    double dx = (double)B.x - (double)A.x;
    double dy = (double)B.ys[pointB] - (double)A.ys[pointA];
    double dist = sqrt(dx * dx + dy * dy);
    double slope = 0.0;
    if (dy > 0) {
        double absdx = fabs(dx);
        if (absdx < 1e-9) slope = 1e6;
        else slope = dy / absdx;
    }
    return dist * wDist + slope * wSlope;
}

vector<int> nearestNeighbor(int start) {
    int N = M;
    vector<int> order;
    order.reserve(N);
    vector<char> used(N, 0);
    int cur = start;
    order.push_back(cur);
    used[cur] = 1;
    for (int step = 1; step < N; ++step) {
        int best = -1;
        double bestDist = 1e100;
        for (int j = 0; j < N; ++j) {
            if (!used[j]) {
                double d = distApprox[cur][j];
                if (d < bestDist) {
                    bestDist = d;
                    best = j;
                }
            }
        }
        order.push_back(best);
        used[best] = 1;
        cur = best;
    }
    return order;
}

void twoOptEuclidean(vector<int> &order) {
    int N = (int)order.size();
    if (N <= 3) return;
    bool improved = true;
    while (improved) {
        improved = false;
        for (int i = 1; i < N - 1; ++i) {
            int a = order[i - 1];
            int b = order[i];
            double dab = distApprox[a][b];
            for (int j = i + 1; j < N; ++j) {
                int c = order[j];
                int d = (j + 1 < N ? order[j + 1] : order[0]);
                if (d == a) continue;
                double dcd = distApprox[c][d];
                double newCost = distApprox[a][c] + distApprox[b][d];
                if (newCost + 1e-9 < dab + dcd) {
                    reverse(order.begin() + i, order.begin() + j + 1);
                    improved = true;
                    break;
                }
            }
            if (improved) break;
        }
    }
}

struct DPResult {
    double cost;
    vector<int> assign; // landing point index per position (0-based)
};

DPResult solveForOrder(const vector<int> &order) {
    int N = (int)order.size();
    vector<int> n(N);
    for (int i = 0; i < N; ++i) {
        n[i] = (int)cities[order[i]].ys.size();
    }

    // Precompute adjacency costs between consecutive positions
    for (int p = 0; p < N - 1; ++p) {
        int cityA = order[p];
        int cityB = order[p + 1];
        int na = n[p];
        int nb = n[p + 1];
        for (int ia = 0; ia < na; ++ia) {
            for (int ib = 0; ib < nb; ++ib) {
                costAdj[p][ia][ib] = edgeCost(cityA, ia, cityB, ib);
            }
        }
    }
    // Wrap-around cost from last to first
    {
        int p = N - 1;
        int cityA = order[p];
        int cityB = order[0];
        int na = n[p];
        int nb = n[0];
        for (int ia = 0; ia < na; ++ia) {
            for (int ib = 0; ib < nb; ++ib) {
                costWrap[ia][ib] = edgeCost(cityA, ia, cityB, ib);
            }
        }
    }

    const double INF = 1e100;
    double bestTotal = INF;
    int bestRoot = -1;
    int bestLastPt = -1;

    if (N == 1) {
        DPResult res;
        res.cost = 0.0;
        res.assign.assign(1, 0);
        return res;
    }

    int numRootPoints = n[0];
    for (int r = 0; r < numRootPoints; ++r) {
        int idx1 = 1;
        int n1 = n[idx1];
        for (int j = 0; j < n1; ++j) {
            dpArr[idx1][j] = costAdj[0][r][j];
            parentArr[r][idx1][j] = r;
        }

        for (int i = 2; i < N; ++i) {
            int ni = n[i];
            int niprev = n[i - 1];
            for (int pi = 0; pi < ni; ++pi) dpArr[i][pi] = INF;
            for (int pj = 0; pj < niprev; ++pj) {
                double prev = dpArr[i - 1][pj];
                if (prev >= INF) continue;
                for (int pi = 0; pi < ni; ++pi) {
                    double cand = prev + costAdj[i - 1][pj][pi];
                    if (cand < dpArr[i][pi]) {
                        dpArr[i][pi] = cand;
                        parentArr[r][i][pi] = pj;
                    }
                }
            }
        }

        int nLast = n[N - 1];
        for (int last = 0; last < nLast; ++last) {
            double total = dpArr[N - 1][last] + costWrap[last][r];
            if (total < bestTotal) {
                bestTotal = total;
                bestRoot = r;
                bestLastPt = last;
            }
        }
    }

    vector<int> assign(N);
    assign[N - 1] = bestLastPt;
    for (int pos = N - 1; pos >= 1; --pos) {
        int prev = parentArr[bestRoot][pos][assign[pos]];
        assign[pos - 1] = prev;
    }

    DPResult res;
    res.cost = bestTotal;
    res.assign = std::move(assign);
    return res;
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
        cities[i].id = i + 1;
        int n, x;
        cin >> n >> x;
        cities[i].x = x;
        cities[i].ys.resize(n);
        long long sumY = 0;
        for (int j = 0; j < n; ++j) {
            int y;
            cin >> y;
            cities[i].ys[j] = y;
            sumY += y;
        }
        cities[i].repY = (double)sumY / (double)n;
    }
    double Dnorm, Snorm;
    cin >> Dnorm >> Snorm;
    if (Dnorm <= 0) Dnorm = 1.0;
    if (Snorm <= 0) Snorm = 1.0;
    wDist = (1.0 - K_WEIGHT) / Dnorm;
    wSlope = K_WEIGHT / Snorm;

    // Build approximate distance matrix for TSP (using representative y)
    for (int i = 0; i < M; ++i) {
        distApprox[i][i] = 0.0;
        for (int j = i + 1; j < M; ++j) {
            double dx = (double)cities[i].x - (double)cities[j].x;
            double dy = cities[i].repY - cities[j].repY;
            double d = sqrt(dx * dx + dy * dy);
            distApprox[i][j] = distApprox[j][i] = d;
        }
    }

    mt19937 rng(123456);

    vector<vector<int>> candidateOrders;
    candidateOrders.reserve(50);

    auto addCandidate = [&](const vector<int> &order) {
        candidateOrders.push_back(order);
        vector<int> rev = order;
        reverse(rev.begin(), rev.end());
        candidateOrders.push_back(std::move(rev));
    };

    // Candidate 1: cities sorted by x
    vector<int> ordX(M);
    iota(ordX.begin(), ordX.end(), 0);
    sort(ordX.begin(), ordX.end(), [&](int a, int b) {
        if (cities[a].x != cities[b].x) return cities[a].x < cities[b].x;
        return cities[a].repY < cities[b].repY;
    });
    addCandidate(ordX);

    // Candidate 2: two-opt improved sorted-by-x tour
    vector<int> ordX2 = ordX;
    twoOptEuclidean(ordX2);
    addCandidate(ordX2);

    // Additional candidates from nearest-neighbor with different starts
    int restarts = min(M, 8);
    for (int r = 0; r < restarts; ++r) {
        int start = r;
        vector<int> ordNN = nearestNeighbor(start);
        twoOptEuclidean(ordNN);
        addCandidate(ordNN);
    }

    double globalBestCost = 1e100;
    vector<int> globalBestOrder;
    vector<int> globalBestAssign;

    for (const auto &ord : candidateOrders) {
        DPResult res = solveForOrder(ord);
        if (res.cost < globalBestCost) {
            globalBestCost = res.cost;
            globalBestOrder = ord;
            globalBestAssign = res.assign;
        }
    }

    // Output
    string sep = "";
    int N = (int)globalBestOrder.size();
    for (int i = 0; i < N; ++i) {
        int cityIdx = globalBestOrder[i];
        int cityId = cities[cityIdx].id;
        int landingIdx = globalBestAssign[i] + 1; // 1-based
        cout << sep << "(" << cityId << "," << landingIdx << ")";
        sep = "@";
    }
    cout << "\n";

    return 0;
}