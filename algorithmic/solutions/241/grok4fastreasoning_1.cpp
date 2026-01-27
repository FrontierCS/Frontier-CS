#include <bits/stdc++.h>
using namespace std;

int n;
string s;
vector<bool> orig;
vector<char> letters = {'a','b','c','d','e','f','g','h','i','j','k','l','m','o','p','q','r','s','t','u','v','w','x','y','z'};

string build(int fixed1, int fixed0, int avail) {
    if (avail == 0) {
        int mask = fixed1;
        return s[mask] == '1' ? "T" : "F";
    }
    // const1
    int minm = fixed1;
    if (s[minm] == '1') return "T";
    // const0
    int maxm = fixed1 | avail;
    if (s[maxm] == '0') return "F";
    // singles
    for (int vb = 0; vb < n; vb++) {
        int bit = (1 << vb);
        if ((avail & bit) == 0) continue;
        // v=0 const0
        int maxm0 = fixed1 | (avail & ~bit);
        if (s[maxm0] != '0') continue;
        // v=1 const1
        int minm1 = fixed1 | bit;
        if (s[minm1] == '1') {
            return string(1, letters[vb]);
        }
    }
    // choose lowest v
    int v = 0;
    while ((avail & (1 << v)) == 0) v++;
    int bitv = (1 << v);
    string expr0 = build(fixed1, fixed0 | bitv, avail & ~bitv);
    string expr1 = build(fixed1 | bitv, fixed0, avail & ~bitv);
    string varstr(1, letters[v]);
    // inner: var & expr1
    string inner;
    if (expr1 == "T") {
        inner = varstr;
    } else if (expr1 == "F") {
        inner = "F";
    } else {
        inner = "(" + varstr + "&" + expr1 + ")";
    }
    // whole: expr0 | inner
    string whole;
    if (inner == "F") {
        whole = expr0;
    } else if (expr0 == "T") {
        whole = "T";
    } else if (inner == "T") {
        whole = "T";
    } else if (expr0 == "F") {
        whole = inner;
    } else {
        whole = "(" + expr0 + "|" + inner + ")";
    }
    return whole;
}

bool is_monotone() {
    int N = 1 << n;
    vector<bool> dp(N);
    for (int i = 0; i < N; i++) {
        dp[i] = (s[i] == '1');
    }
    for (int b = 0; b < n; b++) {
        for (int mask = 0; mask < N; mask++) {
            if (mask & (1 << b)) {
                dp[mask] = dp[mask] | dp[mask ^ (1 << b)];
            }
        }
    }
    for (int mask = 0; mask < N; mask++) {
        if (dp[mask] && s[mask] != '1') {
            return false;
        }
    }
    return true;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int T;
    cin >> T;
    for (int t = 0; t < T; t++) {
        cin >> n;
        cin >> s;
        int N = 1 << n;
        if (is_monotone()) {
            cout << "Yes\n";
            string expr = build(0, 0, (1 << n) - 1);
            cout << expr << "\n";
        } else {
            cout << "No\n";
        }
    }
    return 0;
}