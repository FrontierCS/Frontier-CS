#include <bits/stdc++.h>
using namespace std;

static inline void appendInt(string &s, int x) {
    if (x == 0) {
        s.push_back('0');
        return;
    }
    char buf[16];
    int n = 0;
    while (x > 0) {
        buf[n++] = char('0' + (x % 10));
        x /= 10;
    }
    for (int i = n - 1; i >= 0; --i) s.push_back(buf[i]);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N;
    if (!(cin >> N)) return 0;

    string ans(N, '0');

    for (int i = 0; i < N; i++) {
        int m = i + 3;

        string out;
        out.reserve((2 * m + 2) * 6);

        out.push_back('1');
        out.push_back(' ');
        appendInt(out, m);
        out.push_back(' ');

        // sequence a
        for (int j = 0; j < m; j++) {
            int val;
            if (j < i) val = j + 1;
            else if (j == i) val = i + 1;
            else val = j; // absorbing/self
            appendInt(out, val);
            out.push_back(' ');
        }

        // sequence b
        for (int j = 0; j < m; j++) {
            int val;
            if (j < i) val = j + 1;
            else if (j == i) val = i + 2;
            else val = j; // absorbing/self
            appendInt(out, val);
            if (j + 1 < m) out.push_back(' ');
        }

        out.push_back('\n');
        cout << out;
        cout.flush();

        int x;
        if (!(cin >> x)) return 0;
        if (x < 0) return 0;

        ans[i] = (x == i + 1) ? '0' : '1';
    }

    cout << "0 " << ans << '\n';
    cout.flush();
    return 0;
}