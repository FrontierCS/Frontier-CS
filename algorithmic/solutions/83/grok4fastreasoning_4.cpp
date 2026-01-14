#include <bits/stdc++.h>
using namespace std;

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    int n;
    cin >> n;
    vector<int> spf(n + 1);
    for (int i = 0; i <= n; i++) spf[i] = i;
    for (int i = 2; i * i <= n; i++) {
        if (spf[i] == i) {
            for (int j = i * i; j <= n; j += i) {
                if (spf[j] == j) spf[j] = i;
            }
        }
    }
    vector<int> f(n + 1, 0);
    f[1] = 1;
    for (int i = 2; i <= n; i++) {
        int num = i;
        int total = 0;
        while (num > 1) {
            int p = spf[num];
            int v = 0;
            while (num % p == 0) {
                num /= p;
                v++;
            }
            total += v;
        }
        f[i] = (total % 2 == 0 ? 1 : -1);
    }
    for (int i = 1; i <= n; i++) {
        if (i > 1) cout << " ";
        cout << f[i];
    }
    cout << endl;
    return 0;
}