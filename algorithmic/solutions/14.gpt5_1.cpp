#include <bits/stdc++.h>
using namespace std;

// Interactive helper: print query and read response
static const long long XMAX = 1000000000LL;
static const int MAX_WALKS = 200000;

mt19937_64 rng(chrono::steady_clock::now().time_since_epoch().count());

long long walks_used = 0;
long long total_steps = 0;

long long walk_query(long long x) {
    if (walks_used >= MAX_WALKS) {
        // Exceeded allowed number of walk queries; make a final guess of 1 to terminate.
        cout << "guess " << 1 << endl;
        cout.flush();
        exit(0);
    }
    cout << "walk " << x << endl;
    cout.flush();
    walks_used++;
    long long resp;
    if (!(cin >> resp)) {
        exit(0);
    }
    if (resp == -1) exit(0);
    return resp;
}

void make_guess(long long g) {
    cout << "guess " << g << endl;
    cout.flush();
    exit(0);
}

// 64-bit arithmetic helpers for Miller-Rabin and Pollard-Rho
using u128 = unsigned __int128;
using u64 = unsigned long long;

u64 mod_mul(u64 a, u64 b, u64 mod) {
    return (u128)a * b % mod;
}

u64 mod_pow(u64 a, u64 d, u64 mod) {
    u64 r = 1;
    while (d) {
        if (d & 1) r = mod_mul(r, a, mod);
        a = mod_mul(a, a, mod);
        d >>= 1;
    }
    return r;
}

bool isPrime64(u64 n) {
    if (n < 2) return false;
    for (u64 p : {2ULL,3ULL,5ULL,7ULL,11ULL,13ULL,17ULL,19ULL,23ULL,29ULL,31ULL,37ULL}) {
        if (n % p == 0) return n == p;
    }
    u64 d = n - 1, s = 0;
    while ((d & 1) == 0) { d >>= 1; ++s; }
    // Deterministic bases for 64-bit
    for (u64 a : {2ULL, 3ULL, 5ULL, 7ULL, 11ULL, 13ULL}) {
        if (a % n == 0) continue;
        u64 x = mod_pow(a, d, n);
        if (x == 1 || x == n - 1) continue;
        bool comp = true;
        for (u64 r = 1; r < s; ++r) {
            x = mod_mul(x, x, n);
            if (x == n - 1) { comp = false; break; }
        }
        if (comp) return false;
    }
    return true;
}

u64 pollard_rho(u64 n) {
    if ((n & 1ULL) == 0) return 2;
    if (n % 3ULL == 0) return 3;
    u64 c = uniform_int_distribution<u64>(1, n - 1)(rng);
    u64 x = uniform_int_distribution<u64>(0, n - 1)(rng);
    u64 y = x;
    u64 d = 1;
    auto f = [&](u64 v){ return (mod_mul(v, v, n) + c) % n; };
    while (d == 1) {
        x = f(x);
        y = f(f(y));
        u64 diff = x > y ? x - y : y - x;
        d = std::gcd(diff, n);
    }
    if (d == n) return pollard_rho(n);
    return d;
}

void factor_rec(u64 n, vector<u64>& fac) {
    if (n == 1) return;
    if (isPrime64(n)) { fac.push_back(n); return; }
    u64 d = pollard_rho(n);
    factor_rec(d, fac);
    factor_rec(n / d, fac);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    // Initial position label
    long long curr_label = walk_query(0);
    unordered_map<int, long long> last_seen;
    last_seen.reserve(300000);
    last_seen[(int)curr_label] = 0;

    long long g = 0;

    // Random walk until we get at least one collision (ideally), then refine gcd
    while (walks_used < MAX_WALKS) {
        long long x = (long long)(uniform_int_distribution<unsigned long long>(1ULL, (unsigned long long)XMAX)(rng));
        long long label = walk_query(x);
        total_steps += x;

        auto it = last_seen.find((int)label);
        if (it != last_seen.end()) {
            long long D = total_steps - it->second;
            g = std::gcd(g, D);
            it->second = total_steps;
        } else {
            last_seen[(int)label] = total_steps;
        }
        curr_label = label;

        if (g != 0 && g <= XMAX) {
            // Factor g and strip redundant prime factors using small walks (g/p <= 1e9)
            vector<u64> fac;
            factor_rec((u64)g, fac);
            // Count prime exponents
            unordered_map<u64, int> cnt;
            cnt.reserve(fac.size()*2 + 1);
            for (u64 p : fac) cnt[p]++;
            // Sort primes for deterministic behavior
            vector<pair<u64,int>> primes;
            primes.reserve(cnt.size());
            for (auto &kv : cnt) primes.emplace_back(kv.first, kv.second);
            sort(primes.begin(), primes.end());

            for (auto &pe : primes) {
                u64 p = pe.first;
                int e = pe.second;
                for (int t = 0; t < e; ++t) {
                    long long candidate = g / (long long)p;
                    if (candidate == 0) break;
                    if (candidate > XMAX) break; // cannot test if larger than 1e9
                    // Test if moving by candidate returns to same label
                    long long prev_label = curr_label;
                    long long new_label = walk_query(candidate);
                    total_steps += candidate;
                    // Update last_seen for potential future improvements
                    auto it2 = last_seen.find((int)new_label);
                    if (it2 != last_seen.end()) {
                        long long D2 = total_steps - it2->second;
                        g = std::gcd(g, D2);
                        it2->second = total_steps;
                    } else {
                        last_seen[(int)new_label] = total_steps;
                    }
                    if (new_label == prev_label) {
                        // candidate is still multiple of n
                        g = candidate; // reduces g
                        curr_label = new_label;
                        // We reduced g, continue attempting to divide by p
                    } else {
                        // candidate not multiple of n, cannot divide further by p
                        curr_label = new_label;
                        break;
                    }
                }
            }
            if (g <= XMAX) {
                // Try to strip more factors while <= 1e9 (in case gcd refinement further reduced g via D2)
                vector<u64> fac2;
                factor_rec((u64)g, fac2);
                unordered_map<u64,int> cnt2;
                for (u64 p : fac2) cnt2[p]++;
                vector<pair<u64,int>> primes2;
                primes2.reserve(cnt2.size());
                for (auto &kv : cnt2) primes2.emplace_back(kv.first, kv.second);
                sort(primes2.begin(), primes2.end());
                for (auto &pe : primes2) {
                    u64 p = pe.first;
                    int e = pe.second;
                    for (int t = 0; t < e; ++t) {
                        long long candidate = g / (long long)p;
                        if (candidate == 0) break;
                        if (candidate > XMAX) break;
                        long long prev_label = curr_label;
                        long long new_label = walk_query(candidate);
                        total_steps += candidate;
                        auto it2 = last_seen.find((int)new_label);
                        if (it2 != last_seen.end()) {
                            long long D2 = total_steps - it2->second;
                            g = std::gcd(g, D2);
                            it2->second = total_steps;
                        } else {
                            last_seen[(int)new_label] = total_steps;
                        }
                        if (new_label == prev_label) {
                            g = candidate;
                            curr_label = new_label;
                        } else {
                            curr_label = new_label;
                            break;
                        }
                    }
                }
            }
            // If g <= 1e9 and no further reduction possible, guess
            if (g != 0 && g <= XMAX) {
                make_guess(g);
                return 0;
            }
        }
    }
    // Fallback guess if we run out of walk budget
    if (g == 0) g = XMAX; // arbitrary fallback
    if (g > XMAX) {
        // Reduce g by random collisions may not have helped enough; just bound to <=1e9
        g = min(g, XMAX);
    }
    make_guess(g);
    return 0;
}