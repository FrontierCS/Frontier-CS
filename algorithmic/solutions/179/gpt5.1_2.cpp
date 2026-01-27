#include <bits/stdc++.h>
using namespace std;

string norm(const string &s) {
    int i = 0;
    while (i + 1 < (int)s.size() && s[i] == '0') ++i;
    if (i == 0) return s;
    return s.substr(i);
}

int cmp(const string &a, const string &b) {
    if (a.size() != b.size()) return (a.size() < b.size()) ? -1 : 1;
    if (a == b) return 0;
    return (a < b) ? -1 : 1;
}

string add_str(const string &a, const string &b) {
    int i = (int)a.size() - 1;
    int j = (int)b.size() - 1;
    int carry = 0;
    string res;
    while (i >= 0 || j >= 0 || carry) {
        int sum = carry;
        if (i >= 0) sum += a[i--] - '0';
        if (j >= 0) sum += b[j--] - '0';
        res.push_back(char('0' + (sum % 10)));
        carry = sum / 10;
    }
    while (res.size() > 1 && res.back() == '0') res.pop_back();
    reverse(res.begin(), res.end());
    return res;
}

string sub_str(const string &a, const string &b) { // a >= b
    int i = (int)a.size() - 1;
    int j = (int)b.size() - 1;
    int borrow = 0;
    string res;
    while (i >= 0) {
        int diff = (a[i] - '0') - borrow - (j >= 0 ? b[j] - '0' : 0);
        if (diff < 0) {
            diff += 10;
            borrow = 1;
        } else {
            borrow = 0;
        }
        res.push_back(char('0' + diff));
        --i;
        --j;
    }
    while (res.size() > 1 && res.back() == '0') res.pop_back();
    reverse(res.begin(), res.end());
    return res;
}

string abs_diff(const string &a, const string &b) {
    int c = cmp(a, b);
    if (c == 0) return string("0");
    if (c > 0) return sub_str(a, b);
    return sub_str(b, a);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    string W;
    if (!(cin >> n >> W)) return 0;
    W = norm(W);

    vector<string> a(n);
    for (int i = 0; i < n; ++i) {
        cin >> a[i];
        a[i] = norm(a[i]);
    }

    vector<int> idx(n);
    iota(idx.begin(), idx.end(), 0);

    sort(idx.begin(), idx.end(), [&](int i, int j) {
        int c = cmp(a[i], a[j]);
        if (c != 0) return c > 0; // descending
        return i < j;
    });

    vector<int> chosen(n, 0);
    string S = "0";

    for (int id : idx) {
        string sum = add_str(S, a[id]);
        if (cmp(sum, W) <= 0) {
            S = sum;
            chosen[id] = 1;
        }
    }

    string diff_subset = abs_diff(S, W);

    // Best single element
    int best_single_idx = 0;
    string best_single_diff = abs_diff(a[0], W);
    for (int i = 1; i < n; ++i) {
        string d = abs_diff(a[i], W);
        if (cmp(d, best_single_diff) < 0) {
            best_single_diff = d;
            best_single_idx = i;
        }
    }

    // Choose better between greedy subset and best single
    if (cmp(diff_subset, best_single_diff) > 0) {
        // single is better
        fill(chosen.begin(), chosen.end(), 0);
        chosen[best_single_idx] = 1;
    }

    for (int i = 0; i < n; ++i) {
        if (i) cout << ' ';
        cout << chosen[i];
    }
    cout << '\n';

    return 0;
}