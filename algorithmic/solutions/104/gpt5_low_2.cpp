#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int t;
    if(!(cin >> t)) return 0;
    while(t--) {
        int n;
        cin >> n;
        cout << "! 1\n" << flush;
        int y;
        if(!(cin >> y)) return 0;
        if(y == 1) {
            cout << "#\n" << flush;
            continue;
        }
        cout << "! 2\n" << flush;
        if(!(cin >> y)) return 0;
        cout << "#\n" << flush;
    }
    return 0;
}