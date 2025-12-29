#include <bits/stdc++.h>
using namespace std;

static const int MAX_WALKS = 200000;
static const int LIM = 1000000000;

struct CustomHash {
    static uint64_t splitmix64(uint64_t x) {
        x += 0x9e3779b97f4a7c15ULL;
        x = (x ^ (x >> 30)) * 0xbf58476d1ce4e5b9ULL;
        x = (x ^ (x >> 27)) * 0x94d049bb133111ebULL;
        return x ^ (x >> 31);
    }
    size_t operator()(uint64_t x) const {
        static const uint64_t FIXED_RANDOM = chrono::steady_clock::now().time_since_epoch().count();
        return (size_t)splitmix64(x + FIXED_RANDOM);
    }
};

static long long walkCount = 0;
static int curLabel = -1;

static int Walk(long long x) {
    if (x < 0) x = 0;
    if (x > LIM) x = LIM; // should not happen in this strategy
    cout << "walk " << x << '\n' << flush;
    ++walkCount;
    int v;
    if (!(cin >> v)) exit(0);
    curLabel = v;
    return v;
}

static void Guess(long long g) {
    cout << "guess " << g << '\n' << flush;
    exit(0);
}

// Tests if cand is a multiple of n, given that base is a known multiple of n.
// Leaves the token at the original vertex.
static bool TestMultiple(long long cand, long long base) {
    int before = curLabel;
    Walk(cand);
    int after = curLabel;
    if (after == before) return true;
    Walk(base - cand); // return to start since base is a multiple of n
    return false;
}

static vector<long long> distinctPrimeFactors(long long x) {
    vector<long long> ps;
    for (long long p = 2; p * p <= x; p += (p == 2 ? 1 : 2)) {
        if (x % p == 0) {
            ps.push_back(p);
            while (x % p == 0) x /= p;
        }
    }
    if (x > 1) ps.push_back(x);
    return ps;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    Walk(0);

    unordered_map<int, int, CustomHash> seen;
    seen.reserve(1 << 19);
    seen.max_load_factor(0.7f);
    seen[curLabel] = 0;

    const int SAMPLE = 195000; // includes the initial walk(0) already done; we'll do SAMPLE-1 more target points
    mt19937_64 rng((uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count());
    uniform_int_distribution<int> dist(1, LIM);

    vector<int> targets;
    targets.reserve(SAMPLE - 1);
    for (int i = 0; i < SAMPLE - 1; i++) targets.push_back(dist(rng));
    sort(targets.begin(), targets.end());
    targets.erase(unique(targets.begin(), targets.end()), targets.end());

    long long curT = 0;
    long long multiple = -1;

    for (int t : targets) {
        if (walkCount >= MAX_WALKS - 200) break;
        long long step = (long long)t - curT;
        if (step < 0) continue;
        Walk(step);
        curT = t;

        auto it = seen.find(curLabel);
        if (it != seen.end()) {
            multiple = curT - it->second;
            break;
        }
        seen[curLabel] = (int)curT;
    }

    if (multiple <= 0) {
        // Extremely unlikely with chosen SAMPLE; last resort (may fail if still no collision).
        // Try a few more random points.
        while (walkCount < MAX_WALKS - 200 && multiple <= 0 && curT < LIM) {
            int t = dist(rng);
            if (t <= (int)curT) continue;
            Walk(t - curT);
            curT = t;
            auto it = seen.find(curLabel);
            if (it != seen.end()) {
                multiple = curT - it->second;
                break;
            }
            seen[curLabel] = (int)curT;
        }
        if (multiple <= 0) Guess(1); // fallback guess
    }

    long long ans = multiple;
    auto primes = distinctPrimeFactors(ans);

    for (long long p : primes) {
        while (ans % p == 0) {
            long long cand = ans / p;
            if (TestMultiple(cand, ans)) {
                ans = cand;
            } else {
                break;
            }
        }
    }

    Guess(ans);
    return 0;
}