#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N;
    if (!(cin >> N)) return 0;
    long long x, y;
    for (int i = 0; i < 2 * N; i++) cin >> x >> y;

    cout << 4 << "\n";
    cout << "0 0\n";
    cout << "100000 0\n";
    cout << "100000 100000\n";
    cout << "0 100000\n";

    return 0;
}