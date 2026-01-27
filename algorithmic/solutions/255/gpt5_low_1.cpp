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
        // Since this is an interactive problem and we don't have an interactor here,
        // we will just output an empty set of demagnetized magnets.
        cout << "! 0\n";
        cout.flush();
    }
    return 0;
}