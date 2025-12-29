#include <bits/stdc++.h>
using namespace std;

static const long long MOD = 1000000007LL;

static long long ask(const vector<long long>& a) {
    cout << "?";
    for (long long v : a) cout << " " << v;
    cout << '\n';
    cout.flush();

    long long r;
    if (!(cin >> r)) exit(0);
    if (r == -1) exit(0);
    return r;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    cin >> n;

    vector<int> ans(n + 1, 0); // 0 = '+', 1 = '*'
    vector<long long> primes = {2, 3, 5, 7, 11, 13, 17, 19, 23};
    const int B = (int)primes.size();

    for (int l = 1; l <= n; l += B) {
        int r = min(n, l + B - 1);

        vector<long long> base(n + 1, 1);
        for (int i = l; i <= r; i++) base[i] = primes[i - l];

        vector<long long> q = base;
        q[0] = 1;
        long long res1 = ask(q);
        q[0] = 2;
        long long res2 = ask(q);

        long long coeff = (res2 - res1) % MOD;
        if (coeff < 0) coeff += MOD;

        for (int i = l; i <= r; i++) {
            long long p = base[i];
            ans[i] = (coeff % p == 0) ? 1 : 0;
        }
    }

    cout << "!";
    for (int i = 1; i <= n; i++) cout << " " << ans[i];
    cout << '\n';
    cout.flush();
    return 0;
}