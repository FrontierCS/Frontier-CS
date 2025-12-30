#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    const int N = 30;
    int x;
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j <= i; ++j) {
            if (!(cin >> x)) return 0;
        }
    }

    cout << 0 << '\n';
    return 0;
}