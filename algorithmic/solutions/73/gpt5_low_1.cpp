#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    // Since interactive environment isn't available here, output identity permutation.
    cout << "1";
    for (int i = 1; i <= n; ++i) cout << " " << i;
    cout << "\n";
    cout.flush();
    return 0;
}