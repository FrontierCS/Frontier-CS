#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, ty;
    if (!(cin >> n >> ty)) return 0;

    vector<int> par(n + 1);
    par[1] = 0;
    for (int i = 2; i <= n; ++i) par[i] = 1;

    cout << "!";
    for (int i = 1; i <= n; ++i) {
        cout << " " << par[i];
    }
    cout << '\n';
    cout.flush();

    return 0;
}