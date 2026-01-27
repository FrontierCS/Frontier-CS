#include <bits/stdc++.h>
using namespace std;

static const long long MOD = 1000000007LL;

long long modpow(long long a, long long e) {
    long long r = 1 % MOD;
    a %= MOD;
    while (e > 0) {
        if (e & 1) r = (__int128)r * a % MOD;
        a = (__int128)a * a % MOD;
        e >>= 1;
    }
    return r;
}

long long inv(long long a) {
    return modpow((a % MOD + MOD) % MOD, MOD - 2);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    // Precompute a sequence s such that s_{k+1} = s_k^2 / (s_k - 1), avoiding s_k = 1
    vector<long long> s(n + 1, 0);
    vector<long long> ainv(n + 1, 0); // ainv[j] = s[j-1]/(s[j-1]-1) for j>=1
    long long c = 2;
    auto try_build = [&](long long c0) -> bool {
        s[0] = c0;
        if (s[0] == 1) return false;
        for (int k = 1; k <= n; ++k) {
            if (s[k-1] == 1) return false;
            long long denom = (s[k-1] - 1 + MOD) % MOD;
            long long invden = inv(denom);
            ainv[k] = (s[k-1] * invden) % MOD;          // a_k to make invariance at step k
            s[k] = (__int128)s[k-1] * s[k-1] % MOD;
            s[k] = (__int128)s[k] * invden % MOD;       // s_k = s_{k-1}^2 / (s_{k-1}-1)
            if (k < n && s[k] == 1) return false;       // ensure s_k != 1 for k <= n-1
        }
        return true;
    };

    while (!try_build(c)) {
        c++;
        if (c >= MOD) c = 2; // wrap, though this should never be needed
    }

    vector<int> op(n + 1, 0); // 1..n, 0 for '+', 1 for 'x'
    long long suffix_plus = 0; // number of '+' in positions > i, known when sweeping from right

    for (int i = n; i >= 1; --i) {
        // Choose u for a_i avoiding degeneracy: (s[i-1]-1)*(u-1) != 1 (mod MOD)
        long long x = s[i-1];
        long long forbidden = (1 + inv((x - 1 + MOD) % MOD)) % MOD; // u != forbidden
        long long u = 2;
        while (u == 0 || u == 1 || u == forbidden) {
            u++;
            if (u >= MOD) u = 2;
        }

        // Build query vector
        vector<long long> A(n + 1, 1);
        A[0] = c;
        for (int j = 1; j <= n; ++j) {
            if (j < i) A[j] = ainv[j];
            else if (j == i) A[j] = u;
            else A[j] = 1;
        }

        cout << "?";
        for (int j = 0; j <= n; ++j) {
            long long val = (A[j] % MOD + MOD) % MOD;
            if (val == 0) val = 1; // ensure within [1, MOD-1], though should not happen
            cout << " " << val;
        }
        cout << endl;
        cout.flush();

        long long r;
        if (!(cin >> r)) return 0;
        r %= MOD;

        long long plusRes = ( (x + u) % MOD + suffix_plus ) % MOD;
        long long mulRes  = ( (__int128)x * u % MOD + suffix_plus ) % MOD;

        if (r == plusRes) {
            op[i] = 0;
        } else if (r == mulRes) {
            op[i] = 1;
        } else {
            // Rare fallback: pick another u and retry once
            long long u2 = u + 1;
            while (u2 == 0 || u2 == 1 || u2 == forbidden || u2 == u) {
                u2++;
                if (u2 >= MOD) u2 = 2;
            }
            A[i] = u2;
            cout << "?";
            for (int j = 0; j <= n; ++j) {
                long long val = (A[j] % MOD + MOD) % MOD;
                if (val == 0) val = 1;
                cout << " " << val;
            }
            cout << endl;
            cout.flush();

            if (!(cin >> r)) return 0;
            r %= MOD;

            plusRes = ( (x + u2) % MOD + suffix_plus ) % MOD;
            mulRes  = ( (__int128)x * u2 % MOD + suffix_plus ) % MOD;

            if (r == plusRes) op[i] = 0;
            else op[i] = 1; // assume correctness
        }

        if (op[i] == 0) suffix_plus++;
    }

    cout << "!";
    for (int i = 1; i <= n; ++i) {
        cout << " " << op[i];
    }
    cout << endl;
    cout.flush();

    return 0;
}