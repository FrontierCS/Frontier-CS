#include <bits/stdc++.h>
using namespace std;

const long long LIMQ = 1000000000000000000LL; // 1e18
const long long LIMX = 1000000000LL;          // 1e9

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    // Precompute primes up to 1000
    const int MAXP = 1000;
    vector<int> primes;
    vector<bool> is_prime(MAXP + 1, true);
    is_prime[0] = is_prime[1] = false;
    for (int i = 2; i <= MAXP; ++i) {
        if (is_prime[i]) {
            primes.push_back(i);
            if ((long long)i * i <= MAXP) {
                for (int j = i * i; j <= MAXP; j += i)
                    is_prime[j] = false;
            }
        }
    }

    // Group primes so that product in each group <= 1e18
    vector<vector<int>> groups;
    {
        vector<int> curGroup;
        long long curProd = 1;
        for (int p : primes) {
            if ( (__int128)curProd * p > LIMQ ) {
                if (!curGroup.empty()) {
                    groups.push_back(curGroup);
                    curGroup.clear();
                }
                curProd = 1;
            }
            curGroup.push_back(p);
            curProd *= p;
        }
        if (!curGroup.empty()) groups.push_back(curGroup);
    }

    int T;
    if (!(cin >> T)) return 0;

    auto ask = [&](long long Q) -> long long {
        cout << "0 " << Q << '\n';
        cout.flush();
        long long g;
        if (!(cin >> g)) exit(0);
        return g;
    };

    for (int tc = 0; tc < T; ++tc) {
        vector<int> smallFactors;

        // Stage 1: find which primes <= 1000 divide X
        for (const auto &grp : groups) {
            long long Q = 1;
            for (int p : grp) Q *= p;
            long long g = ask(Q);
            for (int p : grp) {
                if (g % p == 0) smallFactors.push_back(p);
            }
        }

        // Stage 2: determine exponent for each found small prime
        long long d_small = 1;
        for (int p : smallFactors) {
            long long Q = 1;
            while (Q * p <= LIMX) Q *= p;
            long long g = ask(Q);
            int cnt = 0;
            while (g % p == 0) {
                g /= p;
                ++cnt;
            }
            d_small *= (cnt + 1);
        }

        long long ans = d_small * 2; // d_large in {1,2,3,4}, so 2*d_small keeps ratio in [0.5,2]

        cout << "1 " << ans << '\n';
        cout.flush();
    }

    return 0;
}