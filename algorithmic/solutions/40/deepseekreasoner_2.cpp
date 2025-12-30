#include <bits/stdc++.h>
using namespace std;

int query(const vector<int>& indices) {
    int k = indices.size();
    cout << "0 " << k;
    for (int x : indices) cout << " " << x;
    cout << endl;
    cout.flush();
    int res;
    cin >> res;
    return res;
}

int main() {
    int n;
    cin >> n;
    
    // Find an index j such that (1, j) forms "()"
    int j = -1;
    for (int idx = 2; idx <= n; ++idx) {
        if (query({1, idx}) == 1) {
            j = idx;
            break;
        }
    }
    
    // Determine which of 1 and j is '('
    char s1, sj;
    if (query({1, 1, j}) == 1) {
        s1 = '(';
        sj = ')';
    } else {
        s1 = ')';
        sj = '(';
    }
    
    vector<char> ans(n + 1);
    ans[1] = s1;
    ans[j] = sj;
    
    // Determine the rest using (1, i) queries
    for (int i = 2; i <= n; ++i) {
        if (i == j) continue;
        if (query({1, i}) == 1) {
            ans[i] = (s1 == '(' ? ')' : '(');
        } else {
            ans[i] = s1;
        }
    }
    
    // Output the answer
    cout << "1 ";
    for (int i = 1; i <= n; ++i) cout << ans[i];
    cout << endl;
    cout.flush();
    
    return 0;
}