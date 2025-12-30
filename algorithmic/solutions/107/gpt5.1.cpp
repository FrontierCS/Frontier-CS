#include <bits/stdc++.h>
using namespace std;

const long long MAX_X = 1000000000LL;
const long long MAX_Q = 1000000000000000000LL;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int T;
    if (!(cin >> T)) return 0;

    // Precompute primes up to 1000
    const int B0 = 1000;
    vector<int> primes;
    vector<bool> isComp(B0 + 1, false);
    for (int i = 2; i <= B0; ++i) {
        if (!isComp[i]) {
            primes.push_back(i);
            if ((long long)i * i <= B0) {
                for (int j = i * i; j <= B0; j += i) isComp[j] = true;
            }
        }
    }
    int P = (int)primes.size();

    // Precompute max exponent and corresponding power <= 1e9 for each prime
    vector<int> emax(P);
    vector<long long> powMax(P);
    for (int i = 0; i < P; ++i) {
        int p = primes[i];
        long long val = 1;
        int e = 0;
        while (val * p <= MAX_X) {
            val *= p;
            ++e;
        }
        emax[i] = e;
        powMax[i] = val; // p^emax[i] <= 1e9
    }

    // Build groups of primes so that product of powMax in each group <= 1e18
    vector<vector<int>> groups;
    {
        vector<int> curGroup;
        __int128 curProd = 1;
        for (int i = 0; i < P; ++i) {
            long long val = powMax[i];
            if (curGroup.empty()) {
                curGroup.push_back(i);
                curProd = val;
            } else {
                __int128 nxt = curProd * (__int128)val;
                if (nxt > (__int128)MAX_Q) {
                    groups.push_back(curGroup);
                    curGroup.clear();
                    curGroup.push_back(i);
                    curProd = val;
                } else {
                    curGroup.push_back(i);
                    curProd = nxt;
                }
            }
        }
        if (!curGroup.empty()) groups.push_back(curGroup);
    }

    while (T--) {
        vector<int> expP(P, 0);

        // Query each group
        for (const auto &grp : groups) {
            __int128 Q128 = 1;
            for (int idx : grp) {
                Q128 *= (__int128)powMax[idx];
            }
            long long Q = (long long)Q128;

            cout << "0 " << Q << '\n';
            cout.flush();

            long long g;
            if (!(cin >> g)) return 0;

            long long r = g;
            for (int idx : grp) {
                int p = primes[idx];
                int cnt = 0;
                while (r % p == 0) {
                    r /= p;
                    ++cnt;
                }
                if (cnt > 0) expP[idx] = cnt;
            }
        }

        long long D_small = 1;
        for (int i = 0; i < P; ++i) {
            if (expP[i] > 0) {
                D_small *= (expP[i] + 1);
            }
        }

        long long ans = D_small * 2; // adjust for possible large primes (>1000)
        cout << "1 " << ans << '\n';
        cout.flush();
    }

    return 0;
}