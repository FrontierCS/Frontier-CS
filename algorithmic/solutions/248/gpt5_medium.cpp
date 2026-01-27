#include <bits/stdc++.h>
using namespace std;

struct City {
    int x;
    vector<int> y;
};

static const double EPS = 1e-9;

struct Solver {
    int M;
    vector<City> cities;
    double Wd, Ws;
    vector<vector<double>> dx, invdx;

    Solver(int M, vector<City> cities, double Wd, double Ws)
        : M(M), cities(std::move(cities)), Wd(Wd), Ws(Ws) {
        precomputeDistances();
    }

    void precomputeDistances() {
        dx.assign(M, vector<double>(M, 0.0));
        invdx.assign(M, vector<double>(M, 0.0));
        for (int i = 0; i < M; ++i) {
            for (int j = 0; j < M; ++j) {
                double d = abs(cities[i].x - cities[j].x);
                dx[i][j] = d;
                invdx[i][j] = 1.0 / max(d, EPS);
            }
        }
    }

    inline double pairCost(int i, int idx_i, int j, int idx_j) const {
        double dxij = dx[i][j];
        double dy = (double)cities[j].y[idx_j] - (double)cities[i].y[idx_i];
        double dist = hypot(dxij, dy);
        double slope = dy > 0 ? dy * invdx[i][j] : 0.0;
        return dist * Wd + slope * Ws;
    }

    // DP to get best landing point indices for a fixed order perm
    double optimizeChoicesDP(const vector<int>& perm, vector<int>& choicePerCity) const {
        int N = (int)perm.size();
        vector<int> ms(N);
        for (int i = 0; i < N; ++i) ms[i] = (int)cities[perm[i]].y.size();

        int m0 = ms[0];
        double best_total = numeric_limits<double>::infinity();
        vector<int> best_selPos(N, 0);

        // Pre-allocate parent storage
        vector<vector<int>> parent(N);
        for (int i = 0; i < N; ++i) parent[i].assign(ms[i], -1);

        vector<double> dp, newdp;
        dp.assign(m0, numeric_limits<double>::infinity());

        for (int a0 = 0; a0 < m0; ++a0) {
            // Reset dp for this a0
            for (int t = 0; t < m0; ++t) dp[t] = numeric_limits<double>::infinity();
            dp[a0] = 0.0;

            // Forward DP
            for (int pos = 1; pos < N; ++pos) {
                int ci_prev = perm[pos - 1];
                int ci = perm[pos];
                int mp = ms[pos - 1];
                int m = ms[pos];
                newdp.assign(m, numeric_limits<double>::infinity());
                // Reset parents for this position
                // parent[pos] has size m, each entry stores best index from previous city
                for (int b = 0; b < m; ++b) parent[pos][b] = -1;

                for (int a = 0; a < mp; ++a) {
                    double base = dp[a];
                    if (base >= numeric_limits<double>::infinity()/2) continue;
                    for (int b = 0; b < m; ++b) {
                        double c = pairCost(ci_prev, a, ci, b);
                        double val = base + c;
                        if (val < newdp[b]) {
                            newdp[b] = val;
                            parent[pos][b] = a;
                        }
                    }
                }
                dp.swap(newdp);
            }

            // Close the cycle
            int last_city = perm[N - 1];
            int first_city = perm[0];
            int m_last = ms[N - 1];
            double best_end = numeric_limits<double>::infinity();
            int best_b = -1;
            for (int b = 0; b < m_last; ++b) {
                double total = dp[b] + pairCost(last_city, b, first_city, a0);
                if (total < best_end) {
                    best_end = total;
                    best_b = b;
                }
            }

            if (best_end < best_total) {
                best_total = best_end;
                // Reconstruct selections
                vector<int> selPos(N, 0);
                selPos[N - 1] = best_b;
                int cur = best_b;
                for (int pos = N - 1; pos >= 1; --pos) {
                    int p = parent[pos][cur];
                    selPos[pos - 1] = p;
                    cur = p;
                }
                // selPos[0] should be a0
                best_selPos = std::move(selPos);
            }
        }

        choicePerCity.assign(M, 0);
        for (int pos = 0; pos < N; ++pos) {
            int city = perm[pos];
            choicePerCity[city] = best_selPos[pos];
        }

        return best_total;
    }

    double totalCostGiven(const vector<int>& perm, const vector<int>& choicePerCity) const {
        double total = 0.0;
        int N = (int)perm.size();
        for (int i = 0; i < N; ++i) {
            int u = perm[i];
            int v = perm[(i + 1) % N];
            total += pairCost(u, choicePerCity[u], v, choicePerCity[v]);
        }
        return total;
    }

    void reverseSegment(vector<int>& perm, int l, int r) const {
        while (l < r) {
            swap(perm[l], perm[r]);
            ++l; --r;
        }
    }

    void solveAndOutput() {
        // Initial order: sort by x ascending, and also try reverse; pick better
        vector<int> order(M);
        iota(order.begin(), order.end(), 0);
        stable_sort(order.begin(), order.end(), [&](int a, int b){
            if (cities[a].x != cities[b].x) return cities[a].x < cities[b].x;
            return a < b;
        });
        vector<int> order_rev = order;
        reverse(order_rev.begin(), order_rev.end());

        vector<int> bestChoice(M, 0);
        vector<int> tmpChoice(M, 0);
        double bestCost = optimizeChoicesDP(order, bestChoice);
        double cost_rev = optimizeChoicesDP(order_rev, tmpChoice);
        vector<int> perm = order;
        if (cost_rev + 1e-12 < bestCost) {
            bestCost = cost_rev;
            bestChoice = tmpChoice;
            perm = order_rev;
        }

        // Iterative 2-opt local search with DP re-optimization
        auto start_time = chrono::high_resolution_clock::now();
        auto time_limit = 14.5; // seconds
        auto elapsed = [&]() {
            auto now = chrono::high_resolution_clock::now();
            double sec = chrono::duration<double>(now - start_time).count();
            return sec;
        };

        // Function to compute approximate delta using current choices
        auto approxDelta = [&](int i, int j, const vector<int>& p, const vector<int>& choice)->double{
            int N = (int)p.size();
            int a = p[i], b = p[(i + 1) % N];
            int c = p[j], d = p[(j + 1) % N];
            double oldc = pairCost(a, choice[a], b, choice[b]) + pairCost(c, choice[c], d, choice[d]);
            double newc = pairCost(a, choice[a], c, choice[c]) + pairCost(b, choice[b], d, choice[d]);
            return newc - oldc;
        };

        // 2-opt search
        while (elapsed() < time_limit) {
            bool improved = false;
            int N = (int)perm.size();
            int maxTries = 30;
            int tries = 0;

            // First-improvement with approximate delta
            for (int i = 0; i < N && !improved && elapsed() < time_limit; ++i) {
                for (int j = i + 2; j < N && !improved && elapsed() < time_limit; ++j) {
                    if (i == 0 && j == N - 1) continue;
                    double dlt = approxDelta(i, j, perm, bestChoice);
                    if (dlt < -1e-9) {
                        // Try this move
                        reverseSegment(perm, i + 1, j);
                        vector<int> newChoice(M, 0);
                        double newCost = optimizeChoicesDP(perm, newChoice);
                        if (newCost + 1e-12 < bestCost) {
                            bestCost = newCost;
                            bestChoice = std::move(newChoice);
                            improved = true;
                            break;
                        } else {
                            // revert
                            reverseSegment(perm, i + 1, j);
                            tries++;
                            if (tries >= maxTries) break;
                        }
                    }
                }
            }

            if (!improved) break;
        }

        // Output final sequence
        // Format: (city_id, landing_point_index)@(city_id, landing_point_index)@...
        // city_id and landing_point_index are 1-based
        for (int i = 0; i < (int)perm.size(); ++i) {
            int city = perm[i];
            int lp = bestChoice[city];
            cout << "(" << (city + 1) << "," << (lp + 1) << ")";
            if (i + 1 < (int)perm.size()) cout << "@";
        }
        cout << "\n";
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    double base;
    if (!(cin >> base)) {
        return 0;
    }
    int M;
    cin >> M;
    vector<City> cities(M);
    for (int i = 0; i < M; ++i) {
        int n, x;
        cin >> n >> x;
        cities[i].x = x;
        cities[i].y.resize(n);
        for (int j = 0; j < n; ++j) cin >> cities[i].y[j];
    }
    double D_in, S_in;
    cin >> D_in >> S_in;

    Solver solver(M, cities, D_in, S_in);
    solver.solveAndOutput();

    return 0;
}