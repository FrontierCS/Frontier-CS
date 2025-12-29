#include <bits/stdc++.h>
using namespace std;

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    cin >> n;
    
    if (n == 1) {
        cout << "1 1" << endl;
        return 0;
    }
    
    vector<vector<int>> f(n, vector<int>(n, 0));
    // Query all subarrays of length at least 2
    for (int l = 0; l < n; ++l) {
        for (int r = l + 1; r < n; ++r) {
            cout << "0 " << l + 1 << " " << r + 1 << endl;
            cout.flush();
            int resp;
            cin >> resp;
            f[l][r] = resp;
        }
    }
    
    vector<int> cnt(n, 0);
    for (int i = 0; i < n; ++i) {
        for (int j = i + 1; j < n; ++j) {
            int val;
            if (j == i + 1) {
                val = f[i][j];
            } else {
                int a = f[i][j];
                int b = f[i + 1][j];
                int c = f[i][j - 1];
                int d = (i + 1 < j - 1) ? f[i + 1][j - 1] : 0;
                val = a ^ b ^ c ^ d;
            }
            if (val == 1) {
                cnt[i]++;
            } else {
                cnt[j]++;
            }
        }
    }
    
    vector<int> p(n);
    for (int i = 0; i < n; ++i) {
        p[i] = cnt[i] + 1;
    }
    
    cout << "1";
    for (int i = 0; i < n; ++i) {
        cout << " " << p[i];
    }
    cout << endl;
    cout.flush();
    
    return 0;
}