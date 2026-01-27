#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int t;
    if(!(cin >> t)) return 0;
    while (t--) {
        int n;
        if(!(cin >> n)) return 0;
        string gathered;
        while ((int)gathered.size() < n) {
            string tok;
            if(!(cin >> tok)) break;
            for (char ch : tok) {
                if (ch == 'N' || ch == 'S' || ch == '-') {
                    gathered.push_back(ch);
                    if ((int)gathered.size() == n) break;
                }
            }
        }
        vector<int> ans;
        if ((int)gathered.size() == n) {
            for (int i = 0; i < n; i++) {
                if (gathered[i] == '-') ans.push_back(i+1);
            }
        } else {
            // Fallback: try to read n integers where 0 denotes '-'
            vector<int> a(n, 0);
            for (int i = 0; i < n; i++) {
                if(!(cin >> a[i])) a[i] = 0;
                if (a[i] == 0) ans.push_back(i+1);
            }
        }
        cout << ans.size();
        for (int i = 0; i < (int)ans.size(); i++) {
            cout << " " << ans[i];
        }
        cout << "\n";
    }
    return 0;
}