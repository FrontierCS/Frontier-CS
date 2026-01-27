#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    const int MAXBITS = 11; // since n <= 2048, values are < 2^11
    int mask = (1 << MAXBITS) - 1;

    vector<int> p(n, mask);

    for (int i = 0; i < n; ++i) {
        for (int j = i + 1; j < n; ++j) {
            int x;
            cin >> x;
            p[i] &= x;
            p[j] &= x;
        }
    }

    for (int i = 0; i < n; ++i) {
        if (i) cout << ' ';
        cout << p[i];
    }
    cout << '\n';

    return 0;
}