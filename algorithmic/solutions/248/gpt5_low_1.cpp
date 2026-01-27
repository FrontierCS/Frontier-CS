#include <bits/stdc++.h>
using namespace std;

struct City {
    int id;
    int x;
    vector<int> ys;
};

static inline double edge_cost(double x1, double y1, double x2, double y2, double wD, double wS) {
    double dx = fabs(x2 - x1);
    double dy = y2 - y1;
    double dist = hypot(dx, dy);
    double slope = (dy > 0 ? dy / max(dx, 1e-6) : 0.0);
    return wD * dist + wS * slope;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    double base;
    if(!(cin >> base)) return 0;
    int M;
    cin >> M;
    vector<City> cities(M);
    for (int i = 0; i < M; ++i) {
        int n, x;
        cin >> n >> x;
        cities[i].id = i + 1;
        cities[i].x = x;
        cities[i].ys.resize(n);
        for (int j = 0; j < n; ++j) cin >> cities[i].ys[j];
    }
    double Dnorm, Snorm;
    cin >> Dnorm >> Snorm;

    const double k = 0.6;
    double wD = (1.0 - k) / Dnorm;
    double wS = (k) / Snorm;

    // Initial order: sort by x ascending
    vector<int> ord(M);
    iota(ord.begin(), ord.end(), 0);
    stable_sort(ord.begin(), ord.end(), [&](int a, int b){
        if (cities[a].x != cities[b].x) return cities[a].x < cities[b].x;
        return cities[a].id < cities[b].id;
    });

    // Initial y selection: choose min y for each city
    vector<int> chosen(M);
    for (int idx = 0; idx < M; ++idx) {
        int ci = ord[idx];
        int bestk = 0;
        for (int kidx = 1; kidx < (int)cities[ci].ys.size(); ++kidx) {
            if (cities[ci].ys[kidx] < cities[ci].ys[bestk]) bestk = kidx;
        }
        chosen[ci] = bestk;
    }

    auto total_cost = [&](const vector<int>& ordRef, const vector<int>& chosenRef)->double{
        double sum = 0.0;
        for (int i = 0; i < M; ++i) {
            int a = ordRef[i];
            int b = ordRef[(i+1)%M];
            double x1 = cities[a].x, y1 = cities[a].ys[ chosenRef[a] ];
            double x2 = cities[b].x, y2 = cities[b].ys[ chosenRef[b] ];
            sum += edge_cost(x1, y1, x2, y2, wD, wS);
        }
        return sum;
    };

    auto improve_y_given_order = [&](vector<int>& ordRef, vector<int>& chosenRef){
        bool improved = true;
        int passes = 0;
        while (improved && passes < 50) {
            improved = false;
            ++passes;
            for (int pos = 0; pos < M; ++pos) {
                int i_city = ordRef[pos];
                int prev_city = ordRef[(pos-1+M)%M];
                int next_city = ordRef[(pos+1)%M];
                double x_prev = cities[prev_city].x, y_prev = cities[prev_city].ys[ chosenRef[prev_city] ];
                double x_next = cities[next_city].x, y_next = cities[next_city].ys[ chosenRef[next_city] ];
                // current cost involving i_city
                double x_i = cities[i_city].x, y_i_cur = cities[i_city].ys[ chosenRef[i_city] ];
                double cur = edge_cost(x_prev, y_prev, x_i, y_i_cur, wD, wS) + edge_cost(x_i, y_i_cur, x_next, y_next, wD, wS);
                int bestk = chosenRef[i_city];
                double best = cur;
                for (int kidx = 0; kidx < (int)cities[i_city].ys.size(); ++kidx) {
                    if (kidx == chosenRef[i_city]) continue;
                    double y_i_new = cities[i_city].ys[kidx];
                    double cand = edge_cost(x_prev, y_prev, x_i, y_i_new, wD, wS) + edge_cost(x_i, y_i_new, x_next, y_next, wD, wS);
                    if (cand + 1e-12 < best) {
                        best = cand;
                        bestk = kidx;
                    }
                }
                if (bestk != chosenRef[i_city]) {
                    chosenRef[i_city] = bestk;
                    improved = true;
                }
            }
        }
    };

    auto two_opt_improve = [&](vector<int>& ordRef, const vector<int>& chosenRef){
        bool improved = true;
        int N = M;
        int iter = 0;
        while (improved && iter < 50) { // limit sweeps
            improved = false;
            ++iter;
            for (int i = 0; i < N; ++i) {
                int a = ordRef[i];
                int b = ordRef[(i+1)%N];
                double xa = cities[a].x, ya = cities[a].ys[ chosenRef[a] ];
                double xb = cities[b].x, yb = cities[b].ys[ chosenRef[b] ];
                for (int j = i+2; j < N; ++j) {
                    if ((j+1)%N == i) continue; // skip adjacent wrap
                    int c = ordRef[j];
                    int d = ordRef[(j+1)%N];
                    double xc = cities[c].x, yc = cities[c].ys[ chosenRef[c] ];
                    double xd = cities[d].x, yd = cities[d].ys[ chosenRef[d] ];
                    double before = edge_cost(xa, ya, xb, yb, wD, wS) + edge_cost(xc, yc, xd, yd, wD, wS);
                    double after  = edge_cost(xa, ya, xc, yc, wD, wS) + edge_cost(xb, yb, xd, yd, wD, wS);
                    if (after + 1e-12 < before) {
                        // reverse segment (i+1..j)
                        int l = i+1, r = j;
                        while (l < r) {
                            swap(ordRef[l], ordRef[r]);
                            ++l; --r;
                        }
                        improved = true;
                        // update a,b for new b (still ord[i+1]) and continue local search
                        b = ordRef[(i+1)%N];
                        xb = cities[b].x; yb = cities[b].ys[ chosenRef[b] ];
                    }
                }
            }
        }
    };

    // Initial local optimization
    improve_y_given_order(ord, chosen);
    two_opt_improve(ord, chosen);
    improve_y_given_order(ord, chosen);

    // Try a few random perturbations within time to escape local minima
    auto start = chrono::steady_clock::now();
    double bestCost = total_cost(ord, chosen);
    vector<int> bestOrd = ord;
    vector<int> bestChosen = chosen;

    std::mt19937 rng(1234567);
    int attempts = 0;
    while (true) {
        auto now = chrono::steady_clock::now();
        double elapsed = chrono::duration<double>(now - start).count();
        if (elapsed > 13.5) break;
        ++attempts;
        vector<int> ord2 = bestOrd;
        vector<int> chosen2 = bestChosen;
        // random shuffle windows or small swap
        if (M >= 4) {
            int a = rng() % M;
            int b = rng() % M;
            if (a > b) swap(a,b);
            if (a == b) {
                b = (a + 1) % M;
                if (a > b) swap(a,b);
            }
            // reverse segment
            reverse(ord2.begin()+a, ord2.begin()+b+1);
        } else {
            shuffle(ord2.begin(), ord2.end(), rng);
        }
        improve_y_given_order(ord2, chosen2);
        two_opt_improve(ord2, chosen2);
        improve_y_given_order(ord2, chosen2);
        double cst = total_cost(ord2, chosen2);
        if (cst + 1e-9 < bestCost) {
            bestCost = cst;
            bestOrd.swap(ord2);
            bestChosen.swap(chosen2);
        }
    }

    // Output
    // Format: (city_id, landing_point_index)@(city_id, landing_point_index)@...
    for (int i = 0; i < M; ++i) {
        int ci = bestOrd[i];
        if (i) cout << "@";
        cout << "(" << cities[ci].id << "," << (bestChosen[ci] + 1) << ")";
    }
    cout << "\n";
    return 0;
}