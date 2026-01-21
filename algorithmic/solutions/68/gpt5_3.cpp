#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int t;
    if(!(cin >> t)) return 0;
    while (t--) {
        int n;
        cin >> n;
        vector<int> p(n);
        for (int i = 0; i < n; ++i) cin >> p[i];
        int a = -1, b = -1;
        for (int i = 0; i < n; ++i) {
            if (a == -1 || p[i] > p[a]) {
                b = a;
                a = i;
            } else if (b == -1 || p[i] > p[b]) {
                b = i;
            }
        }
        cout << 1 << " " << a << " " << b << "\n";
        cout.flush();
    }
    return 0;
}