#include <bits/stdc++.h>
using namespace std;

using u64 = unsigned long long;
using u128 = __uint128_t;
using i64 = long long;

static mt19937_64 rng((u64)chrono::high_resolution_clock::now().time_since_epoch().count());

const u64 LIM = 1000000000000000000ULL; // 1e18

// Global spent counter (total cost = sum of query sizes)
u64 total_cost = 0;

// Ask a query to the interactor with a vector of numbers, returns number of collisions
long long ask(const vector<u64>& a) {
    cout << 0 << ' ' << a.size();
    for (u64 x : a) cout << ' ' << x;
    cout << '\n' << flush;
    long long ans;
    if (!(cin >> ans)) exit(0); // if interactor ends
    total_cost += a.size();
    return ans;
}

// Guess the final n and exit
[[noreturn]] void guess_and_exit(u64 n) {
    cout << 1 << ' ' << n << '\n' << flush;
    exit(0);
}

// Sieve primes up to MAXP
vector<int> sieve_primes(int MAXP) {
    vector<bool> is_prime(MAXP + 1, true);
    is_prime[0] = is_prime[1] = false;
    for (int i = 2; (long long)i * i <= MAXP; i++) if (is_prime[i]) {
        for (int j = i * i; j <= MAXP; j += i) is_prime[j] = false;
    }
    vector<int> primes;
    for (int i = 2; i <= MAXP; i++) if (is_prime[i]) primes.push_back(i);
    return primes;
}

// Modular multiplication and power
u64 mulmod(u64 a, u64 b, u64 mod) {
    return (u128)a * b % mod;
}
u64 powmod(u64 a, u64 e, u64 mod) {
    u64 r = 1;
    while (e) {
        if (e & 1) r = mulmod(r, a, mod);
        a = mulmod(a, a, mod);
        e >>= 1;
    }
    return r;
}
// Miller-Rabin for 64-bit
bool isPrime(u64 n) {
    if (n < 2) return false;
    static u64 testPrimes[] = {2ULL,3ULL,5ULL,7ULL,11ULL,13ULL,17ULL,19ULL,23ULL,29ULL,31ULL,37ULL};
    for (u64 p : testPrimes) {
        if (n%p==0) return n==p;
    }
    u64 d = n-1, s = 0;
    while ((d & 1) == 0) { d >>= 1; s++; }
    auto check = [&](u64 a)->bool{
        if (a % n == 0) return true;
        u64 x = powmod(a, d, n);
        if (x == 1 || x == n-1) return true;
        for (u64 r=1; r<s; r++) {
            x = mulmod(x, x, n);
            if (x == n-1) return true;
        }
        return false;
    };
    for (u64 a : testPrimes) {
        if (!check(a)) return false;
    }
    return true;
}

// Pollard Rho
u64 pollard(u64 n) {
    if (n % 2ULL == 0ULL) return 2ULL;
    if (n % 3ULL == 0ULL) return 3ULL;
    u64 c = uniform_int_distribution<u64>(1, n-1)(rng);
    u64 x = uniform_int_distribution<u64>(0, n-1)(rng);
    u64 y = x;
    u64 d = 1;
    auto f = [&](u64 x)->u64 { return (mulmod(x, x, n) + c) % n; };
    while (d == 1) {
        x = f(x);
        y = f(f(y));
        u64 diff = x > y ? x - y : y - x;
        d = std::gcd(diff, n);
        if (d == n) return pollard(n);
    }
    return d;
}

void factor(u64 n, vector<u64>& fac) {
    if (n == 1) return;
    if (isPrime(n)) { fac.push_back(n); return; }
    u64 d = pollard(n);
    factor(d, fac);
    factor(n/d, fac);
}

// Query helper with indices
long long query_indices(const vector<int>& idx, const vector<u64>& X) {
    vector<u64> arr;
    arr.reserve(idx.size());
    for (int i : idx) arr.push_back(X[i]);
    return ask(arr);
}
long long query_union(const vector<int>& A, const vector<int>& B, const vector<u64>& X) {
    vector<u64> arr;
    arr.reserve(A.size() + B.size());
    for (int i : A) arr.push_back(X[i]);
    for (int j : B) arr.push_back(X[j]);
    return ask(arr);
}

// Test if n divides d: query [1, 1 + d]
bool n_divides(u64 d) {
    vector<u64> arr = {1ULL, 1ULL + d};
    long long r = ask(arr);
    return r > 0;
}

// Split indices into two halves
void split_half(const vector<int>& S, vector<int>& A, vector<int>& B) {
    size_t m = S.size()/2;
    A.assign(S.begin(), S.begin() + m);
    B.assign(S.begin() + m, S.end());
}

// cross find pair across two disjoint sets L and R
pair<int,int> cross_find(vector<int> L, vector<int> R, const vector<u64>& X) {
    while (true) {
        if (L.size() == 1 && R.size() == 1) return {L[0], R[0]};
        if (L.size() == 1) {
            while (R.size() > 1) {
                vector<int> R1, R2;
                split_half(R, R1, R2);
                long long c1 = query_union(vector<int>{L[0]}, R1, X);
                if (c1 > 0) R = R1;
                else R = R2;
            }
            return {L[0], R[0]};
        }
        if (R.size() == 1) {
            while (L.size() > 1) {
                vector<int> L1, L2;
                split_half(L, L1, L2);
                long long c1 = query_union(L1, vector<int>{R[0]}, X);
                if (c1 > 0) L = L1;
                else L = L2;
            }
            return {L[0], R[0]};
        }
        vector<int> L1, L2, R1, R2;
        split_half(L, L1, L2);
        split_half(R, R1, R2);
        long long c11 = query_union(L1, R1, X);
        if (c11 > 0) { L = L1; R = R1; continue; }
        long long c12 = query_union(L1, R2, X);
        if (c12 > 0) { L = L1; R = R2; continue; }
        long long c21 = query_union(L2, R1, X);
        if (c21 > 0) { L = L2; R = R1; }
        else { L = L2; R = R2; }
    }
}

// find a pair indices (i,j) within set S with collisions>0
pair<int,int> find_pair_indices(const vector<u64>& X) {
    int n = (int)X.size();
    vector<int> S(n);
    iota(S.begin(), S.end(), 0);
    long long cS = query_indices(S, X);
    if (cS <= 0) return {-1, -1};
    while ((int)S.size() > 1) {
        vector<int> L, R;
        split_half(S, L, R);
        long long cL = query_indices(L, X);
        if (cL > 0) { S = L; cS = cL; continue; }
        long long cR = query_indices(R, X);
        if (cR > 0) { S = R; cS = cR; continue; }
        // cross case
        pair<int,int> pr = cross_find(L, R, X);
        return pr;
    }
    return {-1, -1};
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    // Sieve primes up to 1e6
    const int MAXP = 1000000;
    vector<int> primes = sieve_primes(MAXP);

    // Step 1: find small prime powers dividing n
    u64 g = 1;
    for (int p : primes) {
        if (n_divides((u64)p)) {
            u64 pp = p;
            while (n_divides(pp)) {
                if (g <= (u64)1000000000ULL / (u64)p) g *= (u64)p; // g divides n, so won't overflow under 1e9
                else break;
                if (pp > LIM / (u64)p) break; // guard
                pp *= (u64)p;
            }
        }
    }
    // Check if g == n
    if (n_divides(g)) {
        guess_and_exit(g);
    }

    // Now remainder m = n/g is either 1 or a prime > 1e6.
    // We'll find this prime P by random differences using numbers of the form 1 + g*E.
    u64 MaxE = (LIM - 1) / max<u64>(g, 1ULL);
    if (MaxE < 3) MaxE = 3;

    auto gen_set = [&](int T, vector<u64>& X, vector<u64>& E) {
        X.clear(); E.clear(); X.reserve(T); E.reserve(T);
        unordered_set<u64> used;
        used.reserve(T * 2);
        uniform_int_distribution<u64> dist(1, MaxE);
        while ((int)E.size() < T) {
            u64 e = dist(rng);
            if (used.insert(e).second) {
                E.push_back(e);
                u64 x = 1 + g * e;
                if (x < 1 || x > LIM) continue; // should not happen
                X.push_back(x);
            }
        }
    };

    auto get_difference = [&](int T)->u64 {
        for (int attempt = 0; attempt < 6; attempt++) {
            vector<u64> X, E;
            gen_set(T, X, E);
            long long cS = ask(X);
            if (cS <= 0) continue;
            // Now find a colliding pair
            // Provide to find_pair_indices: it will re-query collisions within subsets
            pair<int,int> pr = find_pair_indices(X);
            if (pr.first != -1) {
                u64 a = E[pr.first], b = E[pr.second];
                u64 diff = (a > b) ? (a - b) : (b - a);
                if (diff > 0) return diff;
            }
        }
        return 0ULL;
    };

    // Choose T such that expected collisions ~ 1-3 for worst-case P ~ 1e9
    int T = 60000;

    vector<u64> diffs;
    // Try to collect two differences
    for (int i = 0; i < 3 && (int)diffs.size() < 2; i++) {
        u64 d = get_difference(T);
        if (d) diffs.push_back(d);
    }

    // If still not enough, try with slightly larger T
    if (diffs.size() < 2) {
        T = 70000;
        for (int i = 0; i < 3 && (int)diffs.size() < 2; i++) {
            u64 d = get_difference(T);
            if (d) diffs.push_back(d);
        }
    }

    // If still not enough, fallback: try even more times with T=80000
    if (diffs.size() < 2) {
        T = 80000;
        for (int i = 0; i < 3 && (int)diffs.size() < 2; i++) {
            u64 d = get_difference(T);
            if (d) diffs.push_back(d);
        }
    }

    // If still failed (extremely unlikely), guess as g (best effort)
    if (diffs.size() < 2) {
        // As a last resort, try random primes near 1e9 to test divisibility
        // but since we must output something, guess g
        guess_and_exit(g);
    }

    u64 G = std::gcd(diffs[0], diffs[1]);
    if (G == 0) G = diffs[0] ^ diffs[1];

    // Remove small prime factors <= 1e6 from G
    for (int p : primes) {
        while (G % (u64)p == 0ULL) G /= (u64)p;
        if (G == 1) break;
    }

    // If still composite, factor G
    u64 candidateP = 0;
    if (G > 1) {
        if (isPrime(G)) {
            // Verify if this prime divides n
            if (n_divides(g * (u64)G)) candidateP = G;
        } else {
            vector<u64> fac;
            factor(G, fac);
            // deduplicate and sort
            sort(fac.begin(), fac.end());
            fac.erase(unique(fac.begin(), fac.end()), fac.end());
            for (u64 p : fac) {
                if (p <= (u64)MAXP) continue; // already accounted
                if (isPrime(p)) {
                    if (n_divides(g * p)) { candidateP = p; break; }
                } else {
                    // Further factor if needed
                    vector<u64> fac2;
                    factor(p, fac2);
                    sort(fac2.begin(), fac2.end());
                    fac2.erase(unique(fac2.begin(), fac2.end()), fac2.end());
                    for (u64 q : fac2) {
                        if (q <= (u64)MAXP) continue;
                        if (isPrime(q) && n_divides(g * q)) { candidateP = q; break; }
                    }
                    if (candidateP) break;
                }
            }
        }
    }

    if (candidateP == 0) {
        // Try to get a third difference and recompute gcd
        u64 d3 = get_difference(T);
        if (d3) {
            G = std::gcd(G, d3);
            for (int p : primes) {
                while (G % (u64)p == 0ULL) G /= (u64)p;
                if (G == 1) break;
            }
            if (G > 1) {
                if (isPrime(G)) {
                    if (n_divides(g * G)) candidateP = G;
                } else {
                    vector<u64> fac;
                    factor(G, fac);
                    sort(fac.begin(), fac.end());
                    fac.erase(unique(fac.begin(), fac.end()), fac.end());
                    for (u64 p : fac) {
                        if (p <= (u64)MAXP) continue;
                        if (isPrime(p) && n_divides(g * p)) { candidateP = p; break; }
                    }
                }
            }
        }
    }

    // If still no candidate found, best effort guess g
    if (candidateP == 0) {
        guess_and_exit(g);
    }

    u64 n = g * candidateP;
    guess_and_exit(n);
}