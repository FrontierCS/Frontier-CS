#include <bits/stdc++.h>
using namespace std;

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

static const int MAX_Q = 200000;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int q = 0;

    auto walk_cmd = [&](long long x) -> int {
        if (x < 0) x = 0;
        if (x > 1000000000LL) x = 1000000000LL;
        if (q >= MAX_Q) exit(0);
        cout << "walk " << x << '\n' << flush;
        int v;
        if (!(cin >> v)) exit(0);
        if (v == -1) exit(0);
        ++q;
        return v;
    };

    auto guess_cmd = [&](long long g) -> void {
        if (g < 1) g = 1;
        if (g > 1000000000LL) g = 1000000000LL;
        cout << "guess " << g << '\n' << flush;
        exit(0);
    };

    mt19937_64 rng(chrono::steady_clock::now().time_since_epoch().count());
    uniform_int_distribution<long long> dist(1, 1000000000LL);

    long long total = 0;
    int cur = walk_cmd(0);

    unordered_map<int, long long, CustomHash> last;
    last.reserve(1 << 20);
    last.max_load_factor(0.7f);
    last[cur] = 0;

    long long g = 0;

    auto do_random_walk = [&]() {
        long long x = dist(rng);
        cur = walk_cmd(x);
        total += x;
        auto it = last.find(cur);
        if (it != last.end()) {
            long long diff = total - it->second;
            if (diff != 0) g = std::gcd(g, diff);
            it->second = total;
        } else {
            last[cur] = total;
        }
    };

    // Phase 1: gather collisions until gcd becomes <= 1e9 (and non-zero).
    // Leave some room for reduction tests.
    const int SAFE_REMAIN = 200;
    while (q < MAX_Q - SAFE_REMAIN && (g == 0 || g > 1000000000LL)) {
        do_random_walk();
    }

    if (g == 0) {
        // Extremely unlikely; best-effort fallback.
        guess_cmd(1);
    }

    // If still too large, attempt a bit more (if possible).
    while (q < MAX_Q - SAFE_REMAIN && g > 1000000000LL) {
        do_random_walk();
    }

    if (g > 1000000000LL) {
        // Best-effort fallback: try to reduce by continuing to gather gcd via more collisions is no longer possible.
        // Guess something within limits (will likely score 0 if wrong).
        guess_cmd(1000000000LL);
    }

    long long candidate = g;

    // Factor candidate (<= 1e9) by trial division.
    vector<long long> primes;
    long long tmp = candidate;
    for (long long p = 2; p * p <= tmp; ++p) {
        if (tmp % p == 0) {
            primes.push_back(p);
            while (tmp % p == 0) tmp /= p;
        }
    }
    if (tmp > 1) primes.push_back(tmp);

    auto walk_big = [&](long long d) -> void {
        while (d > 0) {
            long long step = min(d, 1000000000LL);
            cur = walk_cmd(step);
            total += step;
            d -= step;
        }
    };

    auto is_multiple_of_n = [&](long long d) -> bool {
        int startLabel = cur;
        walk_big(d);
        return cur == startLabel;
    };

    // Reduce candidate by removing redundant prime factors.
    for (long long p : primes) {
        while (candidate % p == 0) {
            long long d = candidate / p;
            if (d <= 0) break;
            if (q >= MAX_Q) break;
            if (is_multiple_of_n(d)) {
                candidate = d;
            } else {
                break;
            }
        }
    }

    guess_cmd(candidate);
    return 0;
}