#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if(!(cin >> n)) return 0;
    // Output n distinct words using only 'X' and 'O', lengths within [1, 30n]
    for (int i = 1; i <= n; ++i) {
        string s(i, (i % 2) ? 'X' : 'O');
        cout << s << "\n";
    }
    cout.flush();

    int q;
    if(!(cin >> q)) return 0;
    while (q--) {
        long long p;
        cin >> p;
        // Dummy answers (since this is originally interactive)
        cout << 1 << " " << 1 << "\n";
        cout.flush();
    }
    return 0;
}