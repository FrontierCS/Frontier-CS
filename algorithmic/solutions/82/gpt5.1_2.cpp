#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    vector<int> p(n);

    for (int i = 0; i < n; ++i) {
        int mask = -1;
        for (int j = 0; j < n; ++j) {
            int x;
            cin >> x;
            mask &= x;
        }
        p[i] = mask;
    }

    for (int i = 0; i < n; ++i) {
        if (i) cout << ' ';
        cout << p[i];
    }
    cout << '\n';

    return 0;
}