#include <bits/stdc++.h>
using namespace std;

string buildTreeRange(const vector<string>& v, char op, int l, int r) {
    if (l + 1 == r) return v[l];
    int mid = (l + r) / 2;
    string left = buildTreeRange(v, op, l, mid);
    string right = buildTreeRange(v, op, mid, r);
    string res;
    res.reserve(left.size() + right.size() + 3);
    res.push_back('(');
    res += left;
    res.push_back(op);
    res += right;
    res.push_back(')');
    return res;
}

string buildTree(const vector<string>& v, char op) {
    int sz = (int)v.size();
    if (sz == 0) return "";
    if (sz == 1) return v[0];
    return buildTreeRange(v, op, 0, sz);
}

string buildAND(const vector<int>& bits) {
    int k = (int)bits.size();
    if (k == 0) {
        return "T";
    } else if (k == 1) {
        return string(1, char('a' + bits[0]));
    } else {
        vector<string> leaves;
        leaves.reserve(k);
        for (int idx : bits) {
            leaves.emplace_back(1, char('a' + idx));
        }
        return buildTree(leaves, '&');
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int T;
    if (!(cin >> T)) return 0;
    while (T--) {
        int n;
        cin >> n;
        string s;
        cin >> s;
        int m = 1 << n;

        bool monotone = true;
        for (int i = 0; i < n && monotone; ++i) {
            for (int mask = 0; mask < m; ++mask) {
                if ((mask & (1 << i)) == 0) {
                    if (s[mask] == '1' && s[mask | (1 << i)] == '0') {
                        monotone = false;
                        break;
                    }
                }
            }
        }

        if (!monotone) {
            cout << "No\n";
            continue;
        }

        cout << "Yes\n";

        if (s[0] == '1') {
            // Constant True
            cout << "T\n";
            continue;
        }
        if (s[m - 1] == '0') {
            // Constant False
            cout << "F\n";
            continue;
        }

        vector<string> terms;
        terms.reserve(m);
        for (int mask = 0; mask < m; ++mask) {
            if (s[mask] == '1') {
                // Since s[0] == '0' here, mask != 0 when s[mask]=='1'
                vector<int> bits;
                bits.reserve(n);
                for (int i = 0; i < n; ++i) {
                    if (mask & (1 << i)) bits.push_back(i);
                }
                string term = buildAND(bits);
                terms.push_back(std::move(term));
            }
        }

        string expr;
        if (terms.size() == 1) expr = terms[0];
        else expr = buildTree(terms, '|');

        cout << expr << "\n";
    }

    return 0;
}