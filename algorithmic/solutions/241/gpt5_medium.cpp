#include <bits/stdc++.h>
using namespace std;

static inline string combine_balanced(vector<string> parts, char op) {
    if (parts.empty()) return "";
    if (parts.size() == 1) return parts[0];
    vector<string> cur = std::move(parts);
    while (cur.size() > 1) {
        vector<string> nxt;
        nxt.reserve((cur.size() + 1) / 2);
        for (size_t i = 0; i + 1 < cur.size(); i += 2) {
            string s;
            s.reserve(cur[i].size() + cur[i+1].size() + 3);
            s.push_back('(');
            s += cur[i];
            s.push_back(op);
            s += cur[i+1];
            s.push_back(')');
            nxt.push_back(std::move(s));
        }
        if (cur.size() & 1) nxt.push_back(std::move(cur.back()));
        cur.swap(nxt);
    }
    return cur[0];
}

static inline string build_and_vars(const vector<string>& vars) {
    if (vars.empty()) return "T"; // should not occur in our usage
    if (vars.size() == 1) return vars[0];
    vector<string> parts = vars;
    return combine_balanced(parts, '&');
}

static inline string build_or_terms(const vector<string>& terms) {
    if (terms.empty()) return "F";
    if (terms.size() == 1) return terms[0];
    vector<string> parts = terms;
    return combine_balanced(parts, '|');
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
        int L = 1 << n;
        bool ok = true;
        // Monotonicity check: for each edge 0->1 on each variable
        for (int i = 0; i < n && ok; ++i) {
            int step = 1 << i;
            for (int mask = 0; mask < L; ++mask) {
                if ((mask & step) == 0) {
                    if (s[mask] == '1' && s[mask | step] == '0') {
                        ok = false;
                        break;
                    }
                }
            }
        }
        if (!ok) {
            cout << "No\n";
            continue;
        }
        cout << "Yes\n";
        if (s[0] == '1') {
            cout << "T\n";
            continue;
        }
        // Count ones; if none, F
        bool any1 = false;
        for (char c : s) if (c == '1') { any1 = true; break; }
        if (!any1) {
            cout << "F\n";
            continue;
        }
        // Collect minimal true points (antichain)
        vector<uint32_t> mins;
        mins.reserve(1 << (n/2));
        for (int mask = 0; mask < L; ++mask) {
            if (s[mask] != '1') continue;
            bool minimal = true;
            uint32_t x = mask;
            while (x) {
                uint32_t lsb = x & -x;
                int i = __builtin_ctz(x);
                if (s[mask ^ lsb] == '1') { minimal = false; break; }
                x ^= lsb;
            }
            if (minimal) mins.push_back((uint32_t)mask);
        }
        // If no minimal points (shouldn't happen unless s all zeros handled above)
        if (mins.empty()) {
            cout << "F\n";
            continue;
        }
        // Build conjunction for each minimal point
        vector<string> terms;
        terms.reserve(mins.size());
        for (uint32_t m : mins) {
            vector<string> vars;
            vars.reserve(__builtin_popcount(m));
            for (int i = 0; i < n; ++i) {
                if (m & (1u << i)) {
                    char v = char('a' + i);
                    vars.emplace_back(1, v);
                }
            }
            if (vars.empty()) { // This would imply T, but s[0]=='1' handled earlier
                terms.push_back("T");
            } else if (vars.size() == 1) {
                terms.push_back(vars[0]);
            } else {
                terms.push_back(build_and_vars(vars));
            }
        }
        // If any term is T, whole function is T
        bool hasT = false;
        for (auto &e : terms) if (e == "T") { hasT = true; break; }
        if (hasT) {
            cout << "T\n";
            continue;
        }
        // Combine with OR
        string expr = build_or_terms(terms);
        cout << expr << "\n";
    }
    return 0;
}