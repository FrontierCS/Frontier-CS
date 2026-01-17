#include <bits/stdc++.h>

using namespace std;

int main() {
    int t;
    cin >> t;
    for(int test = 0; test < t; test++) {
        int n, m;
        cin >> n >> m;
        vector<vector<int>> G(n + 1, vector<int>(n + 1));
        for(int i = 1; i <= n; i++) {
            for(int j = 1; j <= n; j++) {
                cin >> G[i][j];
            }
        }
        vector<int> allf;
        for(int l = 1; l <= n; l++) {
            for(int T = 1; T <= 2 * n - 1; T++) {
                cout << "? " << l << " " << T << endl;
                cout.flush();
                int f;
                cin >> f;
                allf.push_back(f);
            }
        }
        sort(allf.begin(), allf.end());
        cout << "!";
        for(int i = 0; i < m; i++) {
            cout << " " << allf[i];
        }
        cout << endl;
        cout.flush();
    }
    return 0;
}