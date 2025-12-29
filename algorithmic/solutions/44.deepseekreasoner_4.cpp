#include <bits/stdc++.h>
using namespace std;

double dist(int a, int b, const vector<long long>& x, const vector<long long>& y) {
    double dx = x[a] - x[b];
    double dy = y[a] - y[b];
    return sqrt(dx*dx + dy*dy);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    
    int N;
    cin >> N;
    vector<long long> x(N), y(N);
    for (int i = 0; i < N; i++) {
        cin >> x[i] >> y[i];
    }
    
    // Precompute primes
    vector<bool> is_prime(N, true);
    if (N > 0) is_prime[0] = false;
    if (N > 1) is_prime[1] = false;
    for (int i = 2; i * i < N; i++) {
        if (is_prime[i]) {
            for (int j = i * i; j < N; j += i) {
                is_prime[j] = false;
            }
        }
    }
    
    // Build strips
    int S = max(1, (int)sqrt(N));
    int strip_size = N / S;
    int rem = N % S;
    vector<vector<int>> strips(S);
    int idx = 0;
    for (int s = 0; s < S; s++) {
        int start = idx;
        int end = start + strip_size + (s < rem ? 1 : 0);
        for (int i = start; i < end; i++) {
            strips[s].push_back(i);
        }
        idx = end;
    }
    
    // Sort each strip by y
    for (int s = 0; s < S; s++) {
        sort(strips[s].begin(), strips[s].end(), [&](int a, int b) {
            return y[a] < y[b];
        });
    }
    
    // Function to build tour given direction for strip 0 (dir0 = 1 for increasing, -1 for decreasing)
    auto build_tour = [&](int dir0, double& totalDist) -> vector<int> {
        vector<int> tour;
        tour.push_back(0);
        int current = 0;
        totalDist = 0.0;
        for (int s = 0; s < S; s++) {
            vector<int> cities;
            // copy strip s, excluding city 0 if s==0
            for (int id : strips[s]) {
                if (s == 0 && id == 0) continue;
                cities.push_back(id);
            }
            if (cities.empty()) continue;
            int dir = (s % 2 == 0) ? dir0 : -dir0;
            if (dir == -1) {
                reverse(cities.begin(), cities.end());
            }
            for (int id : cities) {
                double d = dist(current, id, x, y);
                totalDist += d;
                tour.push_back(id);
                current = id;
            }
        }
        // return to 0
        totalDist += dist(current, 0, x, y);
        tour.push_back(0);
        return tour;
    };
    
    double dist1, dist2;
    vector<int> tour1 = build_tour(1, dist1);
    vector<int> tour2 = build_tour(-1, dist2);
    
    vector<int> P;
    if (dist1 < dist2) {
        P = tour1;
    } else {
        P = tour2;
    }
    
    // Now P is the initial tour of size N+1
    // Precompute d and m arrays
    vector<double> d(N+1, 0.0); // d[t] for step t=1..N
    vector<double> m(N+1, 1.0); // multiplier for step t
    double totalL = 0.0;
    for (int t = 1; t <= N; t++) {
        int src = P[t-1];
        int dst = P[t];
        d[t] = dist(src, dst, x, y);
        if (t % 10 == 0 && !is_prime[src]) {
            m[t] = 1.1;
        }
        totalL += m[t] * d[t];
    }
    
    // Post-processing: try to improve penalties
    if (N >= 10) {
        int window = 100; // search window
        for (int pos = 9; pos < N; pos += 10) {
            if (is_prime[P[pos]]) continue;
            // look for a prime within window ahead
            int best_j = -1;
            double best_delta = 0.0;
            for (int j = pos+1; j <= min(N-1, pos+window); j++) {
                if (!is_prime[P[j]]) continue;
                // compute delta for swapping pos and j
                double delta = 0.0;
                if (j == pos+1) {
                    // adjacent swap
                    int i = pos;
                    // steps i, i+1, i+2
                    int step_i = i;
                    int step_i1 = i+1;
                    int step_i2 = i+2;
                    double old_cost = m[step_i]*d[step_i] + m[step_i1]*d[step_i1] + m[step_i2]*d[step_i2];
                    // new distances
                    double new_d_i = dist(P[i-1], P[i+1], x, y);
                    double new_d_i1 = dist(P[i+1], P[i], x, y);
                    double new_d_i2 = dist(P[i], P[i+2], x, y);
                    double new_m_i = m[step_i];
                    double new_m_i1 = (step_i1 % 10 == 0 && !is_prime[P[i+1]]) ? 1.1 : 1.0;
                    double new_m_i2 = (step_i2 % 10 == 0 && !is_prime[P[i]]) ? 1.1 : 1.0;
                    double new_cost = new_m_i * new_d_i + new_m_i1 * new_d_i1 + new_m_i2 * new_d_i2;
                    delta = new_cost - old_cost;
                } else {
                    int i = pos;
                    int step_i = i;
                    int step_i1 = i+1;
                    int step_j = j;
                    int step_j1 = j+1;
                    double old_cost = m[step_i]*d[step_i] + m[step_i1]*d[step_i1] + m[step_j]*d[step_j] + m[step_j1]*d[step_j1];
                    double new_d_i = dist(P[i-1], P[j], x, y);
                    double new_d_i1 = dist(P[j], P[i+1], x, y);
                    double new_d_j = dist(P[j-1], P[i], x, y);
                    double new_d_j1 = dist(P[i], P[j+1], x, y);
                    double new_m_i = m[step_i];
                    double new_m_i1 = (step_i1 % 10 == 0 && !is_prime[P[j]]) ? 1.1 : 1.0;
                    double new_m_j = m[step_j];
                    double new_m_j1 = (step_j1 % 10 == 0 && !is_prime[P[i]]) ? 1.1 : 1.0;
                    double new_cost = new_m_i * new_d_i + new_m_i1 * new_d_i1 + new_m_j * new_d_j + new_m_j1 * new_d_j1;
                    delta = new_cost - old_cost;
                }
                if (delta < best_delta) {
                    best_delta = delta;
                    best_j = j;
                }
            }
            if (best_j != -1 && best_delta < -1e-9) {
                // Perform swap
                swap(P[pos], P[best_j]);
                // Update d and m arrays
                if (best_j == pos+1) {
                    int i = pos;
                    d[i] = dist(P[i-1], P[i], x, y);
                    d[i+1] = dist(P[i], P[i+1], x, y);
                    d[i+2] = dist(P[i+1], P[i+2], x, y);
                    if ((i+1) % 10 == 0) {
                        m[i+1] = (!is_prime[P[i]]) ? 1.1 : 1.0;
                    } else {
                        m[i+1] = 1.0;
                    }
                    if ((i+2) % 10 == 0) {
                        m[i+2] = (!is_prime[P[i+1]]) ? 1.1 : 1.0;
                    } else {
                        m[i+2] = 1.0;
                    }
                } else {
                    int i = pos;
                    int j = best_j;
                    d[i] = dist(P[i-1], P[i], x, y);
                    d[i+1] = dist(P[i], P[i+1], x, y);
                    d[j] = dist(P[j-1], P[j], x, y);
                    d[j+1] = dist(P[j], P[j+1], x, y);
                    if ((i+1) % 10 == 0) {
                        m[i+1] = (!is_prime[P[i]]) ? 1.1 : 1.0;
                    } else {
                        m[i+1] = 1.0;
                    }
                    if ((j+1) % 10 == 0) {
                        m[j+1] = (!is_prime[P[j]]) ? 1.1 : 1.0;
                    } else {
                        m[j+1] = 1.0;
                    }
                }
                totalL += best_delta;
            }
        }
    }
    
    // Output
    cout << N+1 << "\n";
    for (int i = 0; i <= N; i++) {
        cout << P[i] << "\n";
    }
    
    return 0;
}