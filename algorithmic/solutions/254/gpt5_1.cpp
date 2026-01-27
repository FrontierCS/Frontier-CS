#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int t;
    if (!(cin >> t)) return 0;
    while (t--) {
        int n;
        cin >> n;
        int N = n * n;
        cout << "!";
        for (int i = N; i >= n; --i) {
            cout << " " << i;
        }
        cout << "\n";
        cout.flush();
    }
    return 0;
}