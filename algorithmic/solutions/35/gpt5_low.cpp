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
        int first_response;
        if (!(cin >> first_response)) return 0;
        if (first_response == -1) return 0;
        cout << "! " << 1 << "\n";
        cout.flush();
    }
    return 0;
}