#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int t;
    if(!(cin >> t)) return 0;
    for(int _case = 0; _case < t; ++_case) {
        int n;
        if(!(cin >> n)) return 0;

        vector<vector<int>> A(n, vector<int>(n, 0));
        long long need = 1LL * n * (n - 1);
        long long cnt = 0;
        char c;
        while(cnt < need && cin.get(c)) {
            if(c == '0' || c == '1') {
                long long pos = cnt;
                int i = (int)(pos / (n - 1));
                int j_off = (int)(pos % (n - 1));
                int j = (j_off >= i) ? (j_off + 1) : j_off;
                A[i][j] = c - '0';
                cnt++;
            }
        }

        vector<int> row(n, 0);
        for(int i = 0; i < n; ++i) {
            int s = 0;
            for(int j = 0; j < n; ++j) if(i != j) s += A[i][j];
            row[i] = s;
        }

        int KVal = *max_element(row.begin(), row.end());
        vector<int> S;
        vector<int> inS(n, 0);
        for(int i = 0; i < n; ++i) if(row[i] == KVal) { S.push_back(i); inS[i] = 1; }

        int imp = -1;
        // Try j not in S: all i in S must say 1 about j
        for(int j = 0; j < n && imp == -1; ++j) if(!inS[j]) {
            bool ok = true;
            for(int i : S) {
                if(A[i][j] != 1) { ok = false; break; }
            }
            if(ok) imp = j;
        }
        // If not found, try j in S: all i in S\{j} must say 1 about j
        if(imp == -1) {
            for(int j : S) {
                bool ok = true;
                for(int i : S) {
                    if(i == j) continue;
                    if(A[i][j] != 1) { ok = false; break; }
                }
                if(ok) { imp = j; break; }
            }
        }
        if(imp == -1) imp = 0; // fallback

        cout << (imp + 1) << "\n";
    }
    return 0;
}