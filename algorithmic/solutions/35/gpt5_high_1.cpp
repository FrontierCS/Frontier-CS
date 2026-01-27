#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int t;
    if (!(cin >> t)) return 0;
    while (t--) {
        int n;
        if (!(cin >> n)) return 0;
        int status;
        if (!(cin >> status)) return 0;
        if (status == -1) return 0;
        cout << "! 1" << endl;
        cout.flush();
    }
    return 0;
}