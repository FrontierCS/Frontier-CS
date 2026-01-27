#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    vector<int> spf(n + 1);
    for (int i = 2; i <= n; ++i) {
        if (spf[i] == 0) {
            spf[i] = i;
            if (1LL * i * i <= n) {
                for (int j = i * i; j <= n; j += i) {
                    if (spf[j] == 0) spf[j] = i;
                }
            }
        }
    }

    vector<int> f(n + 1);
    f[1] = 1;
    for (int i = 2; i <= n; ++i) {
        int p = spf[i];
        if (p == 0) p = i;
        f[i] = -f[i / p];
    }

    for (int i = 1; i <= n; ++i) {
        if (i > 1) cout << ' ';
        cout << f[i];
    }
    cout << '\n';

    return 0;
}