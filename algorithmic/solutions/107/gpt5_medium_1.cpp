#include <bits/stdc++.h>
using namespace std;

using u128 = __uint128_t;
using u64 = unsigned long long;

u64 ask(u64 q) {
    cout << "0 " << q << endl;
    cout.flush();
    u64 g;
    if (!(cin >> g)) exit(0);
    return g;
}

void answer(u64 ans) {
    cout << "1 " << ans << endl;
    cout.flush();
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int T;
    if (!(cin >> T)) return 0;

    // Sieve primes up to 1000
    const int B = 1000;
    vector<int> primes;
    vector<bool> is_composite(B + 1, false);
    for (int i = 2; i <= B; ++i) {
        if (!is_composite[i]) {
            primes.push_back(i);
            if ((long long)i * i <= B)
                for (int j = i * i; j <= B; j += i)
                    is_composite[j] = true;
        }
    }

    while (T--) {
        // Phase 1: detect which primes (<= 1000) divide X at least once
        vector<int> cand;
        u128 cur = 1;
        vector<int> group;
        auto flush_group = [&]() {
            if (group.empty()) return;
            u64 q = (u64)cur;
            u64 g = ask(q);
            for (int p : group) {
                if (g % p == 0) cand.push_back(p);
            }
            cur = 1;
            group.clear();
        };

        for (int p : primes) {
            if (cur * (u128)p > (u128)1e18) {
                flush_group();
            }
            cur *= (u128)p;
            group.push_back(p);
        }
        flush_group();

        // Phase 2: for each candidate prime, find exact exponent in X
        u64 d_small = 1;
        for (int p : cand) {
            // compute largest power of p not exceeding 1e18
            u128 pw = 1;
            while (pw * (u128)p <= (u128)1e18) pw *= (u128)p;
            u64 g = ask((u64)pw);
            int e = 0;
            while (g % p == 0) {
                g /= p;
                ++e;
            }
            d_small *= (u64)(e + 1);
        }

        // Final answer: multiply by 2 to guarantee relative error within 2,
        // and ensure at least 8 to satisfy absolute error bound for small d.
        u64 ans = max<u64>(8, 2 * d_small);
        answer(ans);
    }

    return 0;
}