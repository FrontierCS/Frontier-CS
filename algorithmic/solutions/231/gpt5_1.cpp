#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m, T;
    if (!(cin >> n >> m >> T)) return 0;
    for (int i = 0; i < m; ++i) {
        int a, b;
        if (!(cin >> a >> b)) return 0;
    }

    cout << 0 << "\n";
    cout.flush();

    for (int t = 0; t < T; ++t) {
        cout << "! 1\n";
        cout.flush();
        string resp;
        if (!(cin >> resp)) return 0;
        if (resp == "Wrong") return 0;
    }
    return 0;
}