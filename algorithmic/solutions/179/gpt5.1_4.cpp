#include <bits/stdc++.h>
using namespace std;

string normalize(const string &s) {
    int i = 0;
    while (i + 1 < (int)s.size() && s[i] == '0') ++i;
    return s.substr(i);
}

int cmpBig(const string &a, const string &b) {
    if (a.size() != b.size()) return a.size() < b.size() ? -1 : 1;
    if (a == b) return 0;
    return a < b ? -1 : 1;
}

string subBig(const string &a, const string &b) { // a >= b, non-negative
    int n = a.size(), m = b.size();
    string res(n, '0');
    int carry = 0;
    int i = n - 1, j = m - 1, k = n - 1;
    while (i >= 0) {
        int da = a[i] - '0';
        int db = (j >= 0 ? b[j] - '0' : 0);
        int v = da - db - carry;
        if (v < 0) {
            v += 10;
            carry = 1;
        } else {
            carry = 0;
        }
        res[k] = char('0' + v);
        --i; --j; --k;
    }
    int pos = 0;
    while (pos + 1 < (int)res.size() && res[pos] == '0') ++pos;
    if (pos > 0) res.erase(0, pos);
    return res;
}

string absDiffBig(const string &a, const string &b) { // both normalized
    int c = cmpBig(a, b);
    if (c == 0) return "0";
    if (c > 0) return subBig(a, b);
    return subBig(b, a);
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

    string best_diff = W; // difference for S = 0
    int best_idx = -1;

    for (int i = 0; i < n; ++i) {
        string diff = absDiffBig(W, a[i]);
        if (cmpBig(diff, best_diff) < 0) {
            best_diff = diff;
            best_idx = i;
        }
    }

    for (int i = 0; i < n; ++i) {
        if (i) cout << ' ';
        cout << (i == best_idx ? 1 : 0);
    }
    cout << '\n';

    return 0;
}