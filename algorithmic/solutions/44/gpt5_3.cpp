#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N;
    if (!(cin >> N)) return 0;
    vector<long long> x(N), y(N);
    for (int i = 0; i < N; ++i) cin >> x[i] >> y[i];

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
    for (int i = 1; i <= N - 1; ++i) P[i] = i;
    P[N] = 0;

    // For each multiple of 10 step, ensure source city is prime by local rotation within block
    int maxK = N / 10;
    for (int k = 1; k <= maxK; ++k) {
        int pos = 10 * k - 1; // source index for step t=10k
        if (pos < 1 || pos > N - 1) continue;
        if (isPrime[P[pos]]) continue;

        int l = 10 * k - 9;
        int r = min(10 * k, N - 1);
        l = max(l, 1);

        int chosen = -1;
        // Prefer closest to pos, check left then right for tie
        for (int d = 1; d <= 9; ++d) {
            int jl = pos - d;
            int jr = pos + d;
            if (jl >= l && isPrime[P[jl]]) { chosen = jl; break; }
            if (jr <= r && isPrime[P[jr]]) { chosen = jr; break; }
        }
        if (chosen == -1) continue;

        if (chosen < pos) {
            rotate(P.begin() + chosen, P.begin() + chosen + 1, P.begin() + pos + 1);
        } else if (chosen > pos) {
            rotate(P.begin() + pos, P.begin() + chosen, P.begin() + chosen + 1);
        }
    }

    cout << (N + 1) << '\n';
    for (int i = 0; i <= N; ++i) {
        cout << P[i] << '\n';
    }
    return 0;
}