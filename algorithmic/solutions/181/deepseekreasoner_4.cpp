#include <bits/stdc++.h>
using namespace std;

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    cin >> n;
    
    vector<vector<int>> D(n, vector<int>(n));
    vector<vector<int>> F(n, vector<int>(n));
    
    for (int i = 0; i < n; ++i)
        for (int j = 0; j < n; ++j)
            cin >> D[i][j];
    
    for (int i = 0; i < n; ++i)
        for (int j = 0; j < n; ++j)
            cin >> F[i][j];
    
    // compute flow per facility (sum of row and column)
    vector<long long> flow(n, 0);
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < n; ++j) {
            flow[i] += F[i][j] + F[j][i];
        }
    }
    
    // compute distance per location (sum of row and column)
    vector<long long> dist(n, 0);
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < n; ++j) {
            dist[i] += D[i][j] + D[j][i];
        }
    }
    
    // sort facilities by flow descending, locations by distance ascending
    vector<int> facilities(n), locations(n);
    iota(facilities.begin(), facilities.end(), 0);
    iota(locations.begin(), locations.end(), 0);
    
    sort(facilities.begin(), facilities.end(),
         [&](int a, int b) { return flow[a] > flow[b]; });
    sort(locations.begin(), locations.end(),
         [&](int a, int b) { return dist[a] < dist[b]; });
    
    vector<int> p(n); // p[facility] = location
    for (int i = 0; i < n; ++i)
        p[facilities[i]] = locations[i];
    
    // compute initial cost
    long long cost = 0;
    for (int i = 0; i < n; ++i) {
        int pi = p[i];
        for (int j = 0; j < n; ++j) {
            int pj = p[j];
            cost += (long long)D[pi][pj] * F[i][j];
        }
    }
    
    // random number generation
    mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());
    uniform_real_distribution<double> rand_real(0.0, 1.0);
    uniform_int_distribution<int> rand_int(0, n - 1);
    
    // estimate initial temperature
    double avg_delta = 0.0;
    const int samples = 1000;
    for (int s = 0; s < samples; ++s) {
        int a = rand_int(rng);
        int b = rand_int(rng);
        while (b == a) b = rand_int(rng);
        int old_a = p[a];
        int old_b = p[b];
        long long delta = 0;
        for (int k = 0; k < n; ++k) {
            if (k == a || k == b) continue;
            int pk = p[k];
            delta += (D[old_b][pk] - D[old_a][pk]) * (F[a][k] - F[b][k]);
            delta += (D[pk][old_b] - D[pk][old_a]) * (F[k][a] - F[k][b]);
        }
        delta += (D[old_b][old_a] - D[old_a][old_b]) * (F[a][b] - F[b][a]);
        delta += (D[old_b][old_b] - D[old_a][old_a]) * (F[a][a] - F[b][b]);
        avg_delta += abs(delta);
    }
    avg_delta /= samples;
    double T = max(1.0, avg_delta / log(2.0));
    const double cooling = 0.99999;
    const int iterations = 500000;
    
    long long best_cost = cost;
    vector<int> best_p = p;
    
    for (int iter = 0; iter < iterations; ++iter) {
        int a = rand_int(rng);
        int b = rand_int(rng);
        while (b == a) b = rand_int(rng);
        
        int old_a = p[a];
        int old_b = p[b];
        
        long long delta = 0;
        for (int k = 0; k < n; ++k) {
            if (k == a || k == b) continue;
            int pk = p[k];
            delta += (D[old_b][pk] - D[old_a][pk]) * (F[a][k] - F[b][k]);
            delta += (D[pk][old_b] - D[pk][old_a]) * (F[k][a] - F[k][b]);
        }
        delta += (D[old_b][old_a] - D[old_a][old_b]) * (F[a][b] - F[b][a]);
        delta += (D[old_b][old_b] - D[old_a][old_a]) * (F[a][a] - F[b][b]);
        
        if (delta < 0 || rand_real(rng) < exp(-delta / T)) {
            cost += delta;
            swap(p[a], p[b]);
            if (cost < best_cost) {
                best_cost = cost;
                best_p = p;
            }
        }
        T *= cooling;
    }
    
    // output permutation (1-indexed)
    for (int i = 0; i < n; ++i) {
        cout << best_p[i] + 1 << (i + 1 == n ? '\n' : ' ');
    }
    
    return 0;
}