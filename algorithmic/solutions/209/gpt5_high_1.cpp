#include <bits/stdc++.h>
using namespace std;

static string to_string_int128(__int128 x) {
    if (x == 0) return "0";
    bool neg = false;
    if (x < 0) { neg = true; x = -x; }
    string s;
    while (x > 0) {
        int digit = int(x % 10);
        s.push_back('0' + digit);
        x /= 10;
    }
    if (neg) s.push_back('-');
    reverse(s.begin(), s.end());
    return s;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int h;
    if (!(cin >> h)) return 0;

    long long n = (1LL << h) - 1;
    int D = 2 * h - 2;

    __int128 total = 0;

    for (long long u = 1; u <= n; ++u) {
        for (int d = 1; d <= D; ++d) {
            cout << "? " << u << ' ' << d << endl;
            cout.flush();
            long long r;
            if (!(cin >> r)) return 0;
            if (r == -1) return 0; // in case of interactor error
            total += r;
        }
    }

    __int128 denom = (__int128)(n - 1);
    __int128 T = (denom == 0 ? 0 : total / denom);

    cout << "! " << to_string_int128(T) << endl;
    cout.flush();

    return 0;
}