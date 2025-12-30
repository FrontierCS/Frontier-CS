#include <bits/stdc++.h>
using namespace std;

using ll = long long;
using u64 = unsigned long long;
using u128 = __uint128_t;

const int MAX_WALKS = 200000;

// RNG
mt19937_64 rng(712367821937ULL);

// Modular multiplication and exponentiation for 64-bit
ll mod_mul(ll a, ll b, ll mod) {
    return (ll)((u128)a * (u128)b % (u128)mod);
}

ll mod_pow(ll a, ll d, ll mod) {
    ll r = 1;
    while (d > 0) {
        if (d & 1) r = mod_mul(r, a, mod);
        a = mod_mul(a, a, mod);
        d >>= 1;
    }
    return r;
}

// Deterministic Miller-Rabin for 64-bit
bool isPrime(ll n) {
    if (n < 2) return false;
    static const ll testPrimes[] = {2,3,5,7,11,13,17,19,23,0};
    for (int i = 0; testPrimes[i]; ++i) {
        if (n == testPrimes[i]) return true;
        if (n % testPrimes[i] == 0) return n == testPrimes[i];
    }
    ll d = n - 1;
    int s = 0;
    while ((d & 1) == 0) {
        d >>= 1;
        ++s;
    }
    static const ll bases[] = {2,325,9375,28178,450775,9780504,1795265022,0};
    for (int i = 0; bases[i]; ++i) {
        ll a = bases[i] % n;
        if (a == 0) continue;
        ll x = mod_pow(a, d, n);
        if (x == 1 || x == n - 1) continue;
        bool comp = true;
        for (int r = 1; r < s; ++r) {
            x = mod_mul(x, x, n);
            if (x == n - 1) {
                comp = false;
                break;
            }
        }
        if (comp) return false;
    }
    return true;
}

// Pollard's Rho
ll pollard_rho(ll n) {
    if ((n & 1) == 0) return 2;
    while (true) {
        ll x = uniform_int_distribution<ll>(2, n - 2)(rng);
        ll y = x;
        ll c = uniform_int_distribution<ll>(1, n - 1)(rng);
        ll d = 1;
        auto f = [&](ll v) {
            return (mod_mul(v, v, n) + c) % n;
        };
        while (d == 1) {
            x = f(x);
            y = f(f(y));
            d = std::gcd(abs(x - y), n);
        }
        if (d != n) return d;
    }
}

void factor_rec(ll n, vector<ll> &fac) {
    if (n == 1) return;
    if (isPrime(n)) {
        fac.push_back(n);
        return;
    }
    ll d = pollard_rho(n);
    factor_rec(d, fac);
    factor_rec(n / d, fac);
}

// Consistency check for candidate period m
bool is_consistent(ll m, const vector<ll> &times, const vector<int> &labels) {
    unordered_map<ll, int> mp;
    mp.reserve(times.size() * 2);
    for (size_t i = 0; i < times.size(); ++i) {
        ll r = times[i] % m;
        auto it = mp.find(r);
        if (it == mp.end()) {
            mp.emplace(r, labels[i]);
        } else {
            if (it->second != labels[i]) return false;
        }
    }
    return true;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    ll walkCount = 0;
    ll curTime = 0;

    auto do_walk = [&](ll x) -> int {
        ++walkCount;
        cout << "walk " << x << '\n';
        cout.flush();
        int label;
        if (!(cin >> label)) {
            exit(0);
        }
        return label;
    };

    auto do_guess = [&](ll g) {
        cout << "guess " << g << '\n';
        cout.flush();
    };

    // Initial query to get starting label
    int startLabel = do_walk(0);
    vector<ll> times;
    vector<int> labels;
    times.reserve(MAX_WALKS + 5);
    labels.reserve(MAX_WALKS + 5);

    times.push_back(curTime);
    labels.push_back(startLabel);

    unordered_map<int, ll> lastTime;
    lastTime.reserve(1 << 17);
    lastTime[startLabel] = curTime;

    ll G = 0; // gcd of differences for equal labels
    int collisions = 0;
    ll lastGChangeWalk = walkCount;
    ll prevG = 0;

    auto add_collision = [&](ll D) {
        if (D == 0) return;
        ++collisions;
        if (G == 0) G = D;
        else G = std::gcd(G, D);
    };

    // Main querying loop
    while (walkCount < MAX_WALKS - 1) {
        ll x = (ll)(rng() % 1000000000ULL) + 1; // 1..1e9
        curTime += x;
        int lab = do_walk(x);

        times.push_back(curTime);
        labels.push_back(lab);

        auto it = lastTime.find(lab);
        if (it != lastTime.end()) {
            ll D = curTime - it->second;
            add_collision(D);
            it->second = curTime;
        } else {
            lastTime[lab] = curTime;
        }

        if (G != prevG) {
            prevG = G;
            lastGChangeWalk = walkCount;
        }

        if (G > 0 && collisions >= 20 && walkCount - lastGChangeWalk > 500) {
            break;
        }
    }

    if (G == 0) {
        // Degenerate: no collision observed
        // Best we can do is output some guess; probability is extremely low in random setting.
        do_guess(1000000007LL);
        return 0;
    }

    // Factor G and shrink to minimal period consistent with observations
    vector<ll> facs;
    factor_rec(G, facs);
    sort(facs.begin(), facs.end());

    vector<pair<ll,int>> pf;
    for (size_t i = 0; i < facs.size();) {
        size_t j = i;
        while (j < facs.size() && facs[j] == facs[i]) ++j;
        pf.emplace_back(facs[i], (int)(j - i));
        i = j;
    }

    ll nCand = G;
    for (auto [p, e] : pf) {
        for (int k = 0; k < e; ++k) {
            ll m = nCand / p;
            if (m == 0) break;
            if (is_consistent(m, times, labels)) {
                nCand = m;
            } else {
                break;
            }
        }
    }

    do_guess(nCand);
    return 0;
}