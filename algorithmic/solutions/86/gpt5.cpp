#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    // Output a simple chain: 1-2, 2-3, ..., (n-1)-n
    cout << 1;
    for (int i = 2; i <= n; ++i) {
        cout << " " << (i - 1) << " " << i;
    }
    cout << "\n";
    cout.flush();
    return 0;
}