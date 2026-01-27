#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N;
    if (!(cin >> N)) return 0;
    vector<double> x(N), y(N);
    for (int i = 0; i < N; ++i) {
        long long xi, yi;
        cin >> xi >> yi;
        x[i] = (double)xi;
        y[i] = (double)yi;
    }
    
    // Sieve for primes up to N-1
    vector<char> isPrime(N, true);
    if (N > 0) isPrime[0] = false;
    if (N > 1) isPrime[1] = false;
    for (int i = 2; (long long)i * i < N; ++i) {
        if (isPrime[i]) {
            for (int j = i * i; j < N; j += i) isPrime[j] = false;
        }
    }
    
    // Initial path: 0,1,2,...,N-1,0
    vector<int> P(N + 1);
    P[0] = 0;
    for (int i = 1; i < N; ++i) P[i] = i;
    P[N] = 0;
    
    auto edge_cost = [&](int u, const int a, const int b) -> double {
        if (u < 0 || u >= N) return 0.0;
        auto getCity = [&](int idx) -> int {
            if (idx == a) return P[b];
            if (idx == b) return P[a];
            return P[idx];
        };
        int s = getCity(u);
        int t = getCity(u + 1);
        double dx = x[s] - x[t];
        double dy = y[s] - y[t];
        double d = sqrt(dx * dx + dy * dy);
        double mult = (((u + 1) % 10 == 0) && !isPrime[s]) ? 1.1 : 1.0;
        return d * mult;
    };
    
    auto current_edge_cost = [&](int u) -> double {
        if (u < 0 || u >= N) return 0.0;
        int s = P[u];
        int t = P[u + 1];
        double dx = x[s] - x[t];
        double dy = y[s] - y[t];
        double d = sqrt(dx * dx + dy * dy);
        double mult = (((u + 1) % 10 == 0) && !isPrime[s]) ? 1.1 : 1.0;
        return d * mult;
    };
    
    // Try local swaps around every 10th step source position
    int k = 3; // window size
    for (int pos = 9; pos <= N - 1; pos += 10) {
        if (isPrime[P[pos]]) continue;
        int bestj = -1;
        double bestDelta = 0.0; // we look for negative delta
        // Consider candidates within [-k..k] excluding 0
        for (int d = 1; d <= k; ++d) {
            int j1 = pos - d;
            if (j1 >= 1 && isPrime[P[j1]]) {
                // compute delta for swapping pos and j1
                vector<int> us = {pos - 1, pos, j1 - 1, j1};
                sort(us.begin(), us.end());
                us.erase(unique(us.begin(), us.end()), us.end());
                double before = 0.0, after = 0.0;
                for (int u : us) before += current_edge_cost(u);
                for (int u : us) after += edge_cost(u, pos, j1);
                double delta = after - before;
                if (bestj == -1 || delta < bestDelta) {
                    bestj = j1;
                    bestDelta = delta;
                }
            }
            int j2 = pos + d;
            if (j2 <= N - 1 && isPrime[P[j2]]) {
                vector<int> us = {pos - 1, pos, j2 - 1, j2};
                sort(us.begin(), us.end());
                us.erase(unique(us.begin(), us.end()), us.end());
                double before = 0.0, after = 0.0;
                for (int u : us) before += current_edge_cost(u);
                for (int u : us) after += edge_cost(u, pos, j2);
                double delta = after - before;
                if (bestj == -1 || delta < bestDelta) {
                    bestj = j2;
                    bestDelta = delta;
                }
            }
        }
        if (bestj != -1 && bestDelta < -1e-12) {
            swap(P[pos], P[bestj]);
        }
    }
    
    cout << (N + 1) << '\n';
    for (int i = 0; i <= N; ++i) {
        cout << P[i] << '\n';
    }
    return 0;
}