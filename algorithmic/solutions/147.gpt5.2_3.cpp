#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    cin >> n;
    for (int i = 0; i < n; i++) {
        int x, y;
        long long r;
        cin >> x >> y >> r;
        cout << x << ' ' << y << ' ' << x + 1 << ' ' << y + 1 << "\n";
    }
    return 0;
}