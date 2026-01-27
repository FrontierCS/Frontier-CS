#include <bits/stdc++.h>
using namespace std;

string normalize(string s) {
    if (s.empty()) return "0";
    size_t startpos = s.find_first_not_of('0');
    if (startpos == string::npos) return "0";
    return s.substr(startpos);
}

string big_add(string x, string y) {
    if (x == "0") return y;
    if (y == "0") return x;
    string a = x;
    string b = y;
    reverse(a.begin(), a.end());
    reverse(b.begin(), b.end());
    size_t len = max(a.size(), b.size());
    a.resize(len, '0');
    b.resize(len, '0');
    string res(len + 1, '0');
    int carry = 0;
    for (size_t i = 0; i < len; ++i) {
        int sum = (a[i] - '0') + (b[i] - '0') + carry;
        res[i] = (sum % 10) + '0';
        carry = sum / 10;
    }
    res[len] = carry + '0';
    reverse(res.begin(), res.end());
    size_t startpos = res.find_first_not_of('0');
    if (startpos == string::npos) return "0";
    return res.substr(startpos);
}

string big_subtract(string x, string y) {
    if (y == "0") return x;
    if (x == y) return "0";
    string a = x;
    string b = y;
    reverse(a.begin(), a.end());
    reverse(b.begin(), b.end());
    size_t len = a.size();
    b.resize(len, '0');
    string res(len, '0');
    int borrow = 0;
    for (size_t i = 0; i < len; ++i) {
        int diff = (a[i] - '0') - (b[i] - '0') - borrow;
        if (diff < 0) {
            diff += 10;
            borrow = 1;
        } else {
            borrow = 0;
        }
        res[i] = diff + '0';
    }
    reverse(res.begin(), res.end());
    size_t startpos = res.find_first_not_of('0');
    if (startpos == string::npos) return "0";
    return res.substr(startpos);
}

int main() {
    int n;
    string W_str;
    cin >> n >> W_str;
    W_str = normalize(W_str);
    vector<string> a(n);
    for (auto& s : a) {
        cin >> s;
        s = normalize(s);
    }
    vector<pair<string, int>> items(n);
    for (int i = 0; i < n; i++) {
        items[i] = {a[i], i};
    }
    auto big_cmp = [](const string& x, const string& y) -> int {
        if (x.size() > y.size()) return 1;
        if (x.size() < y.size()) return -1;
        if (x > y) return 1;
        if (x < y) return -1;
        return 0;
    };
    sort(items.begin(), items.end(), [&](const pair<string, int>& p1, const pair<string, int>& p2) {
        return big_cmp(p1.first, p2.first) > 0;
    });
    vector<int> choice(n, 0);
    string current = "0";
    for (auto& p : items) {
        string temp = big_add(current, p.first);
        if (big_cmp(temp, W_str) <= 0) {
            current = temp;
            choice[p.second] = 1;
        }
    }
    string R = big_subtract(W_str, current);
    if (big_cmp(R, "0") > 0) {
        string min_not = "";
        int best_i = -1;
        for (int i = 0; i < n; i++) {
            if (choice[i] == 0 && big_cmp(a[i], "0") > 0) {
                if (best_i == -1 || big_cmp(a[i], min_not) < 0) {
                    min_not = a[i];
                    best_i = i;
                }
            }
        }
        if (best_i != -1) {
            string temp = big_add(current, min_not);
            string error_new = big_subtract(temp, W_str);
            if (big_cmp(error_new, R) < 0) {
                choice[best_i] = 1;
            }
        }
    }
    for (int i = 0; i < n; i++) {
        if (i > 0) cout << " ";
        cout << choice[i];
    }
    cout << endl;
    return 0;
}