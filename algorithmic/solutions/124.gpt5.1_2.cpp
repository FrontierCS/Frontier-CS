#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    // Trivial permutation: 1 2 3 ... n (p1 = 1 <= n/2 since n >= 2)
    cout << "!";
    for (int i = 1; i <= n; ++i) {
        cout << " " << i;
    }
    cout << "\n";
    cout.flush();

    return 0;
}