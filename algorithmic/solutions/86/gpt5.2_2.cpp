#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    // Fallback non-interactive / placeholder: output a star centered at 1.
    // (In the real interactive setting, you should replace this with actual querying logic.)
    cout << 1;
    for (int i = 2; i <= n; i++) {
        cout << ' ' << 1 << ' ' << i;
    }
    cout << "\n";
    cout.flush();
    return 0;
}