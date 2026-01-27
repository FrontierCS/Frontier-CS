#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N;
    if (!(cin >> N)) return 0;
    long long x, y;
    for (int i = 0; i < N; ++i) {
        cin >> x >> y; // read and discard
    }
    
    // Sieve for primality up to N-1
    int M = max(2, N);
    vector<char> is_prime(M, true);
    is_prime[0] = is_prime[1] = false;
    for (int i = 2; i * 1LL * i < M; ++i) {
        if (is_prime[i]) {
            for (int j = i * i; j < M; j += i) is_prime[j] = false;
        }
    }
    
    // Build route with local window adjustments to favor primes at penalized steps
    const int W = 64; // window size for local adjustments
    deque<int> dq;
    dq.resize(N - 1);
    for (int i = 1; i <= N - 1; ++i) dq[i - 1] = i;
    
    vector<int> P(N + 1);
    P[0] = 0;
    for (int pos = 1; pos <= N - 1; ++pos) {
        bool penalized_next_step = ((pos + 1) % 10 == 0); // step t = pos+1
        if (dq.empty()) break;
        if (penalized_next_step) {
            // Prefer a prime at origin of next step (current position)
            int limit = min<int>(W, dq.size());
            int idx = 0;
            while (idx < limit && !is_prime[dq[idx]]) ++idx;
            if (idx > 0 && idx < limit) {
                for (int k = 0; k < idx; ++k) {
                    int v = dq.front(); dq.pop_front(); dq.push_back(v);
                }
            }
            // else: either front is already prime (idx==0) or no prime in window -> do nothing
        } else {
            // Prefer a non-prime here to save primes for penalized steps
            if (!dq.empty() && is_prime[dq.front()]) {
                int limit = min<int>(W, dq.size());
                int idx = 0;
                while (idx < limit && is_prime[dq[idx]]) ++idx;
                if (idx > 0 && idx < limit) {
                    for (int k = 0; k < idx; ++k) {
                        int v = dq.front(); dq.pop_front(); dq.push_back(v);
                    }
                }
                // else: all in window are prime or front non-prime already; proceed
            }
        }
        P[pos] = dq.front();
        dq.pop_front();
    }
    P[N] = 0;
    
    cout << (N + 1) << '\n';
    for (int i = 0; i <= N; ++i) {
        cout << P[i] << '\n';
    }
    return 0;
}