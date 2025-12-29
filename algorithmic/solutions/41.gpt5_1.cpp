#include <bits/stdc++.h>
using namespace std;

using u64 = unsigned long long;
using u128 = __uint128_t;

static vector<int> sieve(int limit) {
    vector<bool> isPrime(limit + 1, true);
    isPrime[0] = false;
    if (limit >= 1) isPrime[1] = false;
    for (int i = 2; (long long)i * i <= limit; ++i) {
        if (isPrime[i]) {
            for (long long j = 1LL * i * i; j <= limit; j += i)
                isPrime[(size_t)j] = false;
        }
    }
    vector<int> primes;
    primes.reserve(limit / 10);
    for (int i = 2; i <= limit; ++i)
        if (isPrime[i]) primes.push_back(i);
    return primes;
}

static vector<u64> buildDoubling(u64 n) {
    vector<u64> v;
    if (n == 0) return v;
    u64 x = 1;
    v.push_back(x);
    while (x <= n / 2) {
        x *= 2;
        v.push_back(x);
    }
    return v;
}

static vector<u64> buildPrimePairsSequence(u64 n) {
    vector<u64> v;
    if (n >= 1) v.push_back(1);
    if (n >= 2) v.push_back(2);
    if (n < 6) return v;

    long double ln = (long double)n;
    u64 s = (u64)floor(sqrtl(ln));
    int margin = 100000;
    int L = (int)min<u64>(s + margin, (u64)2000000); // cap just to be safe
    if (L < 3) L = 3;
    vector<int> primes = sieve(L);

    int lastIdx = -1;
    for (size_t i = 0; i + 1 < primes.size(); ++i) {
        u128 prod = (u128)primes[i] * (u128)primes[i + 1];
        if (prod <= n) {
            v.push_back((u64)prod);
            lastIdx = (int)i;
        } else {
            break;
        }
    }

    if (lastIdx >= 0) {
        int pm = primes[lastIdx];
        int pnext = primes[lastIdx + 1];
        u64 multiple = n / (u64)pnext;
        if (multiple > (u64)pm) {
            u128 t = (u128)pnext * (u128)multiple;
            if ((u64)t > v.back() && t <= n) v.push_back((u64)t);
        }
    }

    // Try to append n itself if it helps
    if (!v.empty() && n > v.back()) {
        u64 a = v.back();
        u64 b = v.size() >= 2 ? v[v.size() - 2] : 0;
        u64 gprev = std::gcd(a, b);
        u64 gnew = std::gcd(n, a);
        if (gnew > gprev) v.push_back(n);
    }

    return v;
}

static u128 sequenceValue(const vector<u64>& v) {
    u128 sum = 0;
    for (u64 x : v) sum += (u128)x;
    return sum * (u128)v.size();
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    u64 n;
    if (!(cin >> n)) return 0;

    vector<u64> seqA = buildDoubling(n);
    vector<u64> seqB = buildPrimePairsSequence(n);

    u128 valA = sequenceValue(seqA);
    u128 valB = sequenceValue(seqB);

    const vector<u64>& best = (valB > valA ? seqB : seqA);

    cout << best.size() << "\n";
    for (size_t i = 0; i < best.size(); ++i) {
        if (i) cout << ' ';
        cout << best[i];
    }
    cout << "\n";
    return 0;
}