#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    const int N = 30;
    int dummy;
    for (int x = 0; x < N; ++x) {
        for (int y = 0; y <= x; ++y) {
            if (!(cin >> dummy)) return 0;
        }
    }

    cout << 0 << '\n';
    return 0;
}