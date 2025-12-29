#include <bits/stdc++.h>
using namespace std;

static const long long MAX_X = 1000000000LL;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    auto walk = [&](long long x)->long long{
        cout << "walk " << x << "\n" << flush;
        long long v;
        if (!(cin >> v)) exit(0);
        return v;
    };
    auto guess = [&](long long g){
        cout << "guess " << g << "\n" << flush;
        exit(0);
    };

    // Get starting label
    long long curLabel = walk(0);
    long long totalSteps = 0;

    unordered_map<long long, long long> lastSeen;
    lastSeen.reserve(300000);
    lastSeen.max_load_factor(0.7f);
    lastSeen[curLabel] = 0;

    // Random generator
    std::mt19937_64 rng((unsigned)chrono::high_resolution_clock::now().time_since_epoch().count());
    // Keep step size small to keep the first collision difference manageable (<= 1e9)
    const int B = 1000;
    std::uniform_int_distribution<int> dist(1, B);

    long long c = -1;
    const int MAX_WALKS = 190000; // leave budget for factor tests

    for (int i = 0; i < MAX_WALKS; ++i) {
        long long x = dist(rng);
        curLabel = walk(x);
        totalSteps += x;
        auto it = lastSeen.find(curLabel);
        if (it != lastSeen.end()) {
            c = totalSteps - it->second;
            if (c <= 0) c = 1; // safety
            break;
        } else {
            lastSeen[curLabel] = totalSteps;
        }
    }

    if (c == -1) {
        // Fallback: no collision found within budget; guess 1 (will likely be wrong, but protocol demands a guess)
        guess(1);
        return 0;
    }

    // Factorization by trial division (c is small due to small step sizes)
    vector<pair<long long,int>> factors;
    auto factorize = [&](long long n){
        vector<pair<long long,int>> res;
        int cnt = 0;
        while ((n % 2) == 0) { n /= 2; cnt++; }
        if (cnt) res.push_back({2, cnt});
        for (long long p = 3; p * p <= n; p += 2) {
            if (n % p == 0) {
                int k = 0;
                while (n % p == 0) { n /= p; ++k; }
                res.push_back({p, k});
            }
        }
        if (n > 1) res.push_back({n, 1});
        return res;
    };

    factors = factorize(c);

    auto walk_large = [&](long long x)->long long{
        if (x == 0) return curLabel;
        while (x > 0) {
            long long step = min(x, MAX_X);
            curLabel = walk(step);
            x -= step;
        }
        return curLabel;
    };

    long long candidate = c; // multiple of n
    // Use divisibility testing with candidate to reduce it to n
    for (auto &pr : factors) {
        long long p = pr.first;
        int e = pr.second;
        for (int i = 0; i < e; ++i) {
            long long d = candidate / p;
            // Test if moving by d keeps label same (i.e., d is multiple of n)
            long long base = curLabel;
            walk_large(d);
            if (curLabel == base) {
                candidate = d; // divisible, we stay on the same vertex
                // continue dividing by p if possible
            } else {
                // Not divisible; return to base by walking candidate - d (since candidate is multiple of n)
                walk_large(candidate - d);
                // Now curLabel should be base again
            }
        }
    }

    if (candidate < 1) candidate = 1;
    if (candidate > 1000000000LL) {
        // Clamp to constraints just in case
        candidate = 1000000000LL;
    }
    guess(candidate);
    return 0;
}