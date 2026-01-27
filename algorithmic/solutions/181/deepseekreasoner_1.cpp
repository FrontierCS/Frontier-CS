#include <iostream>
#include <vector>
#include <algorithm>
#include <random>
#include <chrono>
#include <cmath>
#include <numeric>

using namespace std;

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(nullptr);
    cout.tie(nullptr);

    int n;
    cin >> n;
    vector<vector<char>> D(n, vector<char>(n));
    vector<vector<char>> F(n, vector<char>(n));
    
    for (int i = 0; i < n; ++i)
        for (int j = 0; j < n; ++j) {
            int x;
            cin >> x;
            D[i][j] = static_cast<char>(x);
        }
    for (int i = 0; i < n; ++i)
        for (int j = 0; j < n; ++j) {
            int x;
            cin >> x;
            F[i][j] = static_cast<char>(x);
        }

    long long totalFlow = 0;
    for (int i = 0; i < n; ++i)
        for (int j = 0; j < n; ++j)
            totalFlow += F[i][j];

    if (totalFlow == 0) {
        for (int i = 1; i <= n; ++i)
            cout << i << " \n"[i == n];
        return 0;
    }

    vector<long long> flow(n, 0), dist(n, 0);
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < n; ++j) {
            flow[i] += F[i][j];
            dist[i] += D[i][j];
        }
    }
    // add incoming flows/distances
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < n; ++j) {
            flow[i] += F[j][i];
            dist[i] += D[j][i];
        }
    }

    vector<int> facilities(n), locations(n);
    iota(facilities.begin(), facilities.end(), 0);
    iota(locations.begin(), locations.end(), 0);
    sort(facilities.begin(), facilities.end(),
         [&](int i, int j) { return flow[i] > flow[j]; });
    sort(locations.begin(), locations.end(),
         [&](int i, int j) { return dist[i] < dist[j]; });

    vector<int> p(n);
    for (int i = 0; i < n; ++i)
        p[facilities[i]] = locations[i];

    // compute initial cost
    long long cost = 0;
    for (int i = 0; i < n; ++i) {
        int pi = p[i];
        for (int j = 0; j < n; ++j)
            cost += static_cast<long long>(F[i][j]) * D[pi][p[j]];
    }

    vector<int> best_p = p;
    long long best_cost = cost;

    // random generator
    mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());
    uniform_int_distribution<int> rand_idx(0, n-1);
    uniform_real_distribution<double> rand_real(0.0, 1.0);

    double T = 10.0;
    const double cooling = 0.99995;
    const int iterations = 50000;

    for (int iter = 0; iter < iterations; ++iter) {
        int a = rand_idx(rng);
        int b = rand_idx(rng);
        if (a == b) continue;

        long long delta = 0;
        int pa = p[a], pb = p[b];
        for (int k = 0; k < n; ++k) {
            if (k == a || k == b) continue;
            int pk = p[k];
            delta += F[a][k] * (D[pb][pk] - D[pa][pk]);
            delta += F[k][a] * (D[pk][pb] - D[pk][pa]);
            delta += F[b][k] * (D[pa][pk] - D[pb][pk]);
            delta += F[k][b] * (D[pk][pa] - D[pk][pb]);
        }
        // diagonal terms
        delta += F[a][a] * (D[pb][pb] - D[pa][pa]);
        delta += F[b][b] * (D[pa][pa] - D[pb][pb]);
        // pair (a,b)
        delta += F[a][b] * (D[pb][pa] - D[pa][pb]);
        delta += F[b][a] * (D[pa][pb] - D[pb][pa]);

        if (delta < 0 || rand_real(rng) < exp(-delta / T)) {
            swap(p[a], p[b]);
            cost += delta;
            if (cost < best_cost) {
                best_cost = cost;
                best_p = p;
            }
        }
        T *= cooling;
    }

    for (int i = 0; i < n; ++i)
        cout << best_p[i] + 1 << " \n"[i == n-1];

    return 0;
}