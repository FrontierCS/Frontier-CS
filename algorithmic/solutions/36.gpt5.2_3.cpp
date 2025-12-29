#include <bits/stdc++.h>
using namespace std;

using ull = unsigned long long;
using u128 = __uint128_t;

static const ull LIM = 1000000000000000000ULL;

static uint64_t splitmix64(uint64_t x) {
    x += 0x9e3779b97f4a7c15ULL;
    x = (x ^ (x >> 30)) * 0xbf58476d1ce4e5b9ULL;
    x = (x ^ (x >> 27)) * 0x94d049bb133111ebULL;
    return x ^ (x >> 31);
}

struct Interactor {
    long long cost = 0;
    static constexpr long long MAXCOST = 1000000;

    long long ask(const vector<ull>& v) {
        if (v.empty()) return 0;
        if (cost + (long long)v.size() > MAXCOST) {
            // Should never happen with our budgeting; exit to avoid invalid protocol.
            exit(0);
        }
        cout << "0 " << v.size();
        for (ull x : v) cout << " " << x;
        cout << "\n";
        cout.flush();

        long long res;
        if (!(cin >> res)) exit(0);
        if (res < 0) exit(0);
        cost += (long long)v.size();
        return res;
    }

    [[noreturn]] void guess(uint32_t n) {
        cout << "1 " << n << "\n";
        cout.flush();
        exit(0);
    }
};

struct FastCollisions {
    static constexpr uint32_t EMPTY = 0xFFFFFFFFu;
    uint32_t mask;
    vector<uint32_t> key;
    vector<uint32_t> val;
    vector<uint32_t> used;

    explicit FastCollisions(int capPow2 = (1 << 19)) {
        key.assign(capPow2, EMPTY);
        val.assign(capPow2, 0);
        mask = (uint32_t)(capPow2 - 1);
        used.reserve(70000);
    }

    static inline uint64_t h32(uint32_t x) { return splitmix64((uint64_t)x); }

    long long compute(const vector<ull>& v, uint32_t mod) {
        used.clear();
        long long col = 0;
        for (ull x : v) {
            uint32_t r = (uint32_t)(x % mod);
            uint32_t idx = (uint32_t)(h32(r) & mask);
            while (true) {
                uint32_t k = key[idx];
                if (k == EMPTY) {
                    key[idx] = r;
                    val[idx] = 1;
                    used.push_back(idx);
                    break;
                }
                if (k == r) {
                    col += (long long)val[idx];
                    val[idx]++;
                    break;
                }
                idx = (idx + 1) & mask;
            }
        }
        for (uint32_t idx : used) key[idx] = EMPTY;
        return col;
    }
};

// ---- 64-bit Miller-Rabin + Pollard Rho ----

static ull mod_mul(ull a, ull b, ull mod) {
    return (ull)((u128)a * b % mod);
}
static ull mod_pow(ull a, ull d, ull mod) {
    ull r = 1;
    while (d) {
        if (d & 1) r = mod_mul(r, a, mod);
        a = mod_mul(a, a, mod);
        d >>= 1;
    }
    return r;
}

static bool isPrime64(ull n) {
    if (n < 2) return false;
    for (ull p : {2ULL, 3ULL, 5ULL, 7ULL, 11ULL, 13ULL, 17ULL, 19ULL, 23ULL, 29ULL, 31ULL, 37ULL}) {
        if (n % p == 0) return n == p;
    }
    ull d = n - 1, s = 0;
    while ((d & 1) == 0) d >>= 1, ++s;

    auto witness = [&](ull a) -> bool {
        if (a % n == 0) return false;
        ull x = mod_pow(a, d, n);
        if (x == 1 || x == n - 1) return false;
        for (ull i = 1; i < s; i++) {
            x = mod_mul(x, x, n);
            if (x == n - 1) return false;
        }
        return true;
    };

    // Deterministic bases for 64-bit
    for (ull a : {2ULL, 325ULL, 9375ULL, 28178ULL, 450775ULL, 9780504ULL, 1795265022ULL}) {
        if (witness(a)) return false;
    }
    return true;
}

static ull pollard_f(ull x, ull c, ull mod) {
    return (mod_mul(x, x, mod) + c) % mod;
}

static ull pollard_rho(ull n, std::mt19937_64& rng) {
    if (n % 2ULL == 0) return 2;
    if (n % 3ULL == 0) return 3;

    uniform_int_distribution<ull> dist(2ULL, n - 2);
    while (true) {
        ull c = dist(rng);
        ull x = dist(rng);
        ull y = x;
        ull d = 1;

        while (d == 1) {
            x = pollard_f(x, c, n);
            y = pollard_f(pollard_f(y, c, n), c, n);
            ull diff = (x > y) ? (x - y) : (y - x);
            d = std::gcd(diff, n);
        }
        if (d != n) return d;
    }
}

static void factor_rec(ull n, map<ull, int>& mp, std::mt19937_64& rng) {
    if (n == 1) return;
    if (isPrime64(n)) {
        mp[n]++;
        return;
    }
    ull d = pollard_rho(n, rng);
    factor_rec(d, mp, rng);
    factor_rec(n / d, mp, rng);
}

static vector<uint32_t> divisors_upto_1e9(ull n, std::mt19937_64& rng) {
    map<ull, int> mp;
    factor_rec(n, mp, rng);
    vector<pair<ull, int>> pf(mp.begin(), mp.end());

    vector<uint32_t> divs;
    function<void(int, ull)> dfs = [&](int i, ull cur) {
        if (cur > 1000000000ULL) return;
        if (i == (int)pf.size()) {
            if (cur >= 2) divs.push_back((uint32_t)cur);
            return;
        }
        ull p = pf[i].first;
        int e = pf[i].second;
        ull v = 1;
        for (int k = 0; k <= e; k++) {
            if (cur > 1000000000ULL / v) break;
            dfs(i + 1, cur * v);
            if (k < e) v *= p;
        }
    };
    dfs(0, 1);

    sort(divs.begin(), divs.end());
    divs.erase(unique(divs.begin(), divs.end()), divs.end());
    return divs;
}

// ---- random distinct generation ----

static vector<ull> genDistinct(int n, std::mt19937_64& rng) {
    vector<ull> v;
    v.reserve(n);
    unordered_set<ull> seen;
    seen.reserve((size_t)n * 2);

    while ((int)v.size() < n) {
        ull x = (ull)(rng() % LIM) + 1ULL;
        if (seen.insert(x).second) v.push_back(x);
    }
    return v;
}

static bool removeValue(vector<ull>& v, ull x) {
    for (size_t i = 0; i < v.size(); i++) {
        if (v[i] == x) {
            v[i] = v.back();
            v.pop_back();
            return true;
        }
    }
    return false;
}

struct Solver {
    Interactor it;
    std::mt19937_64 rng;
    FastCollisions fc;

    Solver() : rng((ull)chrono::high_resolution_clock::now().time_since_epoch().count()), fc(1 << 19) {}

    pair<ull, ull> findPairFromSetWithCollision(const vector<ull>& base) {
        vector<ull> V = base;

        while (V.size() > 2) {
            bool progressed = false;
            for (int tries = 0; tries < 12 && !progressed; tries++) {
                shuffle(V.begin(), V.end(), rng);
                size_t mid = V.size() / 2;

                vector<ull> A;
                vector<ull> B;
                A.reserve(mid);
                B.reserve(V.size() - mid);
                A.insert(A.end(), V.begin(), V.begin() + (ptrdiff_t)mid);
                B.insert(B.end(), V.begin() + (ptrdiff_t)mid, V.end());

                long long cA = it.ask(A);
                if (cA > 0) {
                    V.swap(A);
                    progressed = true;
                    break;
                }
                long long cB = it.ask(B);
                if (cB > 0) {
                    V.swap(B);
                    progressed = true;
                    break;
                }
            }

            if (!progressed) {
                // If V is already small, brute force by pair queries.
                if (V.size() <= 200) {
                    for (size_t i = 0; i < V.size(); i++) {
                        for (size_t j = i + 1; j < V.size(); j++) {
                            vector<ull> q = {V[i], V[j]};
                            long long c = it.ask(q);
                            if (c > 0) return {V[i], V[j]};
                        }
                    }
                    // Should not happen if base truly had collision.
                    return {V[0], V[1]};
                }
                // Otherwise, keep trying (rare).
            }
        }
        return {V[0], V[1]};
    }

    vector<uint32_t> filterCandidates(const vector<uint32_t>& cand, const vector<ull>& v, long long target) {
        vector<uint32_t> out;
        out.reserve(cand.size());
        for (uint32_t d : cand) {
            if (fc.compute(v, d) == target) out.push_back(d);
        }
        return out;
    }

    void run() {
        const int poolSize = 240000;
        const int valSize = 60000;
        const int groupSize = 20000;
        const int targetDiffs = 8;

        vector<ull> pool = genDistinct(poolSize, rng);

        vector<ull> A(pool.begin(), pool.begin() + valSize);
        vector<ull> B(pool.begin() + valSize, pool.begin() + 2 * valSize);

        long long CA = it.ask(A);
        long long CB = it.ask(B);

        ull G = 0;
        int got = 0;

        // Extract differences from groups
        for (int start = 0; start < poolSize && got < targetDiffs; start += groupSize) {
            int end = min(poolSize, start + groupSize);
            vector<ull> W(pool.begin() + start, pool.begin() + end);

            // Try to extract multiple pairs from the same group by removing found elements.
            for (int rounds = 0; rounds < 3 && got < targetDiffs; rounds++) {
                if ((int)W.size() < 2) break;
                if (it.cost + (long long)W.size() > Interactor::MAXCOST) break;

                long long cW = it.ask(W);
                if (cW == 0) break;

                // If too close to cost limit, stop extracting.
                if (it.cost + (long long)W.size() * 2 > Interactor::MAXCOST) break;

                auto pr = findPairFromSetWithCollision(W);
                ull d = (pr.first > pr.second) ? (pr.first - pr.second) : (pr.second - pr.first);
                if (d == 0) continue;

                G = (G == 0) ? d : std::gcd(G, d);
                got++;

                removeValue(W, pr.first);
                removeValue(W, pr.second);
            }
        }

        // If somehow we couldn't get any difference, try a last resort: larger random set
        if (G == 0) {
            vector<ull> T = genDistinct(80000, rng);
            long long cT = it.ask(T);
            if (cT == 0) it.guess(2);
            auto pr = findPairFromSetWithCollision(T);
            ull d = (pr.first > pr.second) ? (pr.first - pr.second) : (pr.second - pr.first);
            if (d == 0) it.guess(2);
            G = d;
        }

        vector<uint32_t> candidates = divisors_upto_1e9(G, rng);

        candidates = filterCandidates(candidates, A, CA);
        candidates = filterCandidates(candidates, B, CB);

        // Additional validation queries if needed
        for (int extra = 0; extra < 4 && candidates.size() > 1; extra++) {
            if (it.cost + valSize > Interactor::MAXCOST) break;
            vector<ull> C = genDistinct(valSize, rng);
            long long CC = it.ask(C);
            candidates = filterCandidates(candidates, C, CC);
        }

        if (candidates.empty()) {
            // Try to refine G with a bit more data if budget allows
            for (int rep = 0; rep < 2 && it.cost + groupSize <= Interactor::MAXCOST; rep++) {
                vector<ull> W = genDistinct(groupSize, rng);
                long long cW = it.ask(W);
                if (cW == 0) continue;
                auto pr = findPairFromSetWithCollision(W);
                ull d = (pr.first > pr.second) ? (pr.first - pr.second) : (pr.second - pr.first);
                if (d == 0) continue;
                G = std::gcd(G, d);
                candidates = divisors_upto_1e9(G, rng);
                candidates = filterCandidates(candidates, A, CA);
                candidates = filterCandidates(candidates, B, CB);
                if (!candidates.empty()) break;
            }
        }

        if (candidates.empty()) {
            // Fallback (shouldn't happen)
            it.guess(2);
        }

        // If still multiple, pick the only one left after additional constraints; otherwise, pick smallest.
        uint32_t ans = *min_element(candidates.begin(), candidates.end());
        if (candidates.size() == 1) ans = candidates[0];

        it.guess(ans);
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    Solver s;
    s.run();
    return 0;
}