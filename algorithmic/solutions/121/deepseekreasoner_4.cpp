#include <bits/stdc++.h>
using namespace std;

int n, m;
vector<vector<int>> pat;
vector<__int128> pow4;
__int128 union_size;

vector<int> fixed_arr;
int free_cnt;

void dfs(int i, int included) {
    if (i == m) {
        if (included > 0) {
            __int128 term = pow4[free_cnt];
            if (included % 2 == 1) union_size += term;
            else union_size -= term;
        }
        return;
    }
    // exclude pattern i
    dfs(i + 1, included);

    // include pattern i
    vector<int> changed;
    bool conflict = false;
    for (int j = 0; j < n; ++j) {
        int c = pat[i][j];
        if (c != -1) {
            if (fixed_arr[j] == -1) {
                fixed_arr[j] = c;
                changed.push_back(j);
                free_cnt--;
            } else if (fixed_arr[j] != c) {
                conflict = true;
                break;
            }
        }
    }
    if (!conflict) {
        dfs(i + 1, included + 1);
    }
    // undo changes
    for (int j : changed) {
        fixed_arr[j] = -1;
        free_cnt++;
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);

    cin >> n >> m;
    pat.resize(m, vector<int>(n));
    for (int i = 0; i < m; ++i) {
        string s;
        cin >> s;
        for (int j = 0; j < n; ++j) {
            char c = s[j];
            if (c == 'A') pat[i][j] = 0;
            else if (c == 'C') pat[i][j] = 1;
            else if (c == 'G') pat[i][j] = 2;
            else if (c == 'T') pat[i][j] = 3;
            else pat[i][j] = -1; // '?'
        }
    }

    // precompute powers of 4
    pow4.resize(n + 1);
    pow4[0] = 1;
    for (int i = 1; i <= n; ++i) {
        pow4[i] = pow4[i - 1] * 4;
    }

    fixed_arr.assign(n, -1);
    free_cnt = n;
    union_size = 0;

    dfs(0, 0);

    long double prob = (long double)union_size / (long double)pow4[n];
    cout << fixed << setprecision(15) << prob << endl;

    return 0;
}