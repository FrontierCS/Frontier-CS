#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if (!(cin >> n)) return 0;
    for (int i = 1; i <= n; ++i) {
        string s(i, 'X');
        s.push_back('O');
        cout << s << '\n';
    }
    cout.flush();

    int q;
    if (!(cin >> q)) return 0;
    for (int i = 0; i < q; ++i) {
        long long p;
        cin >> p;
        cout << 1 << ' ' << 1 << '\n';
        cout.flush();
    }

    return 0;
}