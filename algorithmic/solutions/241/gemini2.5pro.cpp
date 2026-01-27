#include <iostream>
#include <vector>
#include <string>
#include <cmath>
#include <numeric>
#include <algorithm>
#include <map>
#include <queue>

using namespace std;

// Generates the truth table for the i-th variable.
string get_var_s(int n, int var_idx) {
    int len = 1 << n;
    string s(len, '0');
    for (int i = 0; i < len; ++i) {
        if ((i >> var_idx) & 1) {
            s[i] = '1';
        }
    }
    return s;
}

void solve() {
    int n;
    cin >> n;
    string s;
    cin >> s;

    // A function is expressible with {&, |} iff it's monotone.
    // Check for monotonicity: if f(x)=1, then for any y that is a superset of x, f(y) must be 1.
    // We only need to check for inputs differing by one bit.
    int len = 1 << n;
    for (int i = 0; i < len; ++i) {
        for (int j = 0; j < n; ++j) {
            if (!((i >> j) & 1)) { // If j-th bit is 0
                if (s[i] == '1' && s[i | (1 << j)] == '0') {
                    cout << "No" << endl;
                    return;
                }
            }
        }
    }

    cout << "Yes" << endl;

    // Handle constant functions
    if (s == string(len, '0')) {
        cout << "F" << endl;
        return;
    }
    if (s == string(len, '1')) {
        cout << "T" << endl;
        return;
    }

    // BFS to find the shortest expression
    map<string, pair<string, int>> dists;
    vector<string> reached_funcs;

    auto add_initial_func = [&](const string& func_s, const string& expr) {
        if (dists.find(func_s) == dists.end()) {
            dists[func_s] = {expr, 0};
            reached_funcs.push_back(func_s);
        }
    };

    // Add base functions (0 operators)
    add_initial_func(string(len, '0'), "F");
    add_initial_func(string(len, '1'), "T");
    for (int i = 0; i < n; ++i) {
        string var_s = get_var_s(n, i);
        string var_name(1, (char)('a' + i));
        add_initial_func(var_s, var_name);
    }

    if (dists.count(s)) {
        cout << dists[s].first << endl;
        return;
    }

    int head = 0;
    while(head < reached_funcs.size()) {
        string s1 = reached_funcs[head];
        auto [expr1, ops1] = dists[s1];

        // Combine s1 with all functions found so far (including s1)
        for (int i = 0; i <= head; ++i) {
            string s2 = reached_funcs[i];
            auto [expr2, ops2] = dists[s2];

            // OR operation
            string s_or(len, '0');
            for(int k=0; k<len; ++k) s_or[k] = (s1[k] == '1' || s2[k] == '1') ? '1' : '0';
            
            int new_ops_or = ops1 + ops2 + 1;
            if (dists.find(s_or) == dists.end() || new_ops_or < dists[s_or].second) {
                dists[s_or] = {"(" + expr1 + "|" + expr2 + ")", new_ops_or};
                reached_funcs.push_back(s_or);
                 if (s_or == s) {
                    cout << dists[s].first << endl;
                    return;
                }
            }

            // AND operation
            string s_and(len, '0');
            for(int k=0; k<len; ++k) s_and[k] = (s1[k] == '1' && s2[k] == '1') ? '1' : '0';
            
            int new_ops_and = ops1 + ops2 + 1;
            if (dists.find(s_and) == dists.end() || new_ops_and < dists[s_and].second) {
                dists[s_and] = {"(" + expr1 + "&" + expr2 + ")", new_ops_and};
                reached_funcs.push_back(s_and);
                if (s_and == s) {
                    cout << dists[s].first << endl;
                    return;
                }
            }
        }
        head++;
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    int t;
    cin >> t;
    while (t--) {
        solve();
    }
    return 0;
}