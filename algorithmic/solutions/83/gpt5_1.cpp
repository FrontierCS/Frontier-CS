#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) n = 1000000;

    vector<int> spf(n + 1, 0);
    for (int i = 2; i <= n; ++i) {
        if (spf[i] == 0) {
            spf[i] = i;
            if (1LL * i * i <= n) {
                for (long long j = 1LL * i * i; j <= n; j += i) {
                    if (spf[j] == 0) spf[j] = i;
                }
            }
        }
    }

    vector<int8_t> f(n + 1, 1);
    for (int i = 2; i <= n; ++i) f[i] = -f[i / spf[i]];

    string out;
    out.reserve(n * 3 + 2);
    for (int i = 1; i <= n; ++i) {
        if (f[i] == 1) out.push_back('1');
        else { out.push_back('-'); out.push_back('1'); }
        if (i < n) out.push_back(' ');
    }
    out.push_back('\n');
    cout << out;
    return 0;
}