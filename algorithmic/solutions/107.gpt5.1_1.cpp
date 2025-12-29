#include <bits/stdc++.h>
using namespace std;

using int64 = long long;
const long long LIMIT = 1000000000000000000LL; // 1e18
const int MAXP = 1000;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    // Sieve primes up to MAXP
    vector<int> primes;
    vector<bool> is_composite(MAXP + 1, false);
    for (int i = 2; i <= MAXP; ++i) {
        if (!is_composite[i]) {
            primes.push_back(i);
            if (1LL * i * i <= MAXP) {
                for (long long j = 1LL * i * i; j <= MAXP; j += i)
                    is_composite[(int)j] = true;
            }
        }
    }

    // Group primes so that product of primes in each group <= LIMIT
    vector<vector<int>> groups;
    vector<long long> groupProd;
    {
        long long curProd = 1;
        vector<int> cur;
        for (int p : primes) {
            if (curProd > LIMIT / p) {
                groups.push_back(cur);
                groupProd.push_back(curProd);
                cur.clear();
                curProd = 1;
            }
            cur.push_back(p);
            curProd *= p;
        }
        if (!cur.empty()) {
            groups.push_back(cur);
            groupProd.push_back(curProd);
        }
    }

    int T;
    if (!(cin >> T)) return 0;

    while (T--) {
        vector<int> cand;

        // Stage 1: detect which primes <= MAXP divide X
        for (size_t gi = 0; gi < groups.size(); ++gi) {
            long long Q = groupProd[gi];
            cout << "0 " << Q << endl;
            cout.flush();

            long long g;
            if (!(cin >> g)) return 0;
            if (g == -1) return 0; // error from interactor

            for (int p : groups[gi]) {
                if (g % p == 0) cand.push_back(p);
            }
        }

        // Stage 2: find exponents for detected small primes
        long long d_small = 1;
        for (int p : cand) {
            long long cur = 1;
            while (cur <= LIMIT / p) cur *= p;

            cout << "0 " << cur << endl;
            cout.flush();

            long long g;
            if (!(cin >> g)) return 0;
            if (g == -1) return 0;

            int exp_cnt = 0;
            while (g % p == 0) {
                g /= p;
                ++exp_cnt;
            }
            d_small *= (exp_cnt + 1);
        }

        // Leftover factor has all primes > MAXP, hence its divisor count is in {1,2,3,4}
        // We approximate it as 2, guaranteeing relative error within [0.5, 2].
        long long ans = d_small * 2;

        cout << "1 " << ans << endl;
        cout.flush();
    }

    return 0;
}