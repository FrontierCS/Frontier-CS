#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    const int FULL_MASK = (1 << 12) - 1; // enough for n <= 2048 (values < 2048)
    vector<int> p(n, FULL_MASK);

    int x;
    for (int i = 0; i < n; ++i) {
        for (int j = i + 1; j < n; ++j) {
            if (!(cin >> x)) x = 0; // in case of incomplete input
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