#include <bits/stdc++.h>
using namespace std;

using u64 = unsigned long long;
using u128 = __uint128_t;

static const u64 LIM = 1000000000000000000ULL;
static const u64 COST_LIMIT = 1000000ULL;

struct SplitMix64 {
    u64 x;
    explicit SplitMix64(u64 seed = 0) : x(seed) {}
    u64 next() {
        u64 z = (x += 0x9e3779b97f4a7c15ULL);
        z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
        z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
        return z ^ (z >> 31);
    }
};

static SplitMix64 rng((u64)chrono::high_resolution_clock::now().time_since_epoch().count());

static u64 totalCost = 0;

static vector<u64> baseVals;
static unordered_map<u64, u64> memo;

static inline u64 keyLR(int l, int r) {
    return (u64)((u64)(uint32_t)l << 32) | (u64)(uint32_t)r;
}

static void ensureBudget(u64 add) {
    if (totalCost + add > COST_LIMIT) {
        // Emergency exit with a guess; should not happen with chosen parameters.
        cout << "1 2\n";
        cout.flush();
        exit(0);
    }
}

static u64 askInterval(int l, int r) {
    int m = r - l;
    ensureBudget(m);
    cout << "0 " << m;
    for (int i = l; i < r; i++) cout << ' ' << baseVals[i];
    cout << "\n";
    cout.flush();
    u64 res;
    if (!(cin >> res)) exit(0);
    totalCost += (u64)m;
    return res;
}

static u64 getColl(int l, int r) {
    u64 k = keyLR(l, r);
    auto it = memo.find(k);
    if (it != memo.end()) return it->second;
    u64 res = askInterval(l, r);
    memo.emplace(k, res);
    return res;
}

static u64 askUnion(int l1, int r1, int l2, int r2) {
    int m = (r1 - l1) + (r2 - l2);
    ensureBudget(m);
    cout << "0 " << m;
    for (int i = l1; i < r1; i++) cout << ' ' << baseVals[i];
    for (int i = l2; i < r2; i++) cout << ' ' << baseVals[i];
    cout << "\n";
    cout.flush();
    u64 res;
    if (!(cin >> res)) exit(0);
    totalCost += (u64)m;
    return res;
}

static u64 askPair(u64 x, u64 y) {
    ensureBudget(2);
    cout << "0 2 " << x << ' ' << y << "\n";
    cout.flush();
    u64 res;
    if (!(cin >> res)) exit(0);
    totalCost += 2;
    return res;
}

static pair<u64, u64> crossRec(int l1, int r1, int l2, int r2) {
    // Assumes:
    // - No internal collisions within [l1,r1) and [l2,r2)
    // - There exists at least one cross collision between them
    int n1 = r1 - l1, n2 = r2 - l2;
    if (n1 == 1 && n2 == 1) return {baseVals[l1], baseVals[l2]};
    if (n1 >= n2) {
        if (n1 == 1) {
            int mid = (l2 + r2) / 2;
            u64 c = askUnion(l1, r1, l2, mid);
            if (c > 0) return crossRec(l1, r1, l2, mid);
            return crossRec(l1, r1, mid, r2);
        }
        int mid = (l1 + r1) / 2;
        u64 c = askUnion(l1, mid, l2, r2);
        if (c > 0) return crossRec(l1, mid, l2, r2);
        return crossRec(mid, r1, l2, r2);
    } else {
        if (n2 == 1) {
            int mid = (l1 + r1) / 2;
            u64 c = askUnion(l1, mid, l2, r2);
            if (c > 0) return crossRec(l1, mid, l2, r2);
            return crossRec(mid, r1, l2, r2);
        }
        int mid = (l2 + r2) / 2;
        u64 c = askUnion(l1, r1, l2, mid);
        if (c > 0) return crossRec(l1, r1, l2, mid);
        return crossRec(l1, r1, mid, r2);
    }
}

static pair<u64, u64> withinRec(int l, int r, u64 coll) {
    int n = r - l;
    if (n == 2) return {baseVals[l], baseVals[l + 1]};
    int mid = (l + r) / 2;
    u64 cL = getColl(l, mid);
    if (cL > 0) return withinRec(l, mid, cL);
    u64 cR = getColl(mid, r);
    if (cR > 0) return withinRec(mid, r, cR);
    // Cross case: both sides collision-free and coll>0 implies cross collision exists
    return crossRec(l, mid, mid, r);
}

// ---- Pollard Rho ----

static inline u64 gcd_u64(u64 a, u64 b) {
    while (b) {
        u64 t = a % b;
        a = b;
        b = t;
    }
    return a;
}

static inline u64 mod_mul(u64 a, u64 b, u64 mod) {
    return (u64)((u128)a * b % mod);
}

static inline u64 mod_pow(u64 a, u64 e, u64 mod) {
    u64 r = 1 % mod;
    while (e) {
        if (e & 1) r = mod_mul(r, a, mod);
        a = mod_mul(a, a, mod);
        e >>= 1;
    }
    return r;
}

static bool isPrime(u64 n) {
    if (n < 2) return false;
    for (u64 p : {2ULL, 3ULL, 5ULL, 7ULL, 11ULL, 13ULL, 17ULL, 19ULL, 23ULL, 29ULL, 31ULL, 37ULL}) {
        if (n % p == 0) return n == p;
    }
    u64 d = n - 1, s = 0;
    while ((d & 1) == 0) d >>= 1, ++s;

    auto witness = [&](u64 a) -> bool {
        if (a % n == 0) return false;
        u64 x = mod_pow(a, d, n);
        if (x == 1 || x == n - 1) return false;
        for (u64 i = 1; i < s; i++) {
            x = mod_mul(x, x, n);
            if (x == n - 1) return false;
        }
        return true;
    };

    // Deterministic for 64-bit
    for (u64 a : {2ULL, 325ULL, 9375ULL, 28178ULL, 450775ULL, 9780504ULL, 1795265022ULL}) {
        if (witness(a)) return false;
    }
    return true;
}

static u64 pollard_rho(u64 n) {
    if ((n & 1ULL) == 0) return 2;
    if (n % 3ULL == 0) return 3;
    u64 c = rng.next() % (n - 1) + 1;
    u64 x = rng.next() % n;
    u64 y = x;
    u64 d = 1;

    auto f = [&](u64 v) -> u64 {
        return (mod_mul(v, v, n) + c) % n;
    };

    while (d == 1) {
        x = f(x);
        y = f(f(y));
        u64 diff = (x > y) ? (x - y) : (y - x);
        d = gcd_u64(diff, n);
    }
    if (d == n) return pollard_rho(n);
    return d;
}

static void factorRec(u64 n, vector<u64>& fac) {
    if (n == 1) return;
    if (isPrime(n)) {
        fac.push_back(n);
        return;
    }
    u64 d = pollard_rho(n);
    factorRec(d, fac);
    factorRec(n / d, fac);
}

static bool divisibleByN(u64 d) {
    if (d == 0) return true;
    u64 a = 1;
    if (a + d > LIM) a = LIM - d;
    if (a < 1) a = 1;
    return askPair(a, a + d) == 1;
}

static u64 recoverNFromMultiple(u64 D) {
    vector<u64> fac;
    factorRec(D, fac);
    sort(fac.begin(), fac.end());
    fac.erase(unique(fac.begin(), fac.end()), fac.end());

    u64 g = D;
    for (u64 p : fac) {
        while (g % p == 0) {
            u64 cand = g / p;
            if (cand == 0) break;
            if (divisibleByN(cand)) g = cand;
            else break;
        }
    }
    return g;
}

static void genDistinctRandom(int M) {
    baseVals.clear();
    baseVals.reserve(M);
    unordered_set<u64> seen;
    seen.reserve((size_t)M * 2);

    while ((int)baseVals.size() < M) {
        u64 x = (rng.next() % LIM) + 1;
        if (seen.insert(x).second) baseVals.push_back(x);
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    u64 answer = 0;
    const int M = 110000;

    for (int outer = 0; outer < 5 && answer == 0; outer++) {
        for (int attempt = 0; attempt < 3 && answer == 0; attempt++) {
            memo.clear();
            genDistinctRandom(M);

            u64 total = getColl(0, M);
            if (total == 0) continue;

            auto pr = withinRec(0, M, total);
            if (askPair(pr.first, pr.second) != 1) continue;

            u64 D = (pr.first > pr.second) ? (pr.first - pr.second) : (pr.second - pr.first);
            if (D == 0) continue;

            answer = recoverNFromMultiple(D);
            if (answer < 2 || answer > 1000000000ULL) answer = 0;
        }
    }

    if (answer == 0) answer = 2; // should never happen

    cout << "1 " << answer << "\n";
    cout.flush();
    return 0;
}