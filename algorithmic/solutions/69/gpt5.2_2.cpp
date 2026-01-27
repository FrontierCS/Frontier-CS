#include <bits/stdc++.h>
using namespace std;

static vector<int> sieve_primes(int maxN) {
    vector<bool> isPrime(maxN + 1, true);
    if (maxN >= 0) isPrime[0] = false;
    if (maxN >= 1) isPrime[1] = false;
    for (int i = 2; 1LL * i * i <= maxN; i++) {
        if (!isPrime[i]) continue;
        for (int j = i * i; j <= maxN; j += i) isPrime[j] = false;
    }
    vector<int> primes;
    for (int i = 2; i <= maxN; i++) if (isPrime[i]) primes.push_back(i);
    return primes;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    int maxLen = 30 * n;
    int K = 15 * n;

    auto primesAll = sieve_primes(maxLen);
    vector<int> lens;
    lens.reserve(n);

    unordered_set<int> chosen;
    for (int p : primesAll) {
        if (p < K + 2) continue;
        if ((int)lens.size() >= n) break;
        if (chosen.find(p - 2) != chosen.end()) continue; // avoid twin primes among chosen
        chosen.insert(p);
        lens.push_back(p);
    }

    if ((int)lens.size() < n) {
        // Extremely unlikely for given constraints, but keep a fallback without twin restriction.
        lens.clear();
        for (int p : primesAll) {
            if (p < K + 2) continue;
            lens.push_back(p);
            if ((int)lens.size() >= n) break;
        }
    }

    unordered_map<long long, int> lenToIdx;
    lenToIdx.reserve(n * 2);
    for (int i = 0; i < n; i++) lenToIdx[lens[i]] = i + 1;

    string suf(K, 'X');
    for (int i = 0; i < n; i++) {
        int p = lens[i];
        int a = p - K - 1;
        cout << string(a, 'X') << 'O' << suf << '\n';
    }
    cout.flush();

    int q;
    cin >> q;
    for (int qi = 0; qi < q; qi++) {
        long long P;
        cin >> P;
        long long N = P + 1;

        int u = -1, v = -1;
        for (int i = 0; i < n; i++) {
            long long pv = lens[i];
            if (N % pv != 0) continue;
            long long pu = N / pv - 2;
            auto it = lenToIdx.find(pu);
            if (it != lenToIdx.end()) {
                v = i + 1;
                u = it->second;
                break;
            }
        }

        if (u < 0) { // safety fallback; should never happen
            u = 1; v = 1;
        }

        cout << u << ' ' << v << '\n';
        cout.flush();
    }
    return 0;
}