#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N;
    if (!(cin >> N)) return 0;

    string s;
    s.reserve(N);

    for (int p = 0; p < N; ++p) {
        int m = p + 3; // states: 0..p (counter), p+1 (bit=0), p+2 (bit=1)
        vector<int> a(m), b(m);

        for (int x = 0; x < p; ++x) a[x] = b[x] = x + 1;

        a[p] = p + 1;
        b[p] = p + 2;

        a[p + 1] = b[p + 1] = p + 1;
        a[p + 2] = b[p + 2] = p + 2;

        cout << 1 << ' ' << m;
        for (int i = 0; i < m; ++i) cout << ' ' << a[i];
        for (int i = 0; i < m; ++i) cout << ' ' << b[i];
        cout << '\n';
        cout.flush();

        int x;
        if (!(cin >> x)) return 0;

        s.push_back((x == p + 2) ? '1' : '0');
    }

    cout << 0 << ' ' << s << '\n';
    cout.flush();
    return 0;
}