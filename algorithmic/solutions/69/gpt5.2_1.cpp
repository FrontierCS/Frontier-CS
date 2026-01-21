#include <bits/stdc++.h>
using namespace std;

static vector<int> sieve_primes(int N) {
    vector<bool> isPrime(N + 1, true);
    if (N >= 0) isPrime[0] = false;
    if (N >= 1) isPrime[1] = false;
    for (int i = 2; 1LL * i * i <= N; i++) {
        if (!isPrime[i]) continue;
        for (int j = i * i; j <= N; j += i) isPrime[j] = false;
    }
    vector<int> primes;
    for (int i = 2; i <= N; i++) if (isPrime[i]) primes.push_back(i);
    return primes;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    int M = 15 * n;
    int maxN = 30 * n + 2;

    auto primes = sieve_primes(maxN);

    int L = 15 * n + 2;
    int R = 30 * n;

    vector<int> Q;
    Q.reserve(n);
    for (int p : primes) {
        if (p < L || p > R) continue;
        if (!Q.empty() && p - Q.back() == 2) continue; // avoid twin primes in chosen set
        Q.push_back(p);
        if ((int)Q.size() == n) break;
    }

    // Fallback (should never trigger for n<=1000): allow any primes in [L,R] and brute-search collision-free subset
    if ((int)Q.size() < n) {
        vector<int> cand;
        for (int p : primes) if (p >= L && p <= R) cand.push_back(p);
        mt19937_64 rng(chrono::high_resolution_clock::now().time_since_epoch().count());
        bool ok = false;
        for (int attempt = 0; attempt < 200 && !ok; attempt++) {
            shuffle(cand.begin(), cand.end(), rng);
            Q.assign(cand.begin(), cand.begin() + min<int>(n, (int)cand.size()));
            if ((int)Q.size() < n) break;

            unordered_set<long long> seen;
            seen.reserve((size_t)n * (size_t)n * 13 / 10 + 10);
            ok = true;
            for (int u = 0; u < n && ok; u++) {
                for (int v = 0; v < n; v++) {
                    long long pval = 1LL * (Q[u] + 2) * Q[v] - 1;
                    if (!seen.insert(pval).second) { ok = false; break; }
                }
            }
        }
        if (!ok) return 0;
    }

    vector<int> idx(maxN + 1, 0);
    for (int i = 0; i < n; i++) idx[Q[i]] = i + 1;

    string tail(M, 'X');
    for (int i = 0; i < n; i++) {
        int a = Q[i] - (M + 1);
        if (a < 0) a = 0;
        cout << string(a, 'X') << 'O' << tail << '\n';
    }
    cout.flush();

    int q;
    if (!(cin >> q)) return 0;

    for (int qi = 0; qi < q; qi++) {
        long long p;
        cin >> p;
        long long x = p + 1;

        int ansU = -1, ansV = -1;
        for (int v = 0; v < n; v++) {
            int qv = Q[v];
            if (x % qv != 0) continue;
            long long t = x / qv;
            long long uQ = t - 2;
            if (uQ >= 0 && uQ <= maxN && idx[(int)uQ] != 0) {
                ansU = idx[(int)uQ];
                ansV = v + 1;
                break;
            }
        }

        if (ansU < 0) { // should not happen
            ansU = 1; ansV = 1;
        }
        cout << ansU << ' ' << ansV << '\n';
        cout.flush();
    }

    return 0;
}