#include <bits/stdc++.h>
using namespace std;

int n;
vector<int> ans; // final permutation
vector<vector<char>> cmp; // cmp[i][j] = '<' or '>' if known, otherwise 0

// ask comparison between i and j
char ask(int i, int j) {
    if (cmp[i][j] != 0) return cmp[i][j];
    cout << "? " << i << " " << j << endl;
    char c;
    cin >> c;
    cmp[i][j] = c;
    cmp[j][i] = (c == '<') ? '>' : '<';
    return c;
}

// after enough queries, deduce the permutation
void deduce() {
    // We'll use a simple insertion sort with limited comparisons.
    // Not guaranteed to stay within query limit, but we try.
    vector<int> perm(n); // indices sorted by value
    // Start with index 1
    perm[0] = 1;
    for (int i = 2; i <= n; i++) {
        // binary search to insert i into perm
        int lo = 0, hi = i-1;
        while (lo < hi) {
            int mid = (lo + hi) / 2;
            if (ask(perm[mid], i) == '<') {
                lo = mid + 1;
            } else {
                hi = mid;
            }
        }
        // insert i at position lo
        for (int j = i-1; j >= lo; j--) perm[j+1] = perm[j];
        perm[lo] = i;
    }
    // Now perm contains indices in increasing order of values.
    // So the index at position k in perm has value k+1.
    ans.assign(n+1, 0);
    for (int i = 0; i < n; i++) {
        ans[perm[i]] = i+1;
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    cin >> n;
    cmp.assign(n+1, vector<char>(n+1, 0));
    deduce();
    cout << "!";
    for (int i = 1; i <= n; i++) cout << " " << ans[i];
    cout << endl;
    return 0;
}