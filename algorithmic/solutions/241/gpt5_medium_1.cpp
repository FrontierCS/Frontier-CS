#include <bits/stdc++.h>
using namespace std;

static string combineBalanced(vector<string> items, char op) {
    if (items.empty()) return "";
    while (items.size() > 1) {
        vector<string> next;
        next.reserve((items.size() + 1) / 2);
        for (size_t i = 0; i < items.size(); i += 2) {
            if (i + 1 < items.size()) {
                string s;
                s.reserve(items[i].size() + items[i+1].size() + 3);
                s.push_back('(');
                s += items[i];
                s.push_back(op);
                s += items[i+1];
                s.push_back(')');
                next.push_back(std::move(s));
            } else {
                next.push_back(std::move(items[i]));
            }
        }
        items.swap(next);
    }
    return items[0];
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int T;
    if (!(cin >> T)) return 0;
    while (T--) {
        int n;
        string s;
        cin >> n;
        cin >> s;
        size_t L = 1ull << n;
        if (s.size() != L) {
            cout << "No\n";
            continue;
        }
        bool mono = true;
        for (int i = 0; i < n && mono; ++i) {
            size_t step = 1ull << i;
            for (size_t m = 0; m < L; ++m) {
                if ((m & step) == 0) {
                    if (s[m] == '1' && s[m | step] == '0') {
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
        if (s[0] == '1') {
            cout << "T\n";
            continue;
        }
        bool any1 = false;
        for (char c : s) if (c == '1') { any1 = true; break; }
        if (!any1) {
            cout << "F\n";
            continue;
        }
        vector<string> terms;
        terms.reserve(L);
        for (size_t m = 1; m < L; ++m) {
            if (s[m] != '1') continue;
            bool minimal = true;
            size_t mm = m;
            while (mm && minimal) {
                size_t low = mm & -mm;
                size_t prev = m ^ low;
                if (s[prev] == '1') {
                    minimal = false;
                    break;
                }
                mm ^= low;
            }
            if (!minimal) continue;
            vector<string> vars;
            vars.reserve(__builtin_popcount((unsigned)m));
            for (int i = 0; i < n; ++i) {
                if (m & (1ull << i)) {
                    string v(1, char('a' + i));
                    vars.push_back(std::move(v));
                }
            }
            string term = combineBalanced(vars, '&');
            terms.push_back(std::move(term));
        }
        if (terms.empty()) {
            cout << "F\n";
            continue;
        }
        sort(terms.begin(), terms.end());
        string expr = combineBalanced(terms, '|');
        cout << expr << "\n";
    }
    return 0;
}