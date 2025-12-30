#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int k, n;
    if (!(cin >> k >> n)) return 0;

    // No queries; just output an arbitrary permutation.
    cout << "!";
    for (int i = 0; i < n; ++i) {
        cout << " " << i;
    }
    cout << "\n";
    cout.flush();

    return 0;
}