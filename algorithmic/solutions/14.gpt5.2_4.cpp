#include <bits/stdc++.h>
using namespace std;

static const int MAX_WALKS = 200000;
static const long long LIM_STEP = 1000000000LL;

struct Interactor {
    int walks = 0;

    int walk_once(long long x) {
        if (x < 0) x = 0;
        if (x > LIM_STEP) x = LIM_STEP;
        if (walks >= MAX_WALKS) exit(0);
        cout << "walk " << x << "\n" << flush;
        int v;
        if (!(cin >> v)) exit(0);
        if (v == -1) exit(0);
        walks++;
        return v;
    }

    int walk_long(long long x, int curLabel) {
        while (x > 0) {
            long long step = min(LIM_STEP, x);
            curLabel = walk_once(step);
            x -= step;
        }
        return curLabel;
    }

    [[noreturn]] void guess(long long g) {
        if (g < 1) g = 1;
        if (g > 1000000000LL) g = 1000000000LL;
        cout << "guess " << g << "\n" << flush;
        exit(0);
    }
};

static vector<pair<long long,int>> factorize_trial(long long n) {
    vector<pair<long long,int>> f;
    if (n <= 1) return f;
    int c = 0;
    while ((n & 1LL) == 0) { n >>= 1; c++; }
    if (c) f.push_back({2, c});
    for (long long p = 3; p * p <= n; p += 2) {
        if (n % p == 0) {
            int e = 0;
            while (n % p == 0) { n /= p; e++; }
            f.push_back({p, e});
        }
    }
    if (n > 1) f.push_back({n, 1});
    return f;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    Interactor it;

    // Get starting label
    int cur = it.walk_once(0);

    mt19937_64 rng((uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count());
    uniform_int_distribution<long long> dist(1, LIM_STEP);

    unordered_map<int, long long> seen;
    seen.reserve(300000);
    seen.max_load_factor(0.7f);

    long long steps = 0;
    seen[cur] = 0;

    long long M = 0;
    int collisions = 0;
    int stable = 0;

    const int RANDOM_MAX = 110000;

    while (it.walks < MAX_WALKS - 1) {
        if (M != 0) {
            // If M is already <= 1e9, we can cheaply finish; if we have at least 2 collisions, good confidence.
            if (M <= 1000000000LL && collisions >= 2 && stable >= 2) break;
            if (collisions >= 6 && stable >= 3) break;
        }

        if (it.walks >= RANDOM_MAX && M != 0 && collisions >= 1) break;
        if (it.walks >= RANDOM_MAX && M == 0 && it.walks >= MAX_WALKS - 5000) break;

        long long x = dist(rng);
        cur = it.walk_once(x);
        steps += x;

        auto itSeen = seen.find(cur);
        if (itSeen != seen.end()) {
            long long diff = steps - itSeen->second;
            long long newM = (M == 0) ? diff : std::gcd(M, diff);
            if (newM == M) stable++;
            else { M = newM; stable = 0; }
            collisions++;
            itSeen->second = steps;
            if (M == 1) break;
        } else {
            seen.emplace(cur, steps);
        }
    }

    // If still no multiple found, continue a bit more (rare).
    while (M == 0 && it.walks < MAX_WALKS - 1) {
        long long x = dist(rng);
        cur = it.walk_once(x);
        steps += x;
        auto itSeen = seen.find(cur);
        if (itSeen != seen.end()) {
            M = steps - itSeen->second;
            break;
        }
        seen.emplace(cur, steps);
    }

    if (M == 0) {
        it.guess(1);
    }

    // Minimize M to the true cycle length by dividing prime factors while preserving periodicity.
    auto fac = factorize_trial(M);
    for (auto [p, e] : fac) {
        for (int i = 0; i < e; i++) {
            if (M % p != 0) break;
            long long cand = M / p;
            if (cand <= 0) break;

            int before = cur;
            cur = it.walk_long(cand, cur);
            if (cur == before) {
                M = cand;
                if (M == 1) break;
            } else {
                break;
            }
        }
        if (M == 1) break;
    }

    it.guess(M);
}