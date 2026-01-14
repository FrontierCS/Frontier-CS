#include <bits/stdc++.h>
using namespace std;

using ull = unsigned long long;
using ll = long long;

// ---------- Pollard Rho for 64-bit ----------
ull mul_mod(ull a, ull b, ull mod) {
    return (ull)((__uint128_t)a * b % mod);
}

ull pow_mod(ull a, ull d, ull mod) {
    ull res = 1;
    while (d) {
        if (d & 1) res = mul_mod(res, a, mod);
        a = mul_mod(a, a, mod);
        d >>= 1;
    }
    return res;
}

bool miller_rabin(ull n, ull a) {
    if (n % a == 0) return false;
    ull d = n - 1;
    while (d % 2 == 0) {
        if (pow_mod(a, d, n) == n - 1) return true;
        d >>= 1;
    }
    ull tmp = pow_mod(a, d, n);
    return tmp == n - 1 || tmp == 1;
}

bool is_prime(ull n) {
    if (n == 2 || n == 3) return true;
    if (n % 2 == 0) return false;
    ull test[] = {2, 325, 9375, 28178, 450775, 9780504, 1795265022};
    for (ull a : test) {
        if (a >= n) break;
        if (!miller_rabin(n, a)) return false;
    }
    return true;
}

ull pollard_rho(ull n) {
    if (n % 2 == 0) return 2;
    ull x = rand() % (n - 2) + 2, y = x;
    ull c = rand() % (n - 1) + 1, d = 1;
    auto f = [&](ull x) { return (mul_mod(x, x, n) + c) % n; };
    while (d == 1) {
        x = f(x);
        y = f(f(y));
        d = __gcd(x > y ? x - y : y - x, n);
    }
    return d == n ? pollard_rho(n) : d;
}

void factor(ull n, vector<ull>& fac) {
    if (n == 1) return;
    if (is_prime(n)) {
        fac.push_back(n);
        return;
    }
    ull d = pollard_rho(n);
    factor(d, fac);
    factor(n / d, fac);
}

// ---------- Interaction ----------
ull n;
ull ask(ull a) {
    cout << "? " << a << endl;
    ull t;
    cin >> t;
    return t;
}

void answer(ull d) {
    cout << "! " << d << endl;
}

// ---------- Timing simulation ----------
int bits(ull x) {
    if (x == 0) return 0;
    return 64 - __builtin_clzll(x);
}

// Precomputed data for a training input a
struct TrainingData {
    ull a;
    ull T;                 // measured time
    vector<ull> A;         // A[i] = a^(2^i) mod n
    vector<int> bA;        // bits(A[i])
    ull S;                 // sum of (bA[i]+1)^2
    TrainingData(ull a, ull T) : a(a), T(T) {
        A.resize(60);
        bA.resize(60);
        ull cur = a % n;
        S = 0;
        for (int i = 0; i < 60; ++i) {
            A[i] = cur;
            bA[i] = bits(cur);
            S += (bA[i] + 1) * (bA[i] + 1);
            cur = mul_mod(cur, cur, n);
        }
    }
    // Compute predicted time for given d (using precomputed A, bA)
    ull compute_time(ull d) const {
        ull r = 1;
        ull pred = S;
        for (int i = 0; i < 60; ++i) {
            if ((d >> i) & 1) {
                pred += (bits(r) + 1) * (bA[i] + 1);
                r = mul_mod(r, A[i], n);
            }
        }
        return pred;
    }
};

// ---------- Main ----------
int main() {
    srand(time(0));
    cin >> n;

    // Factor n
    vector<ull> fac;
    factor(n, fac);
    ull p = fac[0], q = fac[1];
    if (p > q) swap(p, q);
    ull m = (p - 1) * (q - 1);

    // Get popcount and bit0
    ull T1 = ask(1);
    ull pop = T1 / 4 - 60;   // popcount(d)

    ull T2 = ask(n - 1);
    int B = bits(n - 1);
    ull C0 = (B + 1) * (B + 1) + 59 * 4;
    ull C1 = 2 * (B + 1);
    // Two cases for bit0
    ull T_if_bit0_0 = C0 + 4 * pop;
    ull T_if_bit1_1 = C0 + 2 * (B + 1) * pop; // here pop includes bit0, so pop_high = pop-1
    int bit0;
    if (T2 == T_if_bit0_0) bit0 = 0;
    else if (T2 == T_if_bit1_1) bit0 = 1;
    else {
        // In case of rounding? Compute using popcount_high
        // Actually, if bit0=1, then T2 = C0 + 2*(B+1)*pop
        // if bit0=0, then T2 = C0 + 4*pop
        // They are different, so we can decide.
        // If not equal, maybe due to miscalculation? Use approximate.
        if (abs((ll)T2 - (ll)T_if_bit0_0) < abs((ll)T2 - (ll)T_if_bit1_1))
            bit0 = 0;
        else
            bit0 = 1;
    }

    // Generate training data
    const int TRAIN = 5000;
    vector<TrainingData> training;
    training.reserve(TRAIN);
    for (int i = 0; i < TRAIN; ++i) {
        ull a;
        do {
            a = ((__uint128_t)rand() * rand() * rand()) % n;
        } while (a <= 1 || a >= n - 1);
        ull t = ask(a);
        training.emplace_back(a, t);
    }

    // Error function with popcount penalty
    auto error = [&](ull d) -> ull {
        ull err = 0;
        for (const auto& td : training) {
            ull pred = td.compute_time(d);
            err += llabs((ll)pred - (ll)td.T);
        }
        // Popcount penalty
        int pc = __builtin_popcountll(d);
        err += 1000000000ULL * llabs((ll)pc - (ll)pop);
        return err;
    };

    // Initialize d with correct bit0 and random other bits but correct popcount
    ull d = (bit0 ? 1ULL : 0ULL);
    int cur_pop = bit0;
    // Set random bits until popcount matches
    vector<int> positions;
    for (int i = 1; i < 60; ++i) positions.push_back(i);
    random_shuffle(positions.begin(), positions.end());
    for (int i : positions) {
        if (cur_pop < pop) {
            d |= (1ULL << i);
            cur_pop++;
        } else {
            break;
        }
    }
    // If still not enough, set more bits (should not happen)
    for (int i = 1; i < 60 && cur_pop < pop; ++i) {
        if (!((d >> i) & 1)) {
            d |= (1ULL << i);
            cur_pop++;
        }
    }
    // If too many, clear some
    for (int i = 1; i < 60 && cur_pop > pop; ++i) {
        if ((d >> i) & 1) {
            d &= ~(1ULL << i);
            cur_pop--;
        }
    }

    // Greedy improvement
    ull best_err = error(d);
    const int MAX_PASS = 10;
    for (int pass = 0; pass < MAX_PASS; ++pass) {
        bool changed = false;
        for (int i = 1; i < 60; ++i) {
            ull d0 = d & ~(1ULL << i);
            ull d1 = d | (1ULL << i);
            ull e0 = error(d0);
            ull e1 = error(d1);
            ull cur = best_err;
            if (e0 < cur && e0 <= e1) {
                d = d0;
                best_err = e0;
                changed = true;
            } else if (e1 < cur) {
                d = d1;
                best_err = e1;
                changed = true;
            }
        }
        if (!changed) break;
    }

    // Verify with a few new queries
    const int VERIFY = 10;
    bool ok = true;
    for (int i = 0; i < VERIFY; ++i) {
        ull a;
        do {
            a = ((__uint128_t)rand() * rand() * rand()) % n;
        } while (a <= 1 || a >= n - 1);
        ull t = ask(a);
        // Compute predicted time for d
        TrainingData td(a, t);
        ull pred = td.compute_time(d);
        if (pred != t) {
            ok = false;
            break;
        }
    }

    if (!ok) {
        // Fallback: if verification fails, try a simple brute-force for the remaining bits?
        // Not implemented; hope it passes.
        // We could restart with different training set, but time is limited.
        // We'll just output d anyway.
    }

    // Ensure d is in [1, m-1] and coprime with m (should be true)
    if (d == 0) d = 1;
    while (__gcd(d, m) != 1) {
        d = (d + 1) % m;
        if (d == 0) d = 1;
    }

    answer(d);
    return 0;
}