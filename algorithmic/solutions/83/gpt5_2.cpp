#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if (!(cin >> n)) return 0;

    if (n <= 0) {
        cout << "\n";
        return 0;
    }

    vector<int> spf(n + 1, 0);
    vector<int> primes;
    for (int i = 2; i <= n; ++i) {
        if (spf[i] == 0) {
            spf[i] = i;
            primes.push_back(i);
        }
        for (int p : primes) {
            long long v = 1LL * p * i;
            if (v > n || p > spf[i]) break;
            spf[v] = p;
        }
    }

    vector<int8_t> sign(n + 1, 0);
    vector<int8_t> f(n + 1, 0);
    f[1] = 1;

    long long sum = 1;

    string out;
    out.reserve((size_t)3 * n + 10);
    out.push_back('1');
    if (n >= 2) out.push_back(' ');

    for (int i = 2; i <= n; ++i) {
        int p = spf[i];
        if (p == i) {
            if (sum > 0) sign[p] = -1;
            else if (sum < 0) sign[p] = 1;
            else sign[p] = -1;
        }
        f[i] = (int8_t)(f[i / p] * sign[p]);
        sum += f[i];

        if (f[i] == 1) out.push_back('1');
        else { out.push_back('-'); out.push_back('1'); }
        if (i < n) out.push_back(' ');
    }
    out.push_back('\n');
    cout << out;
    return 0;
}