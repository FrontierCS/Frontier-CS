#include <bits/stdc++.h>
using namespace std;

string build(int cur_n, int start, const string& s) {
    if (cur_n == 0) {
        return s[start] == '1' ? "T" : "F";
    }
    int size = 1 << cur_n;
    bool all_false = true;
    for (int i = 0; i < size; ++i) {
        if (s[start + i] == '1') {
            all_false = false;
            break;
        }
    }
    if (all_false) return "F";
    bool all_true = true;
    for (int i = 0; i < size; ++i) {
        if (s[start + i] == '0') {
            all_true = false;
            break;
        }
    }
    if (all_true) return "T";
    int half = 1 << (cur_n - 1);
    char z = 'a' + cur_n - 1;
    string expr0 = build(cur_n - 1, start, s);
    string expr1 = build(cur_n - 1, start + half, s);
    bool same = true;
    for (int i = 0; i < half; ++i) {
        if (s[start + i] != s[start + half + i]) {
            same = false;
            break;
        }
    }
    if (same) return expr0;
    bool f1_t = true;
    for (int i = 0; i < half; ++i) {
        if (s[start + half + i] == '0') {
            f1_t = false;
            break;
        }
    }
    if (f1_t) {
        string left = expr0;
        if (left == "F") return string(1, z);
        return "(" + left + "|" + string(1, z) + ")";
    }
    bool f0_f = true;
    for (int i = 0; i < half; ++i) {
        if (s[start + i] == '1') {
            f0_f = false;
            break;
        }
    }
    if (f0_f) {
        string right = expr1;
        if (right == "T") return string(1, z);
        return "(" + right + "&" + string(1, z) + ")";
    }
    string inner = "(" + expr1 + "&" + string(1, z) + ")";
    return "(" + expr0 + "|" + inner + ")";
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int T;
    cin >> T;
    for (int t = 0; t < T; ++t) {
        int n;
        cin >> n;
        string s;
        cin >> s;
        int N = 1 << n;
        bool mono = true;
        for (int m = 0; mono && m < N; ++m) {
            if (s[m] == '0') continue;
            for (int j = 0; j < n; ++j) {
                if ((m & (1 << j)) == 0) {
                    int sup = m | (1 << j);
                    if (s[sup] == '0') {
                        mono = false;
                        break;
                    }
                }
            }
        }
        if (!mono) {
            cout << "No\n";
            continue;
        }
        cout << "Yes\n";
        string expr = build(n, 0, s);
        cout << expr << "\n";
    }
    return 0;
}