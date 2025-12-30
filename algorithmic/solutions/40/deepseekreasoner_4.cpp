#include <bits/stdc++.h>
using namespace std;

int query(const vector<int>& indices) {
    cout << "0 " << indices.size();
    for (int x : indices) cout << " " << x;
    cout << endl;
    cout.flush();
    int res;
    cin >> res;
    return res;
}

// alternating pattern of (i,j,i,j,...) of length 2*m
int ask_alternating(int i, int j, int m) {
    vector<int> v;
    for (int k = 0; k < m; ++k) {
        v.push_back(i);
        v.push_back(j);
    }
    return query(v);
}

// find an index j such that s[j] != s[base] using exponential + binary search
int find_different(int base, int n) {
    int step = 1;
    int prev = base;
    // exponential phase
    while (true) {
        int j = base + step;
        if (j > n) break;
        int f = ask_alternating(base, j, 2); // m=2 gives length 4
        // f = 0 -> same, f = 3 -> case2 (base='(', j=')'), f=1 -> case3 (base=')', j='(')
        if (f != 0) {
            // found different
            return j;
        }
        prev = j;
        step *= 2;
    }
    // binary search between prev and n
    int lo = prev, hi = n;
    while (lo < hi) {
        int mid = (lo + hi) / 2;
        int f = ask_alternating(base, mid, 2);
        if (f != 0) {
            hi = mid;
        } else {
            lo = mid + 1;
        }
    }
    return lo;
}

int main() {
    int n;
    cin >> n;
    vector<char> ans(n+1, '?');
    
    // find first index with different character from index 1
    int diff = find_different(1, n);
    
    // determine types of 1 and diff
    int f = ask_alternating(1, diff, 4); // m=4 to distinguish clearly
    // case2: m=4 -> f = 4*5/2 = 10 if (1,diff) = ('(',')')
    // case3: m=4 -> f = 3*4/2 = 6 if (1,diff) = (')','(')
    // case1: f = 0 (same) shouldn't happen
    char c1, c2;
    if (f == 10) {
        c1 = '(';
        c2 = ')';
    } else {
        c1 = ')';
        c2 = '(';
    }
    ans[1] = c1;
    ans[diff] = c2;
    
    int open_idx = (c1 == '(') ? 1 : diff;
    int close_idx = (c1 == '(') ? diff : 1;
    
    // classify remaining indices
    for (int i = 1; i <= n; ++i) {
        if (ans[i] != '?') continue;
        f = ask_alternating(open_idx, i, 2); // m=2
        // if open_idx='(', then f=0 means i='(', f=3 means i=')'
        if (f == 0) {
            ans[i] = '(';
        } else {
            ans[i] = ')';
        }
    }
    
    // output answer
    cout << "1 ";
    for (int i = 1; i <= n; ++i) cout << ans[i];
    cout << endl;
    cout.flush();
    
    return 0;
}