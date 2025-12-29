#include <bits/stdc++.h>
using namespace std;

static const long long MAXQ = 200000;
static const long long MAXX = 1000000000LL;

struct Interactor {
    long long q = 0;
    int cur = -1;

    int walkOnce(long long x) {
        if (x < 0) x = 0;
        if (x > MAXX) x = MAXX;
        cout << "walk " << x << "\n";
        cout.flush();
        int v;
        if (!(cin >> v)) exit(0);
        if (v == -1) exit(0);
        q++;
        cur = v;
        return v;
    }

    int walkSteps(long long steps) {
        while (steps > 0) {
            if (q >= MAXQ) exit(0);
            long long chunk = min(steps, MAXX);
            walkOnce(chunk);
            steps -= chunk;
        }
        return cur;
    }

    [[noreturn]] void guess(long long g) {
        cout << "guess " << g << "\n";
        cout.flush();
        exit(0);
    }
};

static vector<long long> factorUnique(long long n) {
    vector<long long> ps;
    if (n <= 1) return ps;
    if (n % 2 == 0) {
        ps.push_back(2);
        while (n % 2 == 0) n /= 2;
    }
    for (long long p = 3; p * p <= n; p += 2) {
        if (n % p == 0) {
            ps.push_back(p);
            while (n % p == 0) n /= p;
        }
    }
    if (n > 1) ps.push_back(n);
    return ps;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    Interactor it;

    // Get starting label
    it.walkOnce(0);

    unordered_map<int, long long> seen;
    seen.reserve(400000);
    seen.max_load_factor(0.7f);

    long long T = 0;
    seen[it.cur] = 0;

    mt19937_64 rng((uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count() ^ (uint64_t)(uintptr_t)&rng);

    const long long STEP_MAX = 10000000LL;
    const long long SAFE = 35000; // reserve queries for reduction

    long long M = 0;

    while (it.q < MAXQ - SAFE && M == 0) {
        long long x = (long long)(rng() % STEP_MAX) + 1;
        it.walkOnce(x);
        T += x;

        auto f = seen.find(it.cur);
        if (f != seen.end()) {
            M = T - f->second;
            break;
        }
        seen[it.cur] = T;
    }

    if (M == 0) {
        // last-ditch: continue a bit more (may reduce remaining budget but likely unnecessary)
        while (it.q < MAXQ - 1 && M == 0) {
            long long x = (long long)(rng() % STEP_MAX) + 1;
            it.walkOnce(x);
            T += x;

            auto f = seen.find(it.cur);
            if (f != seen.end()) {
                M = T - f->second;
                break;
            }
            seen[it.cur] = T;
        }
    }

    if (M == 0) {
        it.guess(1);
    }

    // Reduce M to the minimal positive multiple of n (which is n) by testing prime divisions.
    vector<long long> primes = factorUnique(M);
    sort(primes.rbegin(), primes.rend());

    for (long long p : primes) {
        while (M % p == 0) {
            long long cand = M / p;
            int start = it.cur;
            it.walkSteps(cand);
            if (it.cur == start) {
                M = cand;
            } else {
                break;
            }
        }
    }

    it.guess(M);
}