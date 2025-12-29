#include <bits/stdc++.h>
using namespace std;

using u64 = unsigned long long;
using u128 = __uint128_t;
using i64 = long long;

static mt19937_64 rng((u64)chrono::high_resolution_clock::now().time_since_epoch().count() ^ (u64)random_device{}());

static i64 total_cost = 0;

static inline u64 rgcd(u64 a, u64 b) {
    while (b) {
        u64 t = a % b;
        a = b;
        b = t;
    }
    return a;
}

static inline u64 mod_mul(u64 a, u64 b, u64 mod) {
    return (u128)a * b % mod;
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

static u64 pollard_rho_f(u64 x, u64 c, u64 mod) {
    return (mod_mul(x, x, mod) + c) % mod;
}

static u64 pollard_rho(u64 n) {
    if ((n & 1ULL) == 0) return 2;
    if (n % 3ULL == 0) return 3;
    u64 c = uniform_int_distribution<u64>(1, n - 1)(rng);
    u64 x = uniform_int_distribution<u64>(0, n - 1)(rng);
    u64 y = x;
    u64 d = 1;
    while (d == 1) {
        x = pollard_rho_f(x, c, n);
        y = pollard_rho_f(pollard_rho_f(y, c, n), c, n);
        u64 diff = x > y ? x - y : y - x;
        d = rgcd(diff, n);
    }
    if (d == n) return pollard_rho(n);
    return d;
}

static void factor_rec(u64 n, vector<u64>& fac) {
    if (n == 1) return;
    if (isPrime(n)) {
        fac.push_back(n);
        return;
    }
    u64 d = pollard_rho(n);
    factor_rec(d, fac);
    factor_rec(n / d, fac);
}

static inline void append_u64(string& s, u64 x) {
    char buf[32];
    int n = 0;
    while (x) {
        buf[n++] = char('0' + (x % 10));
        x /= 10;
    }
    if (n == 0) buf[n++] = '0';
    while (n--) s.push_back(buf[n]);
}

static i64 read_i64() {
    i64 x;
    if (scanf("%lld", &x) != 1) exit(0);
    return x;
}

static i64 query_vec(const vector<u64>& v) {
    total_cost += (i64)v.size();
    string out;
    out.reserve(16 + v.size() * 22);
    out.push_back('0');
    out.push_back(' ');
    append_u64(out, (u64)v.size());
    for (u64 x : v) {
        out.push_back(' ');
        append_u64(out, x);
    }
    out.push_back('\n');
    fwrite(out.data(), 1, out.size(), stdout);
    fflush(stdout);
    return read_i64();
}

static i64 query2(u64 a, u64 b) {
    total_cost += 2;
    string out;
    out.reserve(80);
    out.append("0 2 ");
    append_u64(out, a);
    out.push_back(' ');
    append_u64(out, b);
    out.push_back('\n');
    fwrite(out.data(), 1, out.size(), stdout);
    fflush(stdout);
    return read_i64();
}

static bool congruent(u64 a, u64 b) {
    return query2(a, b) == 1;
}

static bool n_divides(u64 x) {
    // test if n | x by querying (1, 1+x)
    return query2(1, 1 + x) == 1;
}

static vector<u64> gen_random_distinct(int m) {
    static const u64 LIM = 1000000000000000000ULL;
    uniform_int_distribution<u64> dist(1, LIM);
    vector<u64> v;
    v.reserve(m + 32);
    while ((int)v.size() < m) v.push_back(dist(rng));
    sort(v.begin(), v.end());
    v.erase(unique(v.begin(), v.end()), v.end());
    while ((int)v.size() < m) {
        int need = m - (int)v.size();
        vector<u64> extra;
        extra.reserve(need + 32);
        for (int i = 0; i < need; i++) extra.push_back(dist(rng));
        v.insert(v.end(), extra.begin(), extra.end());
        sort(v.begin(), v.end());
        v.erase(unique(v.begin(), v.end()), v.end());
    }
    v.resize(m);
    return v;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    const int TARGET = 20;
    int m = 120000;

    vector<u64> cur;
    i64 ctot = 0;

    for (int tries = 0; tries < 6; tries++) {
        cur = gen_random_distinct(m);
        ctot = query_vec(cur);
        if (ctot > 0) break;
        m += 20000;
    }
    if (ctot == 0) {
        // Extremely unlikely; guess something to terminate.
        string out = "1 2\n";
        fwrite(out.data(), 1, out.size(), stdout);
        fflush(stdout);
        return 0;
    }

    while ((int)cur.size() > TARGET) {
        int n = (int)cur.size();
        int half = n / 2;
        bool ok = false;

        for (int attempt = 0; attempt < 40 && !ok; attempt++) {
            shuffle(cur.begin(), cur.end(), rng);

            vector<u64> A(cur.begin(), cur.begin() + half);
            i64 cA = query_vec(A);
            if (cA > 0) {
                cur.swap(A);
                ok = true;
                break;
            }

            vector<u64> B(cur.begin() + half, cur.end());
            i64 cB = query_vec(B);
            if (cB > 0) {
                cur.swap(B);
                ok = true;
                break;
            }
        }

        if (!ok) {
            // Fallback: restart with a new random set (rare)
            int mm = max(m, 140000);
            cur = gen_random_distinct(mm);
            ctot = query_vec(cur);
            if (ctot == 0) {
                string out = "1 2\n";
                fwrite(out.data(), 1, out.size(), stdout);
                fflush(stdout);
                return 0;
            }
        }
    }

    pair<u64, u64> ab = {0, 0};
    bool found = false;
    for (int i = 0; i < (int)cur.size() && !found; i++) {
        for (int j = i + 1; j < (int)cur.size(); j++) {
            if (congruent(cur[i], cur[j])) {
                ab = {cur[i], cur[j]};
                found = true;
                break;
            }
        }
    }

    if (!found) {
        // Should not happen if cur guaranteed to have collisions; restart minimal
        string out = "1 2\n";
        fwrite(out.data(), 1, out.size(), stdout);
        fflush(stdout);
        return 0;
    }

    u64 a = ab.first, b = ab.second;
    u64 D = a > b ? (a - b) : (b - a);

    vector<u64> fac;
    factor_rec(D, fac);
    sort(fac.begin(), fac.end());

    vector<pair<u64, int>> pf;
    for (u64 p : fac) {
        if (pf.empty() || pf.back().first != p) pf.push_back({p, 1});
        else pf.back().second++;
    }

    u64 cand = D;
    for (auto [p, e] : pf) {
        for (int t = 0; t < e; t++) {
            if (cand % p) break;
            u64 nxt = cand / p;
            if (nxt == 0) break;
            if (n_divides(nxt)) cand = nxt;
            else break;
        }
    }

    string out;
    out.reserve(32);
    out.push_back('1');
    out.push_back(' ');
    append_u64(out, cand);
    out.push_back('\n');
    fwrite(out.data(), 1, out.size(), stdout);
    fflush(stdout);
    return 0;
}