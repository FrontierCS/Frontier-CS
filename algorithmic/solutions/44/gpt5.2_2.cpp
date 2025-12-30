#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N;
    if (!(cin >> N)) return 0;
    long long x, y;
    for (int i = 0; i < N; i++) cin >> x >> y; // coordinates not used

    int K = N + 1;
    cout << K << '\n';
    cout << 0 << '\n';
    for (int i = 1; i < N; i++) cout << i << '\n';
    cout << 0 << '\n';
    return 0;
}