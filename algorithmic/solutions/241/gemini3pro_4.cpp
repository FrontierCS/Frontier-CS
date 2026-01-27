#include <iostream>
#include <vector>
#include <string>
#include <map>
#include <algorithm>

using namespace std;

// Memoization: map truth_table -> {cost, expression_template}
// The expression uses char(0), char(1)... to represent variables corresponding to
// the dimensions of the truth table.
map<string, pair<int, string>> memo;

// Helper to check if bit set
inline bool is_set(int mask, int bit) {
    return (mask >> bit) & 1;
}

// Function to check monotonicity
bool check_monotonicity(int n, const string& s) {
    int len = 1 << n;
    for (int i = 0; i < len; ++i) {
        if (s[i] == '1') {
            for (int b = 0; b < n; ++b) {
                if (!is_set(i, b)) {
                    int neighbor = i | (1 << b);
                    if (s[neighbor] == '0') return false;
                }
            }
        }
    }
    return true;
}

// Smart constructors for AND and OR to simplify expressions and costs
pair<int, string> combine_and(pair<int, string> p1, pair<int, string> p2) {
    if (p1.second == "F" || p2.second == "F") return {0, "F"};
    if (p1.second == "T") return p2;
    if (p2.second == "T") return p1;
    return {p1.first + p2.first + 1, "(" + p1.second + "&" + p2.second + ")"};
}

pair<int, string> combine_or(pair<int, string> p1, pair<int, string> p2) {
    if (p1.second == "T" || p2.second == "T") return {0, "T"};
    if (p1.second == "F") return p2;
    if (p2.second == "F") return p1;
    return {p1.first + p2.first + 1, "(" + p1.second + "|" + p2.second + ")"};
}

// Solve function
pair<int, string> solve(string s) {
    int len = s.length();
    // k = log2(len)
    int k = 0;
    while ((1 << k) < len) k++;

    // Base cases
    bool all0 = true, all1 = true;
    for (char c : s) {
        if (c == '1') all0 = false;
        else all1 = false;
    }
    if (all0) return {0, "F"};
    if (all1) return {0, "T"};
    
    if (memo.count(s)) return memo[s];

    // Identify essential variables
    vector<int> essentials;
    for (int i = 0; i < k; ++i) {
        bool depends = false;
        for (int mask = 0; mask < len; ++mask) {
            if (!is_set(mask, i)) {
                if (s[mask] != s[mask | (1 << i)]) {
                    depends = true;
                    break;
                }
            }
        }
        if (depends) {
            essentials.push_back(i);
        }
    }

    // If there are non-essential variables, reduce the table
    if (essentials.size() < k) {
        string new_s(1 << essentials.size(), ' ');
        for (int i = 0; i < (1 << essentials.size()); ++i) {
            int old_idx = 0;
            for (int b = 0; b < essentials.size(); ++b) {
                if (is_set(i, b)) {
                    old_idx |= (1 << essentials[b]);
                }
            }
            new_s[i] = s[old_idx];
        }
        pair<int, string> res = solve(new_s);
        string remapped_expr = "";
        for (char c : res.second) {
            if (c == 'F' || c == 'T' || c == '&' || c == '|' || c == '(' || c == ')') {
                remapped_expr += c;
            } else {
                remapped_expr += (char)(essentials[(int)c]);
            }
        }
        return memo[s] = {res.first, remapped_expr};
    }

    // Try splitting on each variable
    int min_cost = 2e9;
    string best_expr = "";

    for (int i = 0; i < k; ++i) {
        string s0 = "", s1 = "";
        s0.reserve(len / 2); s1.reserve(len / 2);
        for (int mask = 0; mask < len; ++mask) {
            if (!is_set(mask, i)) s0 += s[mask];
            else s1 += s[mask];
        }
        
        pair<int, string> r0 = solve(s0);
        pair<int, string> r1 = solve(s1);
        
        // Construct candidates
        // Decompose as f = (f0 | (x & f1)) which works for monotone functions (since f0 <= f1)
        // Note: f|_{x=0} = f0, f|_{x=1} = f0 | f1 = f1.
        pair<int, string> var_x = {0, string(1, (char)i)};
        pair<int, string> term = combine_and(var_x, r1);
        pair<int, string> cand = combine_or(r0, term);
        
        if (cand.first < min_cost) {
            min_cost = cand.first;
            best_expr = cand.second;
        }
    }
    
    return memo[s] = {min_cost, best_expr};
}

void run_test() {
    int n;
    if (!(cin >> n)) return;
    string s;
    cin >> s;
    
    if (!check_monotonicity(n, s)) {
        cout << "No" << endl;
        return;
    }
    
    cout << "Yes" << endl;
    memo.clear(); // Clear memo for each test case to avoid memory limit issues with many large cases
    
    pair<int, string> res = solve(s);
    string final_expr = "";
    for (char c : res.second) {
         if (c == 'F' || c == 'T' || c == '&' || c == '|' || c == '(' || c == ')') {
            final_expr += c;
         } else {
             final_expr += (char)('a' + c);
         }
    }
    cout << final_expr << endl;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    int t;
    if (cin >> t) {
        while(t--) {
            run_test();
        }
    }
    return 0;
}