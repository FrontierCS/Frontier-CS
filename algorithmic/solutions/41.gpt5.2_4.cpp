#include <bits/stdc++.h>
using namespace std;

using int64 = long long;
using i128 = __int128_t;
using u128 = __uint128_t;

static vector<int> sievePrimes(int limit) {
    vector<bool> isPrime(limit + 1, true);
    isPrime[0] = isPrime[1] = false;
    for (int i = 2; 1LL * i * i <= limit; ++i) {
        if (!isPrime[i]) continue;
        for (long long j = 1LL * i * i; j <= limit; j += i) isPrime[(int)j] = false;
    }
    vector<int> primes;
    primes.reserve(limit / 10);
    for (int i = 2; i <= limit; ++i) if (isPrime[i]) primes.push_back(i);
    return primes;
}

static bool isValidBSU(const vector<int64>& a, int64 n) {
    int k = (int)a.size();
    if (k < 1 || k > 1000000) return false;
    for (int i = 0; i < k; ++i) {
        if (a[i] < 1 || a[i] > n) return false;
        if (i && a[i] <= a[i - 1]) return false;
    }
    if (k <= 2) return true;
    int64 prevg = std::gcd(a[1], a[0]);
    for (int i = 2; i < k; ++i) {
        int64 g = std::gcd(a[i], a[i - 1]);
        if (!(g > prevg)) return false;
        prevg = g;
    }
    return true;
}

static u128 computeV(const vector<int64>& a) {
    u128 sum = 0;
    for (int64 x : a) sum += (u128)x;
    return sum * (u128)a.size();
}

static vector<pair<int64,int>> factorize(int64 x, const vector<int>& primes) {
    vector<pair<int64,int>> f;
    for (int p : primes) {
        if (1LL * p * p > x) break;
        if (x % p == 0) {
            int cnt = 0;
            while (x % p == 0) {
                x /= p;
                ++cnt;
            }
            f.push_back({p, cnt});
        }
    }
    if (x > 1) f.push_back({x, 1});
    return f;
}

static void enumDivsRec(int idx, int64 cur, const vector<pair<int64,int>>& f, vector<int64>& divs) {
    if (idx == (int)f.size()) {
        divs.push_back(cur);
        return;
    }
    auto [p, e] = f[idx];
    int64 val = 1;
    for (int i = 0; i <= e; ++i) {
        enumDivsRec(idx + 1, cur * val, f, divs);
        if (i != e) val *= p;
    }
}

static int64 smallestDivisorGreaterThan(int64 x, int64 bound, const vector<int>& primes) {
    if (bound >= x) return -1;
    auto f = factorize(x, primes);
    vector<int64> divs;
    divs.reserve(2048);
    enumDivsRec(0, 1, f, divs);
    sort(divs.begin(), divs.end());
    auto it = upper_bound(divs.begin(), divs.end(), bound);
    if (it == divs.end()) return -1;
    return *it;
}

static void greedyExtend(vector<int64>& a, int64 n, const vector<int>& primes, int maxSteps = 2000) {
    int steps = 0;
    while ((int)a.size() < 1000000 && steps < maxSteps) {
        if ((int)a.size() < 2) break;
        int64 x = a.back();
        int64 prev = a[a.size() - 2];
        int64 gprev = std::gcd(x, prev);

        int64 d = smallestDivisorGreaterThan(x, gprev, primes);
        if (d <= 0) break;

        i128 y = (i128)x + (i128)d; // minimal possible next with gcd exactly d
        if (y > (i128)n) break;
        a.push_back((int64)y);

        ++steps;
    }
}

static void maximizeLast(vector<int64>& a, int64 n) {
    if (a.empty()) return;
    if ((int)a.size() == 1) {
        a[0] = min<int64>(a[0], n);
        return;
    }
    int64 prev = a[a.size() - 2];
    int64 g = std::gcd(a.back(), prev);
    if (g <= 0) return;
    int64 best = (n / g) * g;
    if (best > prev) a.back() = best;
}

static vector<int64> buildPow2(int64 n) {
    vector<int64> a;
    a.push_back(1);
    while ((int)a.size() < 1000000) {
        if (a.back() > n / 2) break;
        a.push_back(a.back() * 2);
    }
    return a;
}

static vector<int64> buildPrimeChain(int64 n, const vector<int>& primes) {
    vector<int64> a;
    a.push_back(1);
    if (n >= 2) a.push_back(2);

    for (int i = 0; i + 1 < (int)primes.size(); ++i) {
        i128 val = (i128)primes[i] * (i128)primes[i + 1];
        if (val > (i128)n) break;
        if (val > (i128)a.back()) a.push_back((int64)val);
        if ((int)a.size() >= 1000000) break;
    }

    greedyExtend(a, n, primes);
    maximizeLast(a, n);

    return a;
}

static vector<int64> buildBig2(int64 n) {
    if (n <= 1) return {1};
    return {n - 1, n};
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int64 n;
    cin >> n;

    const int SIEVE_LIMIT = 2000000;
    vector<int> primes = sievePrimes(SIEVE_LIMIT);

    vector<vector<int64>> candidates;
    candidates.reserve(4);

    candidates.push_back(buildPow2(n));
    candidates.push_back(buildPrimeChain(n, primes));
    candidates.push_back(buildBig2(n));

    vector<int64> best = {1};
    u128 bestV = 0;

    for (auto &cand : candidates) {
        if (!isValidBSU(cand, n)) continue;
        u128 v = computeV(cand);
        if (v > bestV) {
            bestV = v;
            best = cand;
        }
    }

    if (!isValidBSU(best, n)) best = {1};

    cout << best.size() << "\n";
    for (size_t i = 0; i < best.size(); ++i) {
        if (i) cout << ' ';
        cout << best[i];
    }
    cout << "\n";
    return 0;
}