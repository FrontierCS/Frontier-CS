#include <bits/stdc++.h>
#include <boost/multiprecision/cpp_int.hpp>

using namespace std;
using boost::multiprecision::cpp_int;

static inline cpp_int parseBig(const string& s) {
    cpp_int x = 0;
    for (char c : s) {
        if (c >= '0' && c <= '9') {
            x *= 10;
            x += (c - '0');
        }
    }
    return x;
}

static inline cpp_int abs_diff(const cpp_int& a, const cpp_int& b) {
    return (a >= b) ? (a - b) : (b - a);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    string Wstr;
    if (!(cin >> n >> Wstr)) return 0;

    cpp_int W = parseBig(Wstr);
    vector<cpp_int> a(n);
    for (int i = 0; i < n; i++) {
        string s;
        cin >> s;
        a[i] = parseBig(s);
    }

    vector<int> idx(n);
    iota(idx.begin(), idx.end(), 0);
    sort(idx.begin(), idx.end(), [&](int i, int j) {
        return a[i] > a[j];
    });

    vector<int> b(n, 0);
    cpp_int S = 0;
    cpp_int bestDiff = abs_diff(W, S);

    for (int id : idx) {
        cpp_int S2 = S + a[id];
        cpp_int d2 = abs_diff(W, S2);
        if (d2 < bestDiff) {
            b[id] = 1;
            S = std::move(S2);
            bestDiff = std::move(d2);
        }
    }

    // Simple local improvement pass (toggle each element if it improves)
    for (int i = 0; i < n; i++) {
        if (b[i] == 0) {
            cpp_int S2 = S + a[i];
            cpp_int d2 = abs_diff(W, S2);
            if (d2 < bestDiff) {
                b[i] = 1;
                S = std::move(S2);
                bestDiff = std::move(d2);
            }
        } else {
            cpp_int S2 = S - a[i];
            cpp_int d2 = abs_diff(W, S2);
            if (d2 < bestDiff) {
                b[i] = 0;
                S = std::move(S2);
                bestDiff = std::move(d2);
            }
        }
    }

    for (int i = 0; i < n; i++) {
        if (i) cout << ' ';
        cout << b[i];
    }
    cout << '\n';
    return 0;
}