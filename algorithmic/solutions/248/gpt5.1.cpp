#include <bits/stdc++.h>
using namespace std;

struct City {
    int x;
    vector<int> y;
};

const double K_WEIGHT = 0.6;
const double EPS = 1e-12;

vector<City> cities;
double Dnorm, Snorm;

inline double edgeCostDirCity(int ci, int li, int cj, int lj) {
    const City &A = cities[ci];
    const City &B = cities[cj];
    double x1 = (double)A.x;
    double y1 = (double)A.y[li];
    double x2 = (double)B.x;
    double y2 = (double)B.y[lj];
    double dx = fabs(x2 - x1);
    double dy = y2 - y1;
    double dist = hypot(dx, dy);
    double slope = 0.0;
    if (dy > 0.0) {
        if (dx > 1e-9) slope = dy / dx;
        else slope = 0.0;
    }
    return Dnorm * dist + Snorm * slope;
}

inline double edgeCostSym(int ci, int cj, const vector<int> &landing) {
    const City &A = cities[ci];
    const City &B = cities[cj];
    int li = landing[ci];
    int lj = landing[cj];
    double x1 = (double)A.x;
    double y1 = (double)A.y[li];
    double x2 = (double)B.x;
    double y2 = (double)B.y[lj];
    double dx = fabs(x2 - x1);
    double dy = y2 - y1;
    double dist = hypot(dx, dy);
    double slopeApprox = 0.0;
    if (dx > 1e-9) {
        slopeApprox = (fabs(dy) / dx) * 0.5;
    }
    return Dnorm * dist + Snorm * slopeApprox;
}

double totalDirCost(const vector<int> &order, const vector<int> &landing) {
    int N = (int)order.size();
    double res = 0.0;
    for (int i = 0; i < N; ++i) {
        int ci = order[i];
        int cj = order[(i + 1) % N];
        res += edgeCostDirCity(ci, landing[ci], cj, landing[cj]);
    }
    return res;
}

bool optimizeLandingsOnePass(const vector<int> &order, vector<int> &landing, double &currDirCost) {
    bool improved = false;
    int N = (int)order.size();
    for (int pos = 0; pos < N; ++pos) {
        int ci = order[pos];
        const City &C = cities[ci];
        int num = (int)C.y.size();
        if (num <= 1) continue;
        int cp = order[(pos - 1 + N) % N];
        int cn = order[(pos + 1) % N];
        int lcp = landing[cp];
        int lci = landing[ci];
        int lcn = landing[cn];

        double oldEdges = edgeCostDirCity(cp, lcp, ci, lci) +
                          edgeCostDirCity(ci, lci, cn, lcn);
        double bestLocal = oldEdges;
        int bestIdx = lci;

        for (int li = 0; li < num; ++li) {
            if (li == lci) continue;
            double cand = edgeCostDirCity(cp, lcp, ci, li) +
                          edgeCostDirCity(ci, li, cn, lcn);
            if (cand + EPS < bestLocal) {
                bestLocal = cand;
                bestIdx = li;
            }
        }

        if (bestIdx != lci) {
            landing[ci] = bestIdx;
            currDirCost += (bestLocal - oldEdges);
            improved = true;
        }
    }
    return improved;
}

bool twoOptSymIteration(vector<int> &order, const vector<int> &landing, double &currDirCost) {
    bool anyImproved = false;
    int N = (int)order.size();
    while (true) {
        bool accepted = false;
        for (int i = 0; i < N && !accepted; ++i) {
            int a = order[i];
            int b = order[(i + 1) % N];
            for (int k = i + 2; k < N; ++k) {
                if (i == 0 && k == N - 1) continue;
                int c = order[k];
                int d = order[(k + 1) % N];

                double oldSym = edgeCostSym(a, b, landing) + edgeCostSym(c, d, landing);
                double newSym = edgeCostSym(a, c, landing) + edgeCostSym(b, d, landing);
                if (newSym + EPS < oldSym) {
                    // Try this move in terms of directed cost.
                    reverse(order.begin() + i + 1, order.begin() + k + 1);
                    double newDir = totalDirCost(order, landing);
                    if (newDir + EPS < currDirCost) {
                        currDirCost = newDir;
                        accepted = true;
                        anyImproved = true;
                    } else {
                        // Revert
                        reverse(order.begin() + i + 1, order.begin() + k + 1);
                    }
                }
            }
        }
        if (!accepted) break;
    }
    return anyImproved;
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
    cities.resize(M);
    for (int i = 0; i < M; ++i) {
        int n, x;
        cin >> n >> x;
        cities[i].x = x;
        cities[i].y.resize(n);
        for (int j = 0; j < n; ++j) cin >> cities[i].y[j];
    }
    double Dorig, Sorig;
    cin >> Dorig >> Sorig;

    Dnorm = (1.0 - K_WEIGHT) / Dorig;
    Snorm = K_WEIGHT / Sorig;

    // Prepare initial landing choices: median altitude per city.
    vector<int> initialLanding(M);
    for (int i = 0; i < M; ++i) {
        int n = (int)cities[i].y.size();
        vector<int> idx(n);
        iota(idx.begin(), idx.end(), 0);
        sort(idx.begin(), idx.end(), [&](int a, int b) {
            return cities[i].y[a] < cities[i].y[b];
        });
        initialLanding[i] = idx[n / 2];
    }

    // Base order sorted by x-coordinate.
    vector<int> ascOrder(M);
    iota(ascOrder.begin(), ascOrder.end(), 0);
    sort(ascOrder.begin(), ascOrder.end(), [&](int a, int b) {
        if (cities[a].x != cities[b].x) return cities[a].x < cities[b].x;
        return a < b;
    });

    mt19937_64 rng((uint64_t)chrono::steady_clock::now().time_since_epoch().count());

    vector<int> bestFinalOrder;
    vector<int> bestFinalLanding;
    double bestFinalCost = 1e100;

    const int NUM_STARTS = 3;
    const int MAX_OUTER_ITERS = 60;

    for (int startType = 0; startType < NUM_STARTS; ++startType) {
        vector<int> order = ascOrder;
        if (startType == 1) {
            reverse(order.begin(), order.end());
        } else if (startType == 2) {
            shuffle(order.begin(), order.end(), rng);
        }

        vector<int> landing = initialLanding;

        double currCost = totalDirCost(order, landing);

        for (int iter = 0; iter < MAX_OUTER_ITERS; ++iter) {
            bool improved = false;
            if (optimizeLandingsOnePass(order, landing, currCost)) improved = true;
            if (twoOptSymIteration(order, landing, currCost)) improved = true;
            if (!improved) break;
        }

        // Evaluate both orientations.
        double costForward = currCost;
        vector<int> revOrder(order.rbegin(), order.rend());
        double costRev = totalDirCost(revOrder, landing);

        if (costForward <= costRev) {
            if (costForward < bestFinalCost) {
                bestFinalCost = costForward;
                bestFinalOrder = order;
                bestFinalLanding = landing;
            }
        } else {
            if (costRev < bestFinalCost) {
                bestFinalCost = costRev;
                bestFinalOrder = revOrder;
                bestFinalLanding = landing;
            }
        }
    }

    // Output best solution.
    int N = (int)bestFinalOrder.size();
    for (int i = 0; i < N; ++i) {
        int ci = bestFinalOrder[i];
        int li = bestFinalLanding[ci];
        cout << "(" << (ci + 1) << "," << (li + 1) << ")";
        if (i + 1 < N) cout << "@";
    }
    return 0;
}