#include <bits/stdc++.h>
using namespace std;

struct City {
    int id; // 1-based original id
    double x;
    vector<double> ys;
};

static const double K_WEIGHT = 0.6;
static const double INF = 1e100;
static const double BIG_SLOPE = 1e12;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    // Time management
    auto start_time = chrono::steady_clock::now();
    auto time_limit = chrono::milliseconds(14500); // keep some margin

    // Read input
    double base;
    if (!(cin >> base)) return 0;
    int M;
    cin >> M;
    vector<City> cities(M);
    for (int i = 0; i < M; ++i) {
        int n;
        double x;
        cin >> n >> x;
        cities[i].id = i + 1;
        cities[i].x = x;
        cities[i].ys.resize(n);
        for (int j = 0; j < n; ++j) {
            double y;
            cin >> y;
            cities[i].ys[j] = y;
        }
    }
    double D_orig, S_orig;
    cin >> D_orig >> S_orig;

    double dw = (1.0 - K_WEIGHT) / (D_orig == 0 ? 1.0 : D_orig);
    double sw = (K_WEIGHT) / (S_orig == 0 ? 1.0 : S_orig);

    int N = M;

    // Precompute |dx| matrix
    vector<vector<double>> dxabs(N, vector<double>(N, 0.0));
    for (int i = 0; i < N; ++i) {
        for (int j = i+1; j < N; ++j) {
            double dx = fabs(cities[i].x - cities[j].x);
            dxabs[i][j] = dxabs[j][i] = dx;
        }
    }

    auto edgeCostY = [&](int a, int ay, int b, int by) -> double {
        double dx = dxabs[a][b];
        double ya = cities[a].ys[ay];
        double yb = cities[b].ys[by];
        double dy = fabs(ya - yb);
        double dist = sqrt(dx*dx + dy*dy);
        double slope = 0.0;
        if (yb > ya) {
            if (dx > 0) slope = (yb - ya) / dx;
            else slope = BIG_SLOPE;
        }
        return dist * dw + slope * sw;
    };

    auto totalCost = [&](const vector<int>& route, const vector<int>& selY) -> double {
        double sum = 0.0;
        for (int i = 0; i < N; ++i) {
            int a = route[i];
            int b = route[(i+1)%N];
            sum += edgeCostY(a, selY[a], b, selY[b]);
        }
        return sum;
    };

    auto optimizeY = [&](const vector<int>& route, vector<int>& selY) {
        bool improved = true;
        int passes = 0;
        while (improved) {
            if (chrono::steady_clock::now() - start_time > time_limit) break;
            improved = false;
            ++passes;
            if (passes > 50) break;
            for (int idx = 0; idx < N; ++idx) {
                int c = route[idx];
                int p = route[(idx - 1 + N) % N];
                int n = route[(idx + 1) % N];
                int bestY = selY[c];
                double bestCost = edgeCostY(p, selY[p], c, selY[c]) + edgeCostY(c, selY[c], n, selY[n]);
                int sz = (int)cities[c].ys.size();
                for (int y = 0; y < sz; ++y) {
                    if (y == selY[c]) continue;
                    double newCost = edgeCostY(p, selY[p], c, y) + edgeCostY(c, y, n, selY[n]);
                    if (newCost + 1e-12 < bestCost) {
                        bestCost = newCost;
                        bestY = y;
                    }
                }
                if (bestY != selY[c]) {
                    selY[c] = bestY;
                    improved = true;
                }
            }
        }
    };

    auto twoOptImprove = [&](vector<int>& route, const vector<int>& selY) -> bool {
        bool improved_any = false;
        bool improved = true;
        while (improved) {
            if (chrono::steady_clock::now() - start_time > time_limit) break;
            improved = false;
            for (int i = 0; i < N; ++i) {
                int a = route[i];
                int b = route[(i+1)%N];
                double cab = edgeCostY(a, selY[a], b, selY[b]);
                for (int k = i+2; k < N; ++k) {
                    if (k == i) continue;
                    int c = route[k];
                    int d = route[(k+1)%N];
                    if (d == a) continue; // skip full cycle reversal
                    double ccd = edgeCostY(c, selY[c], d, selY[d]);
                    double cad = edgeCostY(a, selY[a], c, selY[c]);
                    double cbd = edgeCostY(b, selY[b], d, selY[d]);
                    double delta = (cad + cbd) - (cab + ccd);
                    if (delta + 1e-12 < 0) {
                        // reverse segment (i+1..k)
                        int l = i+1, r = k;
                        while (l < r) {
                            swap(route[l], route[r]);
                            ++l; --r;
                        }
                        improved = true;
                        improved_any = true;
                        break;
                    }
                }
                if (improved) break;
            }
        }
        return improved_any;
    };

    auto buildRouteSortedX = [&]() -> vector<int> {
        vector<int> order(N);
        iota(order.begin(), order.end(), 0);
        stable_sort(order.begin(), order.end(), [&](int a, int b){
            if (cities[a].x != cities[b].x) return cities[a].x < cities[b].x;
            return cities[a].id < cities[b].id;
        });
        return order;
    };

    auto buildRouteNN = [&](int start, const vector<int>& selYInit) -> vector<int> {
        vector<int> route;
        route.reserve(N);
        vector<char> used(N, 0);
        int cur = start;
        used[cur] = 1;
        route.push_back(cur);
        for (int step = 1; step < N; ++step) {
            if (chrono::steady_clock::now() - start_time > time_limit) break;
            double best = INF;
            int bestj = -1;
            for (int j = 0; j < N; ++j) {
                if (used[j]) continue;
                double c = edgeCostY(cur, selYInit[cur], j, selYInit[j]);
                if (c < best) {
                    best = c;
                    bestj = j;
                }
            }
            if (bestj == -1) break;
            used[bestj] = 1;
            route.push_back(bestj);
            cur = bestj;
        }
        // If something went wrong, fill remaining
        if ((int)route.size() < N) {
            for (int j = 0; j < N; ++j) if (!used[j]) route.push_back(j);
        }
        return route;
    };

    // Initial selection of y: choose median index
    vector<int> selY(N, 0);
    for (int i = 0; i < N; ++i) {
        int sz = (int)cities[i].ys.size();
        selY[i] = sz / 2;
    }

    // Try multiple initial routes
    vector<vector<int>> candidates;

    // 1) Sorted by x ascending
    candidates.push_back(buildRouteSortedX());

    // 2) Sorted by x descending
    {
        auto r = buildRouteSortedX();
        reverse(r.begin(), r.end());
        candidates.push_back(r);
    }

    // 3-5) Nearest neighbor from a few starts
    vector<int> starts;
    // leftmost, rightmost, middle by x
    auto sorted = buildRouteSortedX();
    if (!sorted.empty()) {
        starts.push_back(sorted.front());
        starts.push_back(sorted.back());
        starts.push_back(sorted[sorted.size()/2]);
    }
    // ensure unique
    sort(starts.begin(), starts.end());
    starts.erase(unique(starts.begin(), starts.end()), starts.end());
    for (int st : starts) {
        candidates.push_back(buildRouteNN(st, selY));
    }

    // Evaluate candidates with y-optimization and pick best
    vector<int> bestRoute;
    vector<int> bestSelY;
    double bestCost = INF;

    for (auto route : candidates) {
        if (chrono::steady_clock::now() - start_time > time_limit) break;
        vector<int> localSelY = selY;
        optimizeY(route, localSelY);
        // a light 2-opt pass
        twoOptImprove(route, localSelY);
        optimizeY(route, localSelY);
        double c = totalCost(route, localSelY);
        if (c < bestCost) {
            bestCost = c;
            bestRoute = move(route);
            bestSelY = move(localSelY);
        }
    }

    if (bestRoute.empty()) {
        bestRoute = buildRouteSortedX();
        bestSelY = selY;
    }

    // Main improvement loop
    while (chrono::steady_clock::now() - start_time < time_limit) {
        optimizeY(bestRoute, bestSelY);
        bool improvedRoute = twoOptImprove(bestRoute, bestSelY);
        if (!improvedRoute) {
            // Try a small perturbation if time allows
            if (chrono::steady_clock::now() - start_time > time_limit) break;
            // Random 2-opt perturbation
            static mt19937_64 rng(chrono::steady_clock::now().time_since_epoch().count());
            uniform_int_distribution<int> disti(0, N-1);
            int i = disti(rng);
            int k = disti(rng);
            if (abs(k - i) < 2) {
                k = (i + 2) % N;
            }
            if (i > k) swap(i, k);
            if (i == 0 && k == N-1) continue;
            int l = i+1, r = k;
            while (l < r) { swap(bestRoute[l], bestRoute[r]); ++l; --r; }
            // Re-opt y after perturbation
            optimizeY(bestRoute, bestSelY);
            // If still no improvement after perturbation pass 2-opt again, else break when time almost up
            twoOptImprove(bestRoute, bestSelY);
            // If no significant time left, exit
            if (chrono::steady_clock::now() - start_time > time_limit) break;
            // If no more improving moves likely, break
            // but continue loop to settle
            break;
        }
    }

    // Final Y optimization
    optimizeY(bestRoute, bestSelY);

    // Output
    // Format: (city_id, landing_point_index)@(city_id, landing_point_index)@...
    for (int i = 0; i < N; ++i) {
        int c = bestRoute[i];
        if (i) cout << "@";
        cout << "(" << cities[c].id << "," << (bestSelY[c] + 1) << ")";
    }
    cout << "\n";

    return 0;
}