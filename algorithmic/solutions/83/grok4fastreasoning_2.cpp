#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(NULL);
    int n;
    cin >> n;
    vector<int> f(n + 1, 0);
    f[1] = 1;
    vector<bool> is_comp(n + 1, false);
    vector<int> primes;
    for (int i = 2; i <= n; ++i) {
        if (!is_comp[i]) {
            primes.push_back(i);
            f[i] = -1;
        }
        for (size_t j = 0; j < primes.size(); ++j) {
            int p = primes[j];
            if (1LL * i * p > n) break;
            is_comp[i * p] = true;
            if (i % p == 0) {
                f[i * p] = -f[i];
                break;
            } else {
                f[i * p] = -f[i];
            }
        }
    }
    for (int i = 1; i <= n; ++i) {
        if (i > 1) cout << " ";
        cout << f[i];
    }
    cout << "\n";
    return 0;
}