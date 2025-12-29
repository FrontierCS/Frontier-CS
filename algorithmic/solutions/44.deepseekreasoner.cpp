#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    
    int N;
    cin >> N;
    
    // Read coordinates (ignored, but required by input format)
    for (int i = 0; i < N; ++i) {
        int x, y;
        cin >> x >> y;
    }
    
    // Sieve of Eratosthenes up to N-1
    vector<bool> isPrime(N, false);
    if (N > 2) {
        for (int i = 2; i < N; ++i) isPrime[i] = true;
        for (int i = 2; i * i < N; ++i) {
            if (isPrime[i]) {
                for (int j = i * i; j < N; j += i) {
                    isPrime[j] = false;
                }
            }
        }
    }
    
    // Collect prime city IDs (2 to N-1)
    vector<int> primes;
    for (int i = 2; i < N; ++i) {
        if (isPrime[i]) primes.push_back(i);
    }
    
    // Positions in the tour that must hold primes (if possible):
    // For step t = 10,20,..., source index is t-1 = 9,19,...
    int K = N / 10;                     // number of penalized steps
    vector<int> required_pos;
    for (int i = 1; i <= K; ++i) {
        int pos = 10 * i - 1;           // 0‑based index in P
        if (pos <= N - 1) {
            required_pos.push_back(pos);
        }
    }
    
    // Tour array, P[0] = P[N] = 0
    vector<int> P(N + 1, -1);
    P[0] = 0;
    P[N] = 0;
    
    vector<bool> usedCity(N, false);
    int num_required = required_pos.size();
    int num_primes = primes.size();
    int assign_count = min(num_required, num_primes);
    
    // Assign the smallest primes to the required positions
    for (int i = 0; i < assign_count; ++i) {
        int pos = required_pos[i];
        int city = primes[i];
        P[pos] = city;
        usedCity[city] = true;
    }
    
    // Remaining cities (all except those already placed)
    vector<int> remaining;
    for (int i = 1; i < N; ++i) {
        if (!usedCity[i]) {
            remaining.push_back(i);
        }
    }
    
    // Free positions (those not yet assigned)
    vector<int> free_pos;
    for (int i = 1; i < N; ++i) {
        if (P[i] == -1) {
            free_pos.push_back(i);
        }
    }
    
    int M = remaining.size();
    // Create a zig‑zag order of the remaining cities
    vector<int> zigzag(M);
    int l = 0, r = M - 1;
    for (int i = 0; i < M; ++i) {
        if (i % 2 == 0) {
            zigzag[i] = remaining[l++];
        } else {
            zigzag[i] = remaining[r--];
        }
    }
    
    // Fill the free positions with the zig‑zag order
    for (int i = 0; i < M; ++i) {
        P[free_pos[i]] = zigzag[i];
    }
    
    // Output the tour
    cout << N + 1 << "\n";
    for (int i = 0; i <= N; ++i) {
        cout << P[i] << "\n";
    }
    
    return 0;
}