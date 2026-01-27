#include <bits/stdc++.h>
using namespace std;

string normalize(const string &s) {
    int i = 0;
    while (i + 1 < (int)s.size() && s[i] == '0') ++i;
    return s.substr(i);
}

int cmp(const string &a, const string &b) {
    if (a.size() != b.size()) return a.size() < b.size() ? -1 : 1;
    if (a == b) return 0;
    return a < b ? -1 : 1;
}

string subPositive(const string &a, const string &b) { // a >= b, both non-negative, no leading zeros
    string res;
    res.reserve(a.size());
    int i = (int)a.size() - 1;
    int j = (int)b.size() - 1;
    int borrow = 0;
    while (i >= 0 || j >= 0) {
        int da = (i >= 0) ? a[i] - '0' : 0;
        int db = (j >= 0) ? b[j] - '0' : 0;
        int x = da - db - borrow;
        if (x < 0) {
            x += 10;
            borrow = 1;
        } else {
            borrow = 0;
        }
        res.push_back(char('0' + x));
        --i; --j;
    }
    while (res.size() > 1 && res.back() == '0') res.pop_back();
    reverse(res.begin(), res.end());
    return res;
}

string absDiff(const string &a, const string &b) {
    int c = cmp(a, b);
    if (c == 0) return string("0");
    if (c > 0) return subPositive(a, b);
    else return subPositive(b, a);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    string W;
    if (!(cin >> n >> W)) return 0;
    W = normalize(W);

    vector<string> a(n);
    for (int i = 0; i < n; ++i) {
        cin >> a[i];
        a[i] = normalize(a[i]);
    }

    string bestDiff = W; // diff for choosing nothing (sum = 0)
    int bestIdx = -1;

    for (int i = 0; i < n; ++i) {
        string d = absDiff(a[i], W);
        if (cmp(d, bestDiff) < 0) {
            bestDiff = d;
            bestIdx = i;
        }
    }

    for (int i = 0; i < n; ++i) {
        int bit = (i == bestIdx) ? 1 : 0;
        if (i) cout << ' ';
        cout << bit;
    }
    cout << '\n';

    return 0;
}