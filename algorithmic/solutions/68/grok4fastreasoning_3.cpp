#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(NULL);
    int t;
    cin >> t;
    for (int test = 0; test < t; test++) {
        int n;
        cin >> n;
        int k = (n + 4) / 2; // ceil((n+3)/2)
        int m = n - k;
        vector<int> active;
        for (int i = 0; i < n; i++) active.push_back(i);
        for (int r = 0; r < m; r++) {
            vector<int> new_active;
            for (int j = 0; j < active.size(); j++) {
                int i = active[j];
                cout << 0 << " " << i << endl;
                cout.flush();
                int x;
                cin >> x;
                if (x == 1) {
                    new_active.push_back(i);
                }
            }
            active = new_active;
        }
        // now active has k pens
        int a = active[0];
        int b = active[1];
        cout << 1 << " " << a << " " << b << endl;
        cout.flush();
    }
    return 0;
}