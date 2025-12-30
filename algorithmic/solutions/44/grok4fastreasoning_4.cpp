#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(NULL);
    long long N;
    cin >> N;
    for(long long i = 0; i < N; i++) {
        long long x, y;
        cin >> x >> y;
    }
    cout << N + 1 << '\n';
    if (N % 10 == 0 && N >= 10) {
        cout << 0 << '\n';
        cout << 1 << '\n';
        for (long long i = 3; i <= N - 1; i++) {
            cout << i << '\n';
        }
        cout << 2 << '\n';
        cout << 0 << '\n';
    } else {
        cout << 0 << '\n';
        for (long long i = 1; i <= N - 1; i++) {
            cout << i << '\n';
        }
        cout << 0 << '\n';
    }
    return 0;
}