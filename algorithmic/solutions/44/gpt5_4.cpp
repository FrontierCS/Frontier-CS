#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N;
    if (!(cin >> N)) return 0;
    vector<long long> x(N), y(N);
    for (int i = 0; i < N; ++i) cin >> x[i] >> y[i];
    
    // Sieve for primes over city IDs
    vector<char> isPrime(max(2, N), true);
    if (N > 0) isPrime[0] = false;
    if (N > 1) isPrime[1] = false;
    for (int i = 2; 1LL * i * i <= N - 1; ++i) {
        if (isPrime[i]) {
            for (int j = i * i; j <= N - 1; j += i) isPrime[j] = false;
        }
    }
    
    // Initial path: 0 -> 1 -> 2 -> ... -> N-1 -> 0
    vector<int> P(N + 1);
    P[0] = 0;
    for (int i = 1; i <= N - 1; ++i) P[i] = i;
    P[N] = 0;
    
    // Ensure positions at indices 9, 19, ... (0-based) start from prime cities if possible
    int ptr = 1;
    for (int idx = 1; idx <= N - 1; ++idx) {
        if (idx % 10 == 9) {
            if (!isPrime[P[idx]]) {
                if (ptr < idx + 1) ptr = idx + 1;
                while (ptr <= N - 1 && !isPrime[P[ptr]]) ++ptr;
                if (ptr <= N - 1) {
                    swap(P[idx], P[ptr]);
                    ++ptr;
                }
            }
        }
    }
    
    // Prefer to make the last step (N-th step from P[N-1] to 0) start from a prime city if N%10==0
    if (N % 10 == 0 && !isPrime[P[N - 1]]) {
        bool swapped = false;
        // Try to take a prime from a non-penalty index near the end
        for (int i = N - 2; i >= 1; --i) {
            if (i % 10 != 9 && isPrime[P[i]]) {
                swap(P[i], P[N - 1]);
                swapped = true;
                break;
            }
        }
        // If not found, relax and take from a penalty index near the end
        if (!swapped) {
            for (int i = N - 2; i >= 1; --i) {
                if (isPrime[P[i]]) {
                    swap(P[i], P[N - 1]);
                    swapped = true;
                    break;
                }
            }
        }
    }
    
    cout << (N + 1) << '\n';
    for (int i = 0; i <= N; ++i) {
        cout << P[i] << '\n';
    }
    return 0;
}