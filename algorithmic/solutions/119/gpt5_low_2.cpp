#include <bits/stdc++.h>
using namespace std;

static const long long MOD = 1000000007LL;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if(!(cin >> n)) return 0;

    auto ask = [&](const vector<long long>& a)->long long{
        cout << "?";
        for (int i = 0; i <= n; ++i) {
            long long x = a[i] % MOD;
            if (x <= 0) x += MOD;
            if (x == 0) x = 1; // ensure in [1, MOD-1], but our construction uses only 1 or 2
            cout << " " << x;
        }
        cout << "\n" << flush;
        long long r;
        if(!(cin >> r)) exit(0);
        return r % MOD;
    };

    vector<int> sop(n+1, -1); // 1..n; 0 for '+', 1 for 'x'
    long long total_plus = 0;

    // Query 1: determine total_plus using a0=2, a1=1, others 1
    {
        vector<long long> a(n+1, 1);
        a[0] = 2; // A
        a[1] = 1; // x=1
        long long res = ask(a);
        // res = total_plus + A
        long long tp = (res - 2) % MOD;
        if (tp < 0) tp += MOD;
        // Map to [0..n]
        if (tp > n) {
            // In our construction, res should be small; however guard just in case
            tp %= (n+1);
        }
        total_plus = tp;
    }

    // Determine s2..sn
    int pref_known = 0; // sum of s_i for i=2..t-1
    for (int t = 2; t <= n; ++t) {
        vector<long long> a(n+1, 1);
        a[0] = 2;
        a[1] = 2; // ensures v1 = 4 regardless of s1

        for (int i = 2; i < t; ++i) {
            if (sop[i] == 0) a[i] = 1; // '+'
            else if (sop[i] == 1) a[i] = 2; // 'x'
            else a[i] = 1; // shouldn't happen
        }
        a[t] = 2;
        for (int j = t+1; j <= n; ++j) a[j] = 1;

        long long res = ask(a);

        // Compute V starting from v1=4
        long long V = 4 % MOD;
        for (int i = 2; i < t; ++i) {
            if (sop[i] == 0) {
                V = (V + 1) % MOD;
            } else {
                V = (V * 2) % MOD;
            }
        }

        // K' = res - (total_plus - sum_known)
        long long Kp = (res - ((total_plus - pref_known) % MOD) + MOD) % MOD;

        long long d1 = (Kp - ((V + 1) % MOD) + MOD) % MOD;
        // '+' if d1 in {0,1}, else 'x'
        if (d1 == 0 || d1 == 1) {
            sop[t] = 0;
            pref_known += 1;
        } else {
            sop[t] = 1;
        }
    }

    // Deduce s1 = total_plus - sum_{i=2..n} s_i
    int sum_rest = 0;
    for (int i = 2; i <= n; ++i) if (sop[i] == 0) sum_rest++;
    long long s1 = (total_plus - sum_rest) % MOD;
    if (s1 < 0) s1 += MOD;
    if (s1 != 0) sop[1] = 0; // '+' if 1
    else sop[1] = 1;        // 'x' if 0

    // Output result
    cout << "!";
    for (int i = 1; i <= n; ++i) {
        int oi = (sop[i] == 0 ? 0 : 1);
        cout << " " << oi;
    }
    cout << "\n" << flush;

    return 0;
}