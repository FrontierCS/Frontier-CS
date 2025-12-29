#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, K;
    if (!(cin >> N >> K)) return 0;
    vector<int> a(11);
    for (int i = 1; i <= 10; ++i) cin >> a[i];
    long long x, y;
    for (int i = 0; i < N; ++i) cin >> x >> y;

    cout << 0 << '\n';
    return 0;
}