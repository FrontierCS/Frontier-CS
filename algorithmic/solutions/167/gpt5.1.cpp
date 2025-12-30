#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N;
    if (!(cin >> N)) return 0;
    int total = 2 * N;
    for (int i = 0; i < total; ++i) {
        int x, y;
        cin >> x >> y;
    }

    cout << 4 << '\n';
    cout << 0 << ' ' << 0 << '\n';
    cout << 100000 << ' ' << 0 << '\n';
    cout << 100000 << ' ' << 100000 << '\n';
    cout << 0 << ' ' << 100000 << '\n';

    return 0;
}