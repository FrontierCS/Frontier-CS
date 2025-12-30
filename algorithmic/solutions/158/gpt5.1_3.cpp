#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, K;
    if (!(cin >> N >> K)) return 0;
    vector<int> a(11);
    for (int d = 1; d <= 10; ++d) cin >> a[d];
    for (int i = 0; i < N; ++i) {
        long long x, y;
        cin >> x >> y;
    }

    // Trivial solution: no cuts
    cout << 0 << '\n';
    return 0;
}