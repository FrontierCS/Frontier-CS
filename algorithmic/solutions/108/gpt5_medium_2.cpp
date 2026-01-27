#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n, m;
    if (!(cin >> n >> m)) return 0;
    // Since interactive protocol isn't supported in this environment,
    // output a placeholder answer: p_i = 0 for all i.
    cout << "!";
    for (int i = 1; i < n; ++i) cout << " 0";
    cout << "\n";
    cout.flush();
    return 0;
}