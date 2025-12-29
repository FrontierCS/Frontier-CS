#include <bits/stdc++.h>
using namespace std;

using int64 = long long;
using u128 = __uint128_t;

mt19937_64 rng(chrono::steady_clock::now().time_since_epoch().count());

int64 rand_int64(int64 l, int64 r) {
    uniform_int_distribution<int64> dist(l, r);
    return dist(rng);
}

// Miller-Rabin and Pollard Rho for 64-bit integers

int64 mul_mod(int64 a, int64 b, int64 mod) {
    return (u128)a * (u128)b % mod;
}

int64 pow_mod(int64 a, int64 d, int64 mod) {
    int64 r = 1;
    while (d) {
        if (d & 1) r = mul_mod(r, a, mod);
        a = mul_mod(a, a, mod);
        d >>= 1;
    }
    return r;
}

bool isPrime(int64 n) {
    if (n < 2) return false;
    for (int64 p : {2,3,5,7,11,13,17,19,23,29,31,37}) {
        if (n == p) return true;
        if (n % p == 0) return false;
    }
    int64 d = n - 1;
    int s = 0;
    while ((d & 1) == 0) {
        d >>= 1;
        ++s;
    }
    // Deterministic bases for 64-bit integers
    for (int64 a : {2, 325, 9375, 28178, 450775, 9780504, 1795265022}) {
        if (a % n == 0) continue;
        int64 x = pow_mod(a % n, d, n);
        if (x == 1 || x == n - 1) continue;
        bool comp = true;
        for (int r = 1; r < s; ++r) {
            x = mul_mod(x, x, n);
            if (x == n - 1) {
                comp = false;
                break;
            }
        }
        if (comp) return false;
    }
    return true;
}

int64 pollard_rho(int64 n) {
    if (n % 2 == 0) return 2;
    if (n % 3 == 0) return 3;
    uniform_int_distribution<int64> dist(2, n - 2);
    while (true) {
        int64 x = dist(rng);
        int64 y = x;
        int64 c = dist(rng);
        if (c >= n) c %= n;
        if (c == 0) c = 1;
        int64 d = 1;
        while (d == 1) {
            x = (mul_mod(x, x, n) + c) % n;
            y = (mul_mod(y, y, n) + c) % n;
            y = (mul_mod(y, y, n) + c) % n;
            d = std::gcd(std::llabs(x - y), n);
            if (d == n) break;
        }
        if (d > 1 && d < n) return d;
    }
}

void factor_rec(int64 n, vector<int64>& fac) {
    if (n == 1) return;
    if (isPrime(n)) {
        fac.push_back(n);
        return;
    }
    int64 d = pollard_rho(n);
    factor_rec(d, fac);
    factor_rec(n / d, fac);
}

void gen_divisors_dfs(int idx, const vector<pair<int64,int>>& pe, int64 cur, vector<int64>& divs) {
    if (idx == (int)pe.size()) {
        divs.push_back(cur);
        return;
    }
    int64 p = pe[idx].first;
    int e = pe[idx].second;
    int64 v = 1;
    for (int i = 0; i <= e; ++i) {
        gen_divisors_dfs(idx + 1, pe, cur * v, divs);
        v *= p;
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    const int MAX_WALKS = 200000;
    const int TOTAL_WALKS = 150000; // total walk commands (including initial walk 0)
    const int COLLISION_TARGET = 20;

    int walks = 0;
    int64 S = 0;

    vector<int64> steps;
    vector<int> labels;
    steps.reserve(TOTAL_WALKS + 5);
    labels.reserve(TOTAL_WALKS + 5);

    unordered_map<int, int64> firstTime;
    firstTime.reserve(TOTAL_WALKS * 2);
    firstTime.max_load_factor(0.7);

    int64 G = 0;
    int collisions = 0;
    int64 max_label = 0;

    // Initial query: walk 0
    cout << "walk 0\n";
    cout.flush();
    ++walks;
    int curLabel;
    if (!(cin >> curLabel)) return 0;
    S = 0;
    steps.push_back(S);
    labels.push_back(curLabel);
    firstTime[curLabel] = S;
    max_label = curLabel;

    while (walks < TOTAL_WALKS && walks < MAX_WALKS) {
        int64 x = rand_int64(1, 1000000000LL);
        cout << "walk " << x << '\n';
        cout.flush();
        ++walks;
        S += x;
        int v;
        if (!(cin >> v)) return 0;
        steps.push_back(S);
        labels.push_back(v);

        auto it = firstTime.find(v);
        if (it == firstTime.end()) {
            firstTime[v] = S;
        } else {
            int64 d = S - it->second;
            if (d > 0) {
                G = std::gcd(G, d);
                ++collisions;
            }
        }
        if (v > max_label) max_label = v;

        if (collisions >= COLLISION_TARGET) break;
    }

    int64 LB = max(max_label, (int64)firstTime.size());
    int64 answer = LB;

    if (G != 0) {
        vector<int64> fac;
        factor_rec(G, fac);
        sort(fac.begin(), fac.end());
        vector<pair<int64,int>> pe;
        for (size_t i = 0; i < fac.size(); ) {
            size_t j = i;
            while (j < fac.size() && fac[j] == fac[i]) ++j;
            pe.push_back({fac[i], (int)(j - i)});
            i = j;
        }
        vector<int64> divisors;
        gen_divisors_dfs(0, pe, 1, divisors);
        sort(divisors.begin(), divisors.end());

        vector<int64> candidates;
        for (int64 d : divisors) {
            if (d >= LB && d <= 1000000000LL) {
                candidates.push_back(d);
            }
        }
        if (!candidates.empty()) {
            // Try candidates in ascending order, pick first consistent with data
            for (int64 d : candidates) {
                unordered_map<int64, int> mp;
                mp.reserve(steps.size() * 2);
                mp.max_load_factor(0.7f);
                bool ok = true;
                for (size_t i = 0; i < steps.size(); ++i) {
                    int64 r = steps[i] % d;
                    auto it = mp.find(r);
                    if (it == mp.end()) {
                        mp.emplace(r, labels[i]);
                    } else if (it->second != labels[i]) {
                        ok = false;
                        break;
                    }
                }
                if (ok) {
                    answer = d;
                    break;
                }
            }
        } else {
            answer = LB;
        }
    } else {
        answer = LB;
    }

    cout << "guess " << answer << '\n';
    cout.flush();
    return 0;
}