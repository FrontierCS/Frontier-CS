#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    long long n;
    if (!(cin >> n)) return 0;

    string s;
    streambuf* sb = cin.rdbuf();
    while (sb->in_avail() > 0) {
        char c = sb->sbumpc();
        if (c == '(' || c == ')') s.push_back(c);
    }

    if ((int)s.size() >= n) {
        s = s.substr(0, n);
    } else if ((int)s.size() < n) {
        if (s.empty()) {
            int half = n / 2;
            s.assign(half, '(');
            s.append(n - half, ')');
        } else {
            while ((int)s.size() < n) s.push_back(')');
        }
    }

    cout << s;
    return 0;
}