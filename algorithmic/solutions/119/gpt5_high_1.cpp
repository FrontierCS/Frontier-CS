#include <bits/stdc++.h>
using namespace std;

const long long MOD = 1000000007LL;

long long query(const vector<long long>& a) {
    cout << "?";
    for (size_t i = 0; i < a.size(); ++i) {
        long long x = a[i] % MOD;
        if (x < 1) x += MOD; // Ensure in [1, MOD-1] if needed
        cout << " " << x;
    }
    cout << endl;
    cout.flush();
    long long res;
    if (!(cin >> res)) exit(0);
    res %= MOD;
    if (res < 0) res += MOD;
    return res;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    vector<int> ans(n, -1); // 0 for '+', 1 for '×'
    vector<long long> a(n + 1, 1);

    // First query: a0=1, a1=2, others=1 to obtain s (# of plus)
    a[0] = 1;
    if (n >= 1) a[1] = 2;
    long long R1 = query(a);
    if (n >= 1) a[1] = 1;

    long long s = (R1 - 2) % MOD;
    if (s < 0) s += MOD;

    // Queries for i = 2..n with a0 = 2, ai = 2, others = 1
    const long long C = 2;
    long long baseC = (C + s) % MOD;

    for (int i = 2; i <= n; ++i) {
        a[0] = C;
        a[i] = 2;
        long long Ri = query(a);
        long long Di = (Ri - baseC) % MOD;
        if (Di < 0) Di += MOD;
        if (Di == 1) ans[i - 1] = 0; // '+'
        else ans[i - 1] = 1;         // '×'
        a[i] = 1;
    }

    // Determine op1 using total s and the rest
    int rest_plus = 0;
    for (int i = 2; i <= n; ++i) {
        if (ans[i - 1] == 0) ++rest_plus;
    }
    long long op1_plus = (s - rest_plus);
    ans[0] = (op1_plus == 1 ? 0 : 1);

    cout << "!";
    for (int i = 0; i < n; ++i) {
        cout << " " << ans[i];
    }
    cout << endl;
    cout.flush();

    return 0;
}