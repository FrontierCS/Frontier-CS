#include <bits/stdc++.h>
using namespace std;

using u64 = unsigned long long;
using u128 = __uint128_t;
using i64 = long long;

static mt19937_64 rng(chrono::steady_clock::now().time_since_epoch().count());

const u64 MAXV = 1000000000000000000ULL; // 1e18
const int M = 300000; // size of the random set

vector<u64> arr;

inline i64 ask_values(const vector<u64>& vals) {
    cout << "0 " << vals.size();
    for (u64 v : vals) cout << " " << v;
    cout << '\n' << flush;
    i64 res;
    if (!(cin >> res)) exit(0);
    return res;
}

inline i64 ask_indices(const vector<int>& ids) {
    cout << "0 " << ids.size();
    for (int id : ids) cout << " " << arr[id];
    cout << '\n' << flush;
    i64 res;
    if (!(cin >> res)) exit(0);
    return res;
}

inline i64 ask_pair(u64 a, u64 b) {
    cout << "0 2 " << a << " " << b << '\n' << flush;
    i64 res;
    if (!(cin >> res)) exit(0);
    return res;
}

inline bool test_divides(u64 d) {
    if (d == 0) return true;
    return ask_pair(1, 1 + d) == 1;
}

// Miller-Rabin and Pollard's Rho for 64-bit
u64 mul_mod(u64 a, u64 b, u64 mod) {
    return (u128)a * b % mod;
}

u64 pow_mod(u64 a, u64 d, u64 mod) {
    u64 r = 1;
    while (d) {
        if (d & 1) r = mul_mod(r, a, mod);
        a = mul_mod(a, a, mod);
        d >>= 1;
    }
    return r;
}

bool isPrime(u64 n) {
    if (n < 2) return false;
    static u64 testPrimes[] = {2ULL, 3ULL, 5ULL, 7ULL, 11ULL, 13ULL, 17ULL, 19ULL, 23ULL, 29ULL, 31ULL, 37ULL};
    for (u64 p : testPrimes) {
        if (n % p == 0) return n == p;
    }
    u64 d = n - 1, s = 0;
    while ((d & 1) == 0) { d >>= 1; ++s; }
    auto check = [&](u64 a) -> bool {
        if (a % n == 0) return true;
        u64 x = pow_mod(a, d, n);
        if (x == 1 || x == n - 1) return true;
        for (u64 r = 1; r < s; ++r) {
            x = mul_mod(x, x, n);
            if (x == n - 1) return true;
        }
        return false;
    };
    u64 bases[] = {2ULL, 3ULL, 5ULL, 7ULL, 11ULL, 13ULL};
    for (u64 a : bases) {
        if (a == 0) continue;
        if (!check(a)) return false;
    }
    return true;
}

u64 pollard(u64 n) {
    if ((n & 1ULL) == 0) return 2;
    if (n % 3ULL == 0) return 3;
    uniform_int_distribution<u64> dist(2, n - 2);
    while (true) {
        u64 c = dist(rng);
        u64 x = dist(rng);
        u64 y = x;
        u64 d = 1;
        auto f = [&](u64 v) -> u64 { return (mul_mod(v, v, n) + c) % n; };
        while (d == 1) {
            x = f(x);
            y = f(f(y));
            u64 diff = x > y ? x - y : y - x;
            d = std::gcd(diff, n);
        }
        if (d != n) return d;
    }
}

void factor(u64 n, vector<u64>& fac) {
    if (n == 1) return;
    if (isPrime(n)) {
        fac.push_back(n);
        return;
    }
    u64 d = pollard(n);
    factor(d, fac);
    factor(n / d, fac);
}

pair<int,int> find_pair_with_collision(const vector<int>& initial_ids, i64 initial_c) {
    vector<int> cur = initial_ids;
    i64 cur_c = initial_c;
    while (cur.size() > 2) {
        vector<int> A, B;
        A.reserve(cur.size() / 2 + 1);
        B.reserve(cur.size() / 2 + 1);
        // random split ensuring both non-empty
        for (int id : cur) {
            if (rng() & 1) A.push_back(id);
            else B.push_back(id);
        }
        if (A.empty() || B.empty()) {
            // re-split
            A.clear(); B.clear();
            for (int i = 0; i < (int)cur.size(); ++i) {
                if (i < (int)cur.size() / 2) A.push_back(cur[i]); else B.push_back(cur[i]);
            }
        }
        i64 cA = ask_indices(A);
        if (cA > 0) {
            cur.swap(A);
            cur_c = cA;
            continue;
        }
        i64 cB = ask_indices(B);
        if (cB > 0) {
            cur.swap(B);
            cur_c = cB;
            continue;
        }
        // both zero: resplit randomly and try again
        // Incredibly unlikely if cur_c > 0, but handle anyway
        // We'll try a few times
        int tries = 0;
        bool moved = false;
        while (tries < 5 && !moved) {
            ++tries;
            A.clear(); B.clear();
            for (int id : cur) {
                if (rng() & 1) A.push_back(id);
                else B.push_back(id);
            }
            if (A.empty() || B.empty()) continue;
            cA = ask_indices(A);
            if (cA > 0) {
                cur.swap(A); cur_c = cA; moved = true; break;
            }
            cB = ask_indices(B);
            if (cB > 0) {
                cur.swap(B); cur_c = cB; moved = true; break;
            }
        }
        if (!moved) {
            // fallback deterministic split
            A.clear(); B.clear();
            for (int i = 0; i < (int)cur.size(); ++i) {
                if (i % 2 == 0) A.push_back(cur[i]);
                else B.push_back(cur[i]);
            }
            cA = ask_indices(A);
            if (cA > 0) { cur.swap(A); cur_c = cA; continue; }
            cB = ask_indices(B);
            if (cB > 0) { cur.swap(B); cur_c = cB; continue; }
            // If still stuck, break to avoid infinite loop
            break;
        }
    }
    // Now size should be 2
    if (cur.size() > 2) {
        // Try to shrink deterministically
        while (cur.size() > 2) {
            vector<int> A, B;
            for (int i = 0; i < (int)cur.size(); ++i) {
                if (i < (int)cur.size()/2) A.push_back(cur[i]);
                else B.push_back(cur[i]);
            }
            i64 cA = ask_indices(A);
            if (cA > 0) cur.swap(A);
            else {
                i64 cB = ask_indices(B);
                if (cB > 0) cur.swap(B);
                else {
                    // give up
                    break;
                }
            }
        }
    }
    if (cur.size() == 2) {
        i64 c2 = ask_indices(cur);
        if (c2 == 1) return {cur[0], cur[1]};
    }
    // As a last resort: do pairwise checks in small set
    // This should be extremely rare
    for (int i = 0; i < (int)cur.size(); ++i) {
        for (int j = i + 1; j < (int)cur.size(); ++j) {
            cout << "0 2 " << arr[cur[i]] << " " << arr[cur[j]] << '\n' << flush;
            i64 r;
            if (!(cin >> r)) exit(0);
            if (r == 1) return {cur[i], cur[j]};
        }
    }
    // If we reach here something went wrong; return first two
    if (cur.size() >= 2) return {cur[0], cur[1]};
    // Shouldn't happen
    return {-1, -1};
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    // Generate distinct random numbers
    arr.reserve(M);
    unordered_set<u64> used;
    used.reserve(M * 2);
    uniform_int_distribution<u64> dist(1, MAXV);
    while ((int)arr.size() < M) {
        u64 x = dist(rng);
        if (used.insert(x).second) arr.push_back(x);
    }

    // Initial ask: whole set
    i64 c_total = ask_values(arr);
    if (c_total <= 0) {
        // Very unlikely; try regenerate a smaller set to ensure at least one collision
        // We'll try a couple of retries with new arrays
        bool found = false;
        for (int attempt = 0; attempt < 2 && !found; ++attempt) {
            arr.clear();
            used.clear();
            int MM = M / 2;
            arr.reserve(MM);
            used.reserve(MM * 2);
            while ((int)arr.size() < MM) {
                u64 x = dist(rng);
                if (used.insert(x).second) arr.push_back(x);
            }
            c_total = ask_values(arr);
            if (c_total > 0) found = true;
        }
        if (!found) {
            // As a last attempt: small dense sequence may cause collisions for small n
            arr.clear();
            int K = 100000;
            arr.reserve(K);
            for (int i = 0; i < K; ++i) arr.push_back((u64)i + 1);
            c_total = ask_values(arr);
            if (c_total <= 0) {
                // Give up and guess n=2
                cout << "1 2\n" << flush;
                return 0;
            }
        }
    }

    // Find a colliding pair via halving
    vector<int> ids(arr.size());
    iota(ids.begin(), ids.end(), 0);
    pair<int,int> pr = find_pair_with_collision(ids, c_total);
    if (pr.first < 0 || pr.second < 0) {
        // Fallback: guess 2
        cout << "1 2\n" << flush;
        return 0;
    }

    u64 a = arr[pr.first], b = arr[pr.second];
    u64 G = (a > b) ? (a - b) : (b - a);
    if (G == 0) {
        // Shouldn't happen due to distinctness; guess 2
        cout << "1 2\n" << flush;
        return 0;
    }

    // Factor G
    vector<u64> facs;
    factor(G, facs);
    sort(facs.begin(), facs.end());
    // Reduce G by dividing out prime factors not necessary for n
    for (size_t i = 0; i < facs.size(); ) {
        u64 p = facs[i];
        int cnt = 0;
        while (i < facs.size() && facs[i] == p) { ++cnt; ++i; }
        for (int e = 0; e < cnt; ++e) {
            if (G % p == 0) {
                u64 G2 = G / p;
                if (test_divides(G2)) G = G2;
                else break;
            } else break;
        }
    }

    // Output final guess
    cout << "1 " << G << '\n' << flush;
    return 0;
}